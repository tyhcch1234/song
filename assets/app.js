/* 歌 · 廣東話原創 — 前端渲染 + 旋律試聽 */
(function () {
  "use strict";

  var SONGS = (window.SONGS || []).slice().sort(function (a, b) { return b.no - a.no; });
  var app = document.getElementById("app");

  /* ---------------- helpers ---------------- */
  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function fmtDate(d) {
    var p = String(d).split("-");
    return p.length === 3 ? p[0] + "." + p[1] + "." + p[2] : d;
  }

  /* ---------------- 簡譜 ---------------- */
  var DEG = { C: 1, D: 2, E: 3, F: 4, G: 5, A: 6, B: 7 };

  function jianpu(note) {
    var m = /^([A-G])(#|b)?(-?\d)$/.exec(note);
    var box = el("span", "jp");
    if (!m) { box.textContent = note; return box; }
    var oct = parseInt(m[3], 10);
    box.appendChild(document.createTextNode((m[2] === "#" ? "♯" : "") + DEG[m[1]]));
    if (oct > 4) box.appendChild(el("sup", null, "·"));
    if (oct < 4) box.appendChild(el("sub", null, "·"));
    return box;
  }

  function freq(note) {
    var m = /^([A-G])(#|b)?(-?\d)$/.exec(note);
    if (!m) return 440;
    var base = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }[m[1]];
    var acc = m[2] === "#" ? 1 : m[2] === "b" ? -1 : 0;
    var midi = 12 * (parseInt(m[3], 10) + 1) + base + acc;
    return 440 * Math.pow(2, (midi - 69) / 12);
  }

  /* ---------------- 旋律播放 ---------------- */
  function buildPlayer(song) {
    var mel = song.chorusMelody;
    if (!mel || !mel.notes || !mel.notes.length) return null;

    var bpm = (song.meta && song.meta.bpm) || 80;
    var spb = 60 / bpm;

    var box = el("div", "player");
    box.appendChild(el("h3", null, mel.label || "旋律示範"));
    if (mel.note) box.appendChild(el("p", "hint", mel.note));

    /* --- 簡譜格 + 每個音嘅起始秒數 --- */
    var grid = el("div", "melody");
    var cells = [], starts = [], acc = 0, lines = {};

    mel.notes.forEach(function (n) {
      starts.push(acc);
      acc += n.d * spb;

      var key = n.line || 1;
      if (!lines[key]) {
        lines[key] = el("div", "mline");
        grid.appendChild(lines[key]);
      }
      var cell = el("div", "note");
      cell.style.flex = n.d + " 1 0";
      cell.appendChild(jianpu(n.n));
      if (n.s) cell.appendChild(el("span", "syl", n.s));
      lines[key].appendChild(cell);
      cells.push(cell);
    });

    function highlight(i) {
      for (var k = 0; k < cells.length; k++) {
        if (k === i) cells[k].classList.add("on");
        else cells[k].classList.remove("on");
      }
    }

    /* --- 主播放器：真音檔（iOS 靜音掣下仍然有聲，同 <video> 一樣走媒體聲道） --- */
    var audio = document.createElement("audio");
    audio.controls = true;
    audio.preload = "metadata";
    audio.src = "assets/audio/" + song.id + "-chorus.wav";

    var audioWrap = el("div", "audio-wrap");
    audioWrap.appendChild(audio);
    box.appendChild(audioWrap);
    box.appendChild(grid);

    var tip = el("p", "tip", "冇聲？先檢查手機側邊嘅靜音掣同媒體音量，再按一次播放。");
    box.appendChild(tip);

    var failing = false;

    audio.addEventListener("play", function () { box.classList.add("playing"); });
    audio.addEventListener("pause", function () { box.classList.remove("playing"); highlight(-1); });
    audio.addEventListener("ended", function () { highlight(-1); });

    audio.addEventListener("timeupdate", function () {
      var t = audio.currentTime;
      var idx = -1;
      for (var i = 0; i < starts.length; i++) {
        if (t >= starts[i] && t < starts[i] + mel.notes[i].d * spb) { idx = i; break; }
      }
      highlight(idx);
    });

    audio.addEventListener("error", function () {
      if (failing) return;
      failing = true;
      audioWrap.parentNode && audioWrap.parentNode.removeChild(audioWrap);
      grid.parentNode && grid.parentNode.removeChild(grid);
      tip.textContent = "音檔載入唔到，改用即時合成播放。";
      box.insertBefore(buildSynthFallback(mel, bpm, cells, grid), tip);
    });

    // 點簡譜任何一個音 → 由嗰度開始播
    cells.forEach(function (cell, i) {
      cell.addEventListener("click", function () {
        if (failing) return;
        audio.currentTime = starts[i] + 0.01;
        var p = audio.play();
        if (p && p.catch) p.catch(function () {});
      });
    });

    return box;
  }

  /* --- 後備：Web Audio 即時合成 --- */
  function buildSynthFallback(mel, bpm, noteEls, grid) {
    var spb = 60 / bpm;
    var wrap = el("div", "controls");
    var btn = el("button", "btn", "▶ 播放旋律");
    btn.type = "button";
    wrap.appendChild(btn);
    wrap.appendChild(el("span", "tempo", "♩ = " + bpm));

    var ctx = null, timers = [], playing = false;

    function stop() {
      playing = false;
      timers.forEach(clearTimeout);
      timers = [];
      if (ctx) { ctx.close(); ctx = null; }
      noteEls.forEach(function (c) { c.classList.remove("on"); });
      btn.textContent = "▶ 播放旋律";
    }

    btn.addEventListener("click", function () {
      if (playing) { stop(); return; }
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) { btn.textContent = "此瀏覽器唔支援播放"; return; }

      ctx = new AC();
      if (ctx.state === "suspended" && ctx.resume) ctx.resume();
      playing = true;
      btn.textContent = "■ 停止";

      var t0 = ctx.currentTime + 0.12, t = t0;
      mel.notes.forEach(function (n, i) {
        var dur = n.d * spb, f = freq(n.n);
        var osc = ctx.createOscillator(), gain = ctx.createGain();
        osc.type = "triangle";
        osc.frequency.value = f;
        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.exponentialRampToValueAtTime(0.25, t + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + dur * 0.95);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(t); osc.stop(t + dur);

        var off = (t - t0) * 1000;
        timers.push(setTimeout(function () {
          noteEls.forEach(function (c) { c.classList.remove("on"); });
          noteEls[i] && noteEls[i].classList.add("on");
        }, off));
        timers.push(setTimeout(function () {
          noteEls[i] && noteEls[i].classList.remove("on");
        }, off + dur * 950));
        t += dur;
      });
      timers.push(setTimeout(stop, (t - t0) * 1000 + 400));
    });

    return wrap;
  }

  /* ---------------- 版面 ---------------- */
  function renderList() {
    app.innerHTML = "";
    document.title = "歌 · 廣東話原創";

    var hero = el("section", "hero");
    var h1 = el("h1");
    h1.innerHTML = "寫喺<em>火</em>與<em>聲</em>之間";
    hero.appendChild(h1);
    hero.appendChild(el("p", null, "廣東話原創歌詞集。每一首寫一個人、一件事、一句想講但平時講唔出口嘅話。呢度會一直加落去。"));

    var list = el("div", "list");
    if (!SONGS.length) list.appendChild(el("p", null, "暫時未有作品。"));

    SONGS.forEach(function (s) {
      var a = el("a", "song-card");
      a.href = "#/s/" + s.id;

      var top = el("div", "card-top");
      top.appendChild(el("span", "card-no", "No. " + String(s.no).padStart(2, "0")));
      top.appendChild(el("span", null, fmtDate(s.date)));
      a.appendChild(top);

      a.appendChild(el("h2", null, s.title));
      if (s.dedication) a.appendChild(el("p", null, s.dedication));

      if (s.tags && s.tags.length) {
        var tags = el("div", "tags");
        s.tags.forEach(function (t) { tags.appendChild(el("span", "tag", t)); });
        a.appendChild(tags);
      }
      list.appendChild(a);
    });

    hero.appendChild(list);
    app.appendChild(hero);
  }

  function renderSong(song) {
    app.innerHTML = "";
    document.title = song.title + " · 歌";

    var back = el("a", "back", "← 全部歌曲");
    back.href = "#/";
    app.appendChild(back);

    var head = el("section", "song-head");
    var top = el("div", "card-top");
    top.appendChild(el("span", "card-no", "No. " + String(song.no).padStart(2, "0")));
    top.appendChild(el("span", null, fmtDate(song.date)));
    head.appendChild(top);

    head.appendChild(el("h1", null, song.title));
    if (song.dedication) head.appendChild(el("p", "dedication", song.dedication));

    var chips = el("div", "chips");
    var meta = song.meta || {};
    [["調", meta.key], ["速度", meta.bpm ? meta.bpm + " BPM" : ""], ["拍子", meta.meter], ["風格", meta.style], ["長度", meta.length]]
      .forEach(function (pair) {
        if (!pair[1]) return;
        var c = el("span", "chip");
        c.appendChild(document.createTextNode(pair[0]));
        var b = el("b");
        b.textContent = pair[1];
        c.appendChild(b);
        chips.appendChild(c);
      });
    if (song.tags) song.tags.forEach(function (t) {
      chips.appendChild(el("span", "chip", "# " + t));
    });
    head.appendChild(chips);
    app.appendChild(head);

    var body = el("div", "sections");
    (song.sections || []).forEach(function (sec) {
      var d = el("div", "section");
      var h3 = el("h3", null, sec.name);
      if (sec.en) h3.appendChild(el("span", null, sec.en));
      d.appendChild(h3);
      if (sec.chords) d.appendChild(el("p", "chords", sec.chords));
      d.appendChild(el("p", "lyrics", (sec.lines || []).join("\n")));
      body.appendChild(d);
    });
    app.appendChild(body);

    var player = buildPlayer(song);
    if (player) app.appendChild(player);

    if (song.notes && song.notes.length) {
      var nb = el("div", "notes");
      nb.appendChild(el("h3", null, "創作筆記"));
      var ul = el("ul");
      song.notes.forEach(function (t) { ul.appendChild(el("li", null, t)); });
      nb.appendChild(ul);
      app.appendChild(nb);
    }
  }

  function route() {
    var m = /^#\/s\/(.+)$/.exec(location.hash || "");
    if (m) {
      var id = decodeURIComponent(m[1]);
      var song = SONGS.filter(function (s) { return s.id === id; })[0];
      if (song) { renderSong(song); window.scrollTo(0, 0); return; }
    }
    renderList();
    window.scrollTo(0, 0);
  }

  window.addEventListener("hashchange", route);
  route();
})();
