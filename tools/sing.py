#!/usr/bin/env python3
"""合成「唱歌版」音檔 — TD-PSOLA 歌聲合成（formant 保留）

同上一版最大分別：
  上一版 = 變速變調整段音節（formant 一齊拉高）→ 聽落係「讀字」
  呢版   = 用音高標記切 grain，按目標音高重新排 grain，母音靠重複頻譜幀拉長
           → 共振峰（formant）唔變，即係同一個人「唱」呢句，唔係卡通聲

用法: python3 tools/sing.py [songId]
      STEM=/tmp/stem.wav python3 tools/sing.py   # 另存人聲乾軌（驗證用）
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
VOICE = "zh-HK-HiuMaanNeural"
SR = 24000
FRAME = 0.01  # f0 量度步長（秒）

OVERRIDE = {"唔": "唔", "呢": "呢"}


def load_songs():
    code = ("global.window={};require(process.argv[1]);"
            "process.stdout.write(JSON.stringify(window.SONGS))")
    out = subprocess.run(["node", "-e", code, os.path.join(ROOT, "assets", "songs.js")],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


# ---------------- TTS ----------------
def cache_path(ch):
    return os.path.join(CACHE, "%s-%s.mp3" % (VOICE.split("-")[2], ch))


async def tts_one(text, path, sem):
    async with sem:
        if os.path.exists(path) and os.path.getsize(path) > 500:
            return
        for attempt in range(3):
            try:
                await edge_tts.Communicate(text, VOICE).save(path)
                return
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(1.5 * (attempt + 1))


async def tts_all(chars):
    os.makedirs(CACHE, exist_ok=True)
    sem = asyncio.Semaphore(4)
    await asyncio.gather(*[tts_one(OVERRIDE.get(c, c), cache_path(c), sem) for c in chars])


# ---------------- 分析 ----------------
def read_mp3(path):
    x, sr = sf.read(path, dtype="float32", always_2d=False)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if sr != SR:
        from math import gcd
        from scipy.signal import resample_poly
        g = gcd(SR, sr)
        x = resample_poly(x, SR // g, sr // g).astype(np.float32)
    return x


def trim_silence(x, thresh=0.012):
    idx = np.where(np.abs(x) > thresh)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(0.004 * SR))
    b = min(len(x), idx[-1] + int(0.025 * SR))
    return x[a:b]


def f0_track(x, fmin=90.0, fmax=420.0):
    """逐幀自相關估 f0（Hz；無聲 = 0）"""
    win = int(0.04 * SR)
    hop = int(FRAME * SR)
    n = max(1, (len(x) - win) // hop + 1)
    out = np.zeros(n)
    lo, hi = int(SR / fmax), int(SR / fmin)
    for k in range(n):
        f = x[k * hop:k * hop + win]
        if len(f) < win or np.sqrt(np.mean(f ** 2)) < 0.015:
            continue
        f = f - f.mean()
        ac = np.correlate(f, f, mode="full")[win - 1:]
        if ac[0] <= 0:
            continue
        ac = ac / ac[0]
        seg = ac[lo:hi]
        if len(seg) == 0:
            continue
        j = int(np.argmax(seg))
        if seg[j] < 0.25:          # 週期性不足 → 當無聲（聲母）
            continue
        kk = j + lo
        if 0 < kk < len(ac) - 1:
            a, b, c = ac[kk - 1], ac[kk], ac[kk + 1]
            den = a - 2 * b + c
            kk += 0.5 * (a - c) / den if den != 0 else 0
        out[k] = SR / kk if kk > 0 else 0.0
    return out


def voiced_bounds(f0):
    v = np.where(f0 > 0)[0]
    if len(v) == 0:
        return None
    return int(v[0] * FRAME * SR), int((v[-1] + 1) * FRAME * SR)


def median_f0(f0):
    v = f0[f0 > 0]
    return float(np.median(v)) if len(v) else 0.0


# ---------------- TD-PSOLA ----------------
def spectral_envelope(x, v0, v1):
    """母音段平均幅度譜 + 倒頻譜平滑 → 共振峰包絡（formant 保留）"""
    win = int(0.025 * SR)
    hop = int(0.01 * SR)
    frames = []
    for k in range(v0, max(v0 + 1, v1 - win), hop):
        fr = x[k:k + win]
        if len(fr) < win:
            break
        if np.sqrt(np.mean(fr ** 2)) < 0.01:
            continue
        frames.append(np.abs(np.fft.rfft(fr * np.hanning(win))))
    if not frames:
        fr = x[v0:v0 + win] if len(x[v0:v0 + win]) > 8 else np.pad(x, (0, win))[:win]
        frames = [np.abs(np.fft.rfft(fr * np.hanning(len(fr))))]
    mag = np.mean(frames, axis=0)
    mag = np.maximum(mag, 1e-7)

    # 倒頻譜 lifter（保留前 60 個係數 ≈ 共振峰結構）
    logm = np.log(mag)
    cep = np.fft.irfft(logm)
    keep = 60
    cep[keep:len(cep) - keep] = 0
    env = np.exp(np.maximum(np.fft.rfft(cep).real, -20))
    return env, win


def sing_note(x, f0_src, target_hz, dur_s, prev_hz, seed=0):
    """用母音頻譜包絡 + 目標頻率諧波激勵合成一個音（formant 保留、音高精準）"""
    v = voiced_bounds(f0_track(x))
    v0, v1 = v if v else (0, len(x))
    if v1 - v0 < int(0.04 * SR):
        v0, v1 = 0, len(x)

    env_spec, fft_win = spectral_envelope(x, v0, v1)
    bin_hz = SR / fft_win
    n_out = max(int(dur_s * SR), int(0.05 * SR))

    on_len = int(min(0.08, 0.30 * dur_s) * SR)
    body_n = max(n_out - on_len, int(0.04 * SR))

    # 即時頻率：音頭 glide + 之後顫音
    tt = np.arange(body_n) / SR
    f_inst = np.full(body_n, float(target_hz))
    if prev_hz > 0:
        g = np.clip(tt / 0.07, 0, 1)
        f_inst = np.exp((1 - g) * np.log(prev_hz) + g * np.log(target_hz))
    ramp = np.clip((tt - 0.15) / 0.3, 0, 1)
    f_inst = f_inst * (1.0 + 0.009 * ramp * np.sin(2 * np.pi * 5.2 * tt))

    phase = 2 * np.pi * np.cumsum(f_inst) / SR

    # 諧波：幅度由包絡喺 k*f0 取樣
    rng = np.random.default_rng(seed)
    body = np.zeros(body_n, dtype=np.float64)
    k = 1
    while k * target_hz < SR / 2 - 200:
        fk = k * target_hz
        idx = min(len(env_spec) - 1, int(round(fk / bin_hz)))
        amp = env_spec[idx]
        phi = rng.uniform(0, 2 * np.pi)
        body += amp * np.sin(k * phase + phi)
        k += 1
    if not np.any(body):
        return np.zeros(n_out, dtype=np.float32)

    body /= np.sqrt(np.mean(body ** 2)) + 1e-9

    # 令音量貼近原音節母音
    src_rms = np.sqrt(np.mean(x[v0:v1] ** 2)) + 1e-9
    body *= min(src_rms * 1.6, 0.32)

    # 音頭：保留原聲母（無聲子音先保留，避免帶入錯音高）
    head = np.zeros(on_len, dtype=np.float32)
    if on_len > 0:
        seg = x[:on_len].astype(np.float32).copy()
        f_head = f0_track(x[:on_len]) if on_len > int(0.02 * SR) else np.zeros(1)
        if np.mean(f_head > 0) < 0.2:
            m = min(len(seg), on_len)
            head[:m] = seg[:m] * np.linspace(0, 1, m) ** 0.7
            head *= 0.75
    out = np.concatenate([head, body.astype(np.float32)])

    # 包絡
    a = min(len(out), int(0.014 * SR))
    r = min(len(out), int(0.06 * SR))
    env = np.ones(len(out), dtype=np.float32)
    if a:
        env[:a] = np.linspace(0, 1, a) ** 0.8
    if r:
        env[-r:] *= np.linspace(1, 0, r) ** 1.6
    out = out * env

    rms = np.sqrt(np.mean(out ** 2)) + 1e-9
    return (out / rms * 0.14).astype(np.float32)


# ---------------- 伴奏 ----------------
NOTE_MIDI = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def chord(sym):
    minor = sym.endswith("m")
    name = sym[:-1] if minor else sym
    root = NOTE_MIDI[name[0]] + (1 if "#" in name else 0) + 60
    return root, [root, root + (3 if minor else 4), root + 7]


def accompaniment(total, spb, intro_bars=1):
    prog = ["C"] * intro_bars + ["C", "G", "Am", "Em", "F", "C", "F", "G"]
    bar = 4 * spb
    out = np.zeros(total, dtype=np.float32)

    for i, sym in enumerate(prog):
        s0, s1 = int(i * bar * SR), min(total, int((i + 1) * bar * SR))
        if s1 <= s0:
            break
        st = np.arange(s1 - s0) / SR
        root, tri = chord(sym)

        env = np.minimum(1, st / 0.16) * (0.75 + 0.25 * np.exp(-st / (bar * 0.5)))
        tail = np.clip(((s1 - s0) / SR - st), 0, 0.3) / 0.3
        env *= 0.35 + 0.65 * tail

        pad = np.zeros(s1 - s0, dtype=np.float32)
        for m in tri:
            f = hz(m)
            pad += np.sin(2 * np.pi * f * st) + 0.16 * np.sin(2 * np.pi * 2 * f * st)
        out[s0:s1] += (pad / 3) * env * 0.085

        # 琶音（八分音符）加質感
        arp = [tri[0], tri[1], tri[2], tri[1] * 2]
        steps = int(4 / 0.5)
        for k in range(steps):
            a0 = s0 + int(k * 0.5 * spb * SR)
            n = min(int(0.5 * SR), total - a0)
            if n <= 0:
                break
            at = np.arange(n) / SR
            tone = np.sin(2 * np.pi * hz(arp[k % len(arp)]) * 2 * at) * np.exp(-at / 0.12)
            out[a0:a0 + n] += (tone * 0.045 * np.minimum(1, at / 0.005)).astype(np.float32)

        fb = hz(root - 24)
        bass = np.sin(2 * np.pi * fb * st) * np.exp(-st / (bar * 0.8)) * np.minimum(1, st / 0.02)
        out[s0:s1] += (bass * 0.17).astype(np.float32)

        for beat in (0, 2):
            k0 = s0 + int(beat * spb * SR)
            n = min(int(0.2 * SR), total - k0)
            if n <= 0:
                continue
            kt = np.arange(n) / SR
            fr = 95 * np.exp(-kt / 0.028) + 42
            kick = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-kt / 0.065)
            out[k0:k0 + n] += (kick * 0.24).astype(np.float32)

    return out


def reverb(x, wet=0.14, decay=1.0, seed=7):
    """指數衰減噪音 IR 卷積，加空間感"""
    from scipy.signal import fftconvolve
    rng = np.random.default_rng(seed)
    n = int(decay * SR)
    ir = rng.standard_normal(n).astype(np.float32)
    ir *= np.exp(-np.arange(n) / (0.28 * SR))
    ir[: int(0.02 * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
    wt = fftconvolve(x, ir)[: len(x)].astype(np.float32)
    return (x * (1 - wet) + wt * wet * 3.0).astype(np.float32)


# ---------------- 主流程 ----------------
def target_hz(name):
    m = name[0]
    acc = 1 if len(name) > 2 and name[1] == "#" else 0
    return hz(12 * (int(name[-1]) + 1) + NOTE_MIDI[m] + acc)


def build(song):
    mel = song["chorusMelody"]
    notes = mel["notes"]
    bpm = song.get("meta", {}).get("bpm", 80)
    spb = 60.0 / bpm

    asyncio.run(tts_all([n["s"] for n in notes]))

    intro = 4  # 一小節前奏（拍）
    total = int((sum(n["d"] for n in notes) + intro) * spb * SR) + int(1.0 * SR)
    vocal = np.zeros(total, dtype=np.float32)

    pos = intro * spb
    prev = 0.0
    for n in notes:
        x = trim_silence(read_mp3(cache_path(n["s"])))
        base = median_f0(f0_track(x))
        # 新方法音高同共振峰已解耦，直接用記譜音域（C4–C5，女聲舒服位置）
        target = target_hz(n["n"]) * (2 ** float(os.environ.get("VOCAL_OCTAVE", "0")))
        dur = n["d"] * spb
        seg = sing_note(x, base, target, dur, prev, seed=int(pos * 1000))

        s0 = int(pos * SR)
        s1 = min(total, s0 + len(seg))
        if s1 > s0:
            vocal[s0:s1] += seg[: s1 - s0]
        pos += dur
        prev = target

    acc = accompaniment(total, spb, intro_bars=1)
    stem = vocal.copy()
    # 人聲略前，伴奏墊底
    mix = reverb(vocal * 0.60 + acc * 1.05, 0.14, 1.0)

    pk = np.abs(mix).max()
    if pk > 0:
        mix *= 0.90 / pk
    f = int(0.4 * SR)
    mix[-f:] *= np.linspace(1, 0, f)
    mix[:200] *= np.linspace(0, 1, 200)

    if os.environ.get("STEM"):
        sv = stem / (np.abs(stem).max() or 1.0) * 0.9
        sf.write(os.environ["STEM"], sv, SR, subtype="PCM_16")

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "%s-vocal.wav" % song["id"])
    sf.write(path, mix, SR, subtype="PCM_16")
    print("→ %s (%.1fs, %.0f KB)" % (path, total / SR, os.path.getsize(path) / 1024))
    return path


if __name__ == "__main__":
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for s in load_songs():
        if not s.get("chorusMelody") or (only and s["id"] != only):
            continue
        build(s)
