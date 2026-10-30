#!/usr/bin/env node
/* 由 songs.js 嘅 chorusMelody 合成 mp3 旋律示範
   用法: node tools/make-audio.js [songId ...]   (唔填 = 全部)
*/
const fs = require("fs");
const path = require("path");

global.window = {};
const songsPath = path.join(__dirname, "..", "assets", "songs.js");
require(songsPath);
const SONGS = window.SONGS;

const SR = 22050; // 檔案細一半，旋律用唔到更高頻
const OUT = path.join(__dirname, "..", "assets", "audio");

function freq(note) {
  const m = /^([A-G])(#|b)?(-?\d)$/.exec(note);
  if (!m) throw new Error("bad note: " + note);
  const base = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 }[m[1]];
  const acc = m[2] === "#" ? 1 : m[2] === "b" ? -1 : 0;
  const midi = 12 * (parseInt(m[3], 10) + 1) + base + acc;
  return 440 * Math.pow(2, (midi - 69) / 12);
}

function noteTimes(notes, bpm) {
  const spb = 60 / bpm;
  let t = 0;
  return notes.map((n) => {
    const start = t;
    t += n.d * spb;
    return { start, dur: n.d * spb };
  });
}

function renderWav(notes, bpm) {
  const spb = 60 / bpm;
  const totalBeats = notes.reduce((a, n) => a + n.d, 0);
  const tail = 0.8;
  const total = Math.ceil((totalBeats * spb + tail) * SR);
  const buf = new Float32Array(total);

  // 旋律：基音 + 泛音，加一點低八度墊底
  const partials = [[1, 1.0], [2, 0.3], [3, 0.12], [0.5, 0.25]];

  const times = noteTimes(notes, bpm);
  times.forEach((tm, idx) => {
    const f = freq(notes[idx].n);
    const start = Math.floor(tm.start * SR);
    const len = Math.min(Math.floor(tm.dur * SR * 0.97), total - start);
    const A = Math.floor(0.012 * SR);
    const R = Math.floor(0.05 * SR);

    for (let i = 0; i < len; i++) {
      const tt = i / SR;
      let env = 1;
      if (i < A) env *= i / A;
      env *= 1 - 0.45 * Math.min(1, tt / tm.dur);       // 自然衰減
      if (i > len - R) env *= Math.max(0, (len - i) / R); // 收尾
      let s = 0;
      for (const [mult, amp] of partials) {
        s += amp * Math.sin(2 * Math.PI * f * mult * tt);
      }
      buf[start + i] += s * env * 0.22;
    }
  });

  // 正規化 + 整體淡入淡出
  let peak = 0;
  for (let i = 0; i < total; i++) peak = Math.max(peak, Math.abs(buf[i]));
  const g = peak > 0 ? 0.88 / peak : 1;
  const fade = Math.floor(0.25 * SR);
  for (let i = 0; i < total; i++) {
    let v = buf[i] * g;
    if (i < 200) v *= i / 200;
    if (i > total - fade) v *= (total - i) / fade;
    buf[i] = v;
  }
  return { buf, total };
}

function toWavFile(buf, total, file) {
  const bytes = total * 2;
  const h = Buffer.alloc(44);
  h.write("RIFF", 0);
  h.writeUInt32LE(36 + bytes, 4);
  h.write("WAVE", 8);
  h.write("fmt ", 12);
  h.writeUInt32LE(16, 16);
  h.writeUInt16LE(1, 20);
  h.writeUInt16LE(1, 22);          // mono
  h.writeUInt32LE(SR, 24);
  h.writeUInt32LE(SR * 2, 28);
  h.writeUInt16LE(2, 32);
  h.writeUInt16LE(16, 34);
  h.write("data", 36);
  h.writeUInt32LE(bytes, 40);
  const pcm = Buffer.alloc(bytes);
  for (let i = 0; i < total; i++) {
    const v = Math.max(-1, Math.min(1, buf[i]));
    pcm.writeInt16LE(Math.round(v * 32767), i * 2);
  }
  fs.writeFileSync(file, Buffer.concat([h, pcm]));
}

const only = process.argv.slice(2);
fs.mkdirSync(OUT, { recursive: true });

let n = 0;
for (const song of SONGS) {
  if (!song.chorusMelody || !song.chorusMelody.notes) continue;
  if (only.length && !only.includes(song.id)) continue;

  const bpm = (song.meta && song.meta.bpm) || 80;
  const { buf, total } = renderWav(song.chorusMelody.notes, bpm);
  const base = path.join(OUT, song.id + "-chorus");
  toWavFile(buf, total, base + ".wav");
  console.log(`✔ ${song.title} → assets/audio/${song.id}-chorus.wav (${(total / SR).toFixed(1)}s, ${(fs.statSync(base + ".wav").size / 1024).toFixed(0)} KB)`);

  n++;
}
console.log(`完成 ${n} 首`);
