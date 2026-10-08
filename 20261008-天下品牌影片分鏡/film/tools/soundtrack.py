"""產生 90 秒示意配樂與音效（依分鏡表「聲音」欄）。用法：python3 soundtrack.py 輸出.wav
正式版請換成作曲配樂與旁白錄音；時間點與分鏡表相同。"""
import sys, wave
import numpy as np

SR = 48000
DUR = 90.0
N = int(SR * DUR)
rng = np.random.default_rng(3)
L = np.zeros(N); R = np.zeros(N)

def add(sig, t, pan=0.0, gain=1.0):
    i = int(t * SR); j = min(N, i + len(sig))
    if i >= N: return
    s = sig[: j - i] * gain
    L[i:j] += s * np.sqrt((1 - pan) / 2); R[i:j] += s * np.sqrt((1 + pan) / 2)

def env(n, a=0.005, decay=1.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / decay)

def tone(freq, dur, decay=0.6, harm=(1, .35, .12), a=0.005):
    n = int(dur * SR); t = np.arange(n) / SR
    s = sum(h * np.sin(2 * np.pi * freq * (k + 1) * t) for k, h in enumerate(harm))
    return s * env(n, a, decay)

def piano(freq, dur=2.5, decay=1.1):
    return tone(freq, dur, decay, (1, .45, .18, .08), 0.004)

def pad(freqs, dur, a=1.2):
    n = int(dur * SR); t = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * t + i) + .3 * np.sin(2 * np.pi * f * 2.003 * t) for i, f in enumerate(freqs)) / len(freqs)
    e = np.minimum(1, t / a) * np.minimum(1, (dur - t) / a)
    return s * np.clip(e, 0, 1)

def noise_click(dur=0.012, bright=0.6):
    n = int(dur * SR); x = rng.standard_normal(n)
    x = x - bright * np.concatenate([[0], x[:-1]])
    return x * env(n, 0.0005, dur / 4)

def hz(note):  # MIDI → Hz
    return 440 * 2 ** ((note - 69) / 12)

# 0–13 秒：通知音一層層疊加，8 秒後逐漸壓低
t = 0.3
while t < 12.6:
    density = 0.9 - 0.75 * min(1, t / 7)
    g = 0.11 * (1 if t < 8 else max(0.08, 1 - (t - 8) / 4.6))
    f = rng.choice([1318.5, 1567.98, 1760, 2093, 1174.7])
    blip = np.concatenate([tone(f, .09, .05, (1, .2)), tone(f * 1.25, .16, .07, (1, .2))])
    add(blip, t, pan=rng.uniform(-.7, .7), gain=g)
    t += rng.uniform(.4, 1.0) * density + 0.05

# 13–18 秒：細碎打字聲
t = 14.1
while t < 17.3:
    add(noise_click(), t, pan=rng.uniform(-.2, .2), gain=0.05)
    t += rng.uniform(.035, .09)

# 18–21 秒：低鳴淡出；21–22 秒完全靜音
add(pad([hz(45), hz(52)], 3.2, a=1.0), 17.9, gain=0.05)

# 24 秒起：主旋律（F 大調，每小節 2 秒），隨段落逐漸加厚
chords = [[53, 57, 60, 65], [50, 57, 62, 65], [46, 53, 58, 62], [48, 55, 60, 64]]  # F, Dm, Bb, C
melody = [72, 69, 70, 72, 74, 72, 70, 69, 67, 69, 72, 77, 76, 74, 72, 70]
bar = 2.0
start = 24.0
k = 0
tb = start
while tb < 79.0:
    ch = chords[k % 4]
    intensity = 0.55 + 0.45 * np.clip((tb - 24) / 48, 0, 1)
    for i, n in enumerate(ch[1:]):
        add(piano(hz(n), 2.4, 1.0), tb + i * 0.18, pan=-.3 + .3 * i, gain=0.045 * intensity)
    add(piano(hz(ch[0] - 12), 2.6, 1.6), tb, gain=0.07 * intensity)
    if tb >= 31:  # 第二段起加入旋律
        m = melody[k % len(melody)]
        add(piano(hz(m), 1.8, .9), tb + 0.0, pan=.15, gain=0.05 * intensity)
        add(piano(hz(melody[(k + 3) % len(melody)]), 1.4, .7), tb + 1.0, pan=.15, gain=0.035 * intensity)
    if tb >= 44:  # 鏡頭 9 起：鋪底和弦漸強
        add(pad([hz(n) for n in ch[1:]], bar + .4, a=.6), tb, gain=0.035 * intensity)
    tb += bar; k += 1

# 鏡頭 8：每次圈選的筆觸聲
for tc in (37.7, 38.7, 39.7):
    n = int(.5 * SR); x = rng.standard_normal(n)
    x = np.convolve(x, np.ones(30) / 30, mode="same") * np.hanning(n)
    add(x, tc, pan=.2, gain=0.12)

# 鏡頭 10：每通過一道關卡一個輕音
for tc, n in ((57.8, 84), (59.0, 86), (60.2, 89)):
    add(tone(hz(n), 1.5, .5, (1, .25)), tc, gain=0.06)

# 鏡頭 13：旋律收到只剩單音
add(pad([hz(65), hz(72)], 3.0, a=.8), 79.0, gain=0.04)
add(tone(hz(72), 4.5, 1.8, (1, .2)), 81.2, gain=0.06)

# 鏡頭 15：結尾單音
add(tone(hz(77), 3.2, 1.4, (1, .3, .1)), 87.0, gain=0.08)
add(tone(hz(65), 3.2, 1.6, (1, .2)), 87.0, gain=0.05)

# 簡單殘響
def reverb(x):
    out = x.copy()
    for d, g in ((0.031, .35), (0.047, .3), (0.071, .25), (0.113, .2), (0.167, .15), (0.241, .1)):
        k = int(d * SR); out[k:] += x[:-k] * g
    return out
L, R = reverb(L), reverb(R)

# 21–22 秒保持靜音（鏡頭 5 游標變紅）
for ch in (L, R):
    a, b = int(20.8 * SR), int(22.0 * SR)
    ch[a:b] = 0
    ch[int(20.5 * SR):a] *= np.linspace(1, 0, a - int(20.5 * SR))
    # 最後 0.5 秒淡出
    ch[-SR // 2:] *= np.linspace(1, 0, SR // 2)

peak = max(np.abs(L).max(), np.abs(R).max())
L, R = L / peak * 0.7, R / peak * 0.7
pcm = (np.stack([L, R], axis=1) * 32767).astype(np.int16)
with wave.open(sys.argv[1], "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
