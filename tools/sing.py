#!/usr/bin/env python3
"""由 songs.js 嘅 chorusMelody + 歌詞，合成「唱歌版」音檔。

做法：逐個字用粵語 TTS 發音 → 量度基頻 → 移調到目標音高 → 對齊拍子長度
      → 加伴奏（和弦 pad + bass + kick）→ 輸出 wav

用法: python3 tools/sing.py [songId]
"""
import asyncio
import json
import os
import subprocess
import sys

import numpy as np
import soundfile as sf
import edge_tts

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "tools", ".vox-cache")
OUT = os.path.join(ROOT, "assets", "audio")
VOICE = "zh-HK-HiuMaanNeural"   # 女聲基頻較高，移調幅度細，失真少
SR = 24000

# 個別字读音修正（TTS 讀錯時喺呢度換同音字）
OVERRIDE = {
    "唔": "唔",   # m4
    "呢": "呢",   # ni1
}


def load_songs():
    code = (
        "global.window={};require(process.argv[1]);"
        "process.stdout.write(JSON.stringify(window.SONGS))"
    )
    out = subprocess.run(
        ["node", "-e", code, os.path.join(ROOT, "assets", "songs.js")],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


# ---------- TTS ----------
async def tts_one(text, path, sem):
    async with sem:
        if os.path.exists(path) and os.path.getsize(path) > 500:
            return
        for attempt in range(3):
            try:
                c = edge_tts.Communicate(text, VOICE, rate="+0%", pitch="+0Hz")
                await c.save(path)
                return
            except Exception as e:
                if attempt == 2:
                    raise
                await asyncio.sleep(1.5 * (attempt + 1))


async def tts_all(chars):
    os.makedirs(CACHE, exist_ok=True)
    sem = asyncio.Semaphore(4)
    tasks = []
    for ch in chars:
        p = os.path.join(CACHE, "%s-%s.mp3" % (VOICE.split("-")[2], ch))
        tasks.append(tts_one(OVERRIDE.get(ch, ch), p, sem))
    await asyncio.gather(*tasks)


# ---------- DSP ----------
def read_mp3(path):
    x, sr = sf.read(path, dtype="float32", always_2d=False)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != SR:
        from math import gcd
        from scipy.signal import resample_poly
        g = gcd(SR, sr)
        x = resample_poly(x, SR // g, sr // g)
    return x


def trim_silence(x, thresh=0.012):
    env = np.abs(x)
    idx = np.where(env > thresh)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(0.005 * SR))
    b = min(len(x), idx[-1] + int(0.03 * SR))
    return x[a:b]


def est_f0(x, fmin=70.0, fmax=520.0):
    """用歸一化自相關估基頻（取有聲段中位數）"""
    win = int(0.04 * SR)
    hop = int(0.01 * SR)
    vals = []
    lo = int(SR / fmax)
    hi = int(SR / fmin)
    for s in range(0, max(1, len(x) - win), hop):
        f = x[s:s + win]
        if len(f) < win or np.sqrt(np.mean(f ** 2)) < 0.02:
            continue
        f = f - f.mean()
        ac = np.correlate(f, f, mode="full")[win - 1:]
        if ac[0] <= 0:
            continue
        ac = ac / ac[0]
        seg = ac[lo:hi]
        if len(seg) == 0:
            continue
        k = int(np.argmax(seg)) + lo
        if 0 < k < len(ac) - 1:  # 拋物線內插
            a, b, c = ac[k - 1], ac[k], ac[k + 1]
            denom = a - 2 * b + c
            shift = 0.5 * (a - c) / denom if denom != 0 else 0
            k = k + shift
        if k > 0:
            vals.append(SR / k)
    if not vals:
        return 200.0
    return float(np.median(vals))


def shift_pitch(x, ratio):
    """移調 ratio 倍（長度同時變成 1/ratio）"""
    n = max(1, int(round(len(x) / ratio)))
    from scipy.signal import resample
    return resample(x, n).astype(np.float32)


def extend_to(x, n, period):
    """用樂音週期長度嘅窗口做 overlap-add，拉長到尾音"""
    if len(x) >= n:
        return x[:n]
    win = max(16, int(round(period * 2)))
    if len(x) < win:
        x = np.pad(x, (0, win - len(x)))
    buf = x.copy()
    ramp = np.linspace(0, 1, win)[: win // 2]
    while len(buf) < n:
        tail = buf[-win:].copy()
        add = tail.copy()
        add[: win // 2] *= ramp
        tail[: win // 2] *= (1 - ramp)
        buf = np.concatenate([buf[:-win], tail, add[win // 2:]])
    return buf[:n]


def vibrato(x, depth=0.010, rate=5.4):
    if len(x) < SR // 10:
        return x
    t = np.arange(len(x)) / SR
    pos = np.cumsum(1.0 + depth * np.sin(2 * np.pi * rate * t))
    pos = np.clip(pos, 0, len(x) - 1)
    return np.interp(pos, np.arange(len(x)), x).astype(np.float32)


def smooth_env(n, attack=0.008, release=0.04):
    e = np.ones(n, dtype=np.float32)
    a = min(n, int(attack * SR))
    r = min(n, int(release * SR))
    if a:
        e[:a] = np.linspace(0, 1, a)
    if r:
        e[n - r:] *= np.linspace(1, 0, r)
    return e


def fit_note(x, n, f_target):
    """拉長／裁剪到 n 個樣本，並加包絡"""
    period = SR / f_target
    y = extend_to(x, n, period)
    y = y * smooth_env(len(y))
    # 長音加少少顫音，唱味出啲
    if n > 0.55 * SR:
        y = vibrato(y, 0.009, 5.4) * smooth_env(len(y))
    rms = np.sqrt(np.mean(y ** 2)) + 1e-9
    return (y / rms * 0.13).astype(np.float32)


# ---------- 伴奏 ----------
def midi_hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


NOTE_MIDI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def chord_midis(sym):
    """'C' / 'Am' / 'F#m' → (root_midi, [triad midis])，以第 4 八度為準"""
    minor = sym.endswith("m")
    name = sym[:-1] if minor else sym
    root = NOTE_MIDI[name[0]] + (1 if "#" in name else 0) + 60
    third = 3 if minor else 4
    return root, [root, root + third, root + 7]


def accompaniment(total, spb, sr=SR):
    prog = ["C", "G", "Am", "Em", "F", "C", "F", "G"]
    bar = 4 * spb
    out = np.zeros(total, dtype=np.float32)
    t = np.arange(total) / sr

    for i, sym in enumerate(prog):
        s0 = int(i * bar * sr)
        s1 = min(total, int((i + 1) * bar * sr))
        if s1 <= s0:
            break
        seg_t = np.arange(s1 - s0) / sr
        _, tri = chord_midis(sym)

        env = np.minimum(1, seg_t / 0.18) * np.exp(-seg_t / (bar * 1.6))
        env *= np.minimum(1, (seg_t[-1] - seg_t) / 0.25 + 0.02) if len(seg_t) > 1 else 1

        pad = np.zeros(s1 - s0, dtype=np.float32)
        for m in tri:
            f = midi_hz(m)
            for mult, amp in ((1, 1.0), (2, 0.18)):
                pad += amp * np.sin(2 * np.pi * f * mult * seg_t)
        out[s0:s1] += pad * env * 0.030

        # bass
        root, _ = chord_midis(sym)
        fb = midi_hz(root - 24)
        bass = np.sin(2 * np.pi * fb * seg_t) * np.exp(-seg_t / (bar * 0.9))
        bass *= np.minimum(1, seg_t / 0.02)
        out[s0:s1] += bass * 0.16

        # kick（第 1、3 拍）
        for beat in (0, 2):
            k0 = s0 + int(beat * spb * sr)
            n = int(0.22 * sr)
            if k0 + n > total:
                n = max(0, total - k0)
            if n <= 0:
                continue
            kt = np.arange(n) / sr
            f = 95 * np.exp(-kt / 0.03) + 42
            kick = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-kt / 0.07)
            out[k0:k0 + n] += kick.astype(np.float32) * 0.22

    return out


# ---------- 主流程 ----------
def build(song):
    mel = song["chorusMelody"]
    notes = mel["notes"]
    bpm = song.get("meta", {}).get("bpm", 80)
    spb = 60.0 / bpm

    chars = [n["s"] for n in notes]
    asyncio.run(tts_all(chars))

    total = int(sum(n["d"] for n in notes) * spb * SR) + int(0.9 * SR)
    vocal = np.zeros(total, dtype=np.float32)
    report = []

    pos = 0.0
    for n in notes:
        ch = n["s"]
        x = trim_silence(read_mp3(os.path.join(CACHE, "%s-%s.mp3" % (VOICE.split("-")[2], ch))))
        f0 = est_f0(x, 90.0, 420.0)
        # 旋律整體降八度，貼近人聲自然音域（C3–B3），移調幅度細好多
        target = target_hz(n["n"]) / 2.0
        ratio = float(np.clip(target / f0, 0.5, 2.0))
        y = shift_pitch(x, ratio)
        dur = n["d"] * spb
        seg = fit_note(y, int(dur * SR), target)

        s0 = int(pos * SR)
        s1 = min(total, s0 + len(seg))
        vocal[s0:s1] += seg[: s1 - s0]

        report.append((ch, n["n"], f0, target, dur))
        pos += dur

    acc = accompaniment(total, spb)
    mix = vocal * 1.0 + acc * 1.0
    peak = np.abs(mix).max()
    if peak > 0:
        mix *= 0.90 / peak
    fade = int(0.35 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix[:200] *= np.linspace(0, 1, 200)

    stem = os.environ.get("STEM")
    if stem:  # 只寫人聲軌，方便驗證音高
        v = vocal.copy()
        pk = np.abs(v).max() or 1.0
        sf.write(stem, v * (0.9 / pk), SR, subtype="PCM_16")

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "%s-vocal.wav" % song["id"])
    sf.write(path, mix, SR, subtype="PCM_16")

    # 驗證：逐個音量度輸出基頻
    errs = []
    for i, (ch, note, f0, target, dur) in enumerate(report):
        s0 = int(sum(n["d"] for n in notes[:i]) * spb * SR)
        seg = vocal[s0:s0 + int(dur * SR * 0.7)]
        if len(seg) < SR // 20:
            continue
        got = est_f0(seg, target * 0.75, target * 1.35)
        errs.append(abs(got - target) / target * 100)

    print("→ %s (%.1fs, %.0f KB)" % (path, total / SR, os.path.getsize(path) / 1024))
    print("   音高誤差 中位數 %.1f%% / 最大 %.1f%%（%d 個音）" % (
        float(np.median(errs)), float(np.max(errs)), len(errs)))
    print("   基頻範圍 %.0f–%.0f Hz" % (
        min(r[2] for r in report), max(r[2] for r in report)))


def target_hz(name):
    m = name[0]
    acc = 1 if len(name) > 2 and name[1] == "#" else 0
    octv = int(name[-1])
    return midi_hz(12 * (octv + 1) + NOTE_MIDI[m] + acc)


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for s in load_songs():
        if not s.get("chorusMelody"):
            continue
        if only and s["id"] != only:
            continue
        build(s)
