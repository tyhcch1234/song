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
    if (!m) return el("span", "jp", note);
    var deg = DEG[m[1]];
    if (m[2] === "#") deg += "";
    var oct = parseInt(m[3], 10);
    var box = el("span", "jp");
    if (m[2] === "#") {
      box.appendChild(el("span", null, "♯" + deg));
    } else {
      box.appendChild(document.createTextNode(String(deg)));
    }
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

    var ctrl = el("div", "controls");
    var btn = el("button", "btn", "▶ 播放旋律");
    btn.type = "button";
    ctrl.appendChild(btn);
    ctrl.appendChild(el("span", "tempo", "♩ = " + bpm));
    box.appendChild(ctrl);

    var grid = el("div", "melody");
    var noteEls = [];
    var lines = {};
    mel.notes.forEach(function (n) {
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
      noteEls.push(cell);
    });
    box.appendChild(grid);

    var ctx = null, timers = [], playing = false;

    function clearHighlight() {
      noteEls.forEach(function (c) { c.classList.remove("on"); });
    }

    function stop() {
      playing = false;
      timers.forEach(clearTimeout);
      timers = [];
      if (ctx) { ctx.close(); ctx = null; }
      clearHighlight();
      btn.textContent = "▶ 播放旋律";
    }

    btn.addEventListener("click", function () {
      if (playing) { stop(); return; }
      var AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) { btn.textContent = "此瀏覽器不支援試聽"; return; }

      ctx = new AC();
      playing = true;
      btn.textContent = "■ 停止";
      clearHighlight();

      var t0 = ctx.currentTime + 0.12;
      var t = t0;

      mel.notes.forEach(function (n, i) {
        var dur = n.d * spb;
        var f = freq(n.n);

        var osc = ctx.createOscillator();
        var osc2 = ctx.createOscillator();
        var gain = ctx.createGain();
        var gain2 = ctx.createGain();

        osc.type = "triangle";
        osc.frequency.value = f;
        osc2.type = "sine";
        osc2.frequency.value = f / 2;

        gain.gain.setValueAtTime(0.0001, t);
        gain.gain.exponentialRampToValueAtTime(0.22, t + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + dur * 0.95);

        gain2.gain.setValueAtTime(0.0001, t);
        gain2.gain.exponentialRampToValueAtTime(0.07, t + 0.03);
        gain2.gain.exponentialRampToValueAtTime(0.0001, t + dur * 0.9);

        osc.connect(gain).connect(ctx.destination);
        osc2.connect(gain2).connect(ctx.destination);

        osc.start(t); osc.stop(t + dur);
        osc2.start(t); osc2.stop(t + dur);

        var cellEl = noteEls[i];
        var offset = (t - t0) * 1000;
        timers.push(setTimeout(function () {
          clearHighlight();
          cellEl.classList.add("on");
        }, offset));
        timers.push(setTimeout(function () {
          cellEl.classList.remove("on");
        }, offset + dur * 950));

        t += dur;
      });

      timers.push(setTimeout(stop, (t - t0) * 1000 + 500));
    });

    return box;
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
