import json, os, re, subprocess, numpy as np, soundfile as sf
from script import SCENES, parts, clean

SR = 48000
B = "build"
rng = np.random.default_rng(77)

def sox(*a): subprocess.run(["sox", *a], check=True, stderr=subprocess.DEVNULL)

# ---- tratamento das vozes ----
TRIM = ["silence", "1", "0.02", "0.3%", "reverse", "silence", "1", "0.02", "0.3%", "reverse"]

def natural_voice(src, dst):
    """Narração limpa, próxima do microfone, com leve compressão e corpo nos graves."""
    sox(src, "-r", str(SR), dst, *TRIM, "highpass", "70", "bass", "+3", "150", "treble", "-1",
        "compand", "0.01,0.15", "-60,-60,-30,-15,-10,-8", "-3", "gain", "-n", "-2")

def demon_voice(src, dst):
    """Voz demoníaca: 3 camadas (grave rouca, sub-grave, sussurro agudo atrasado) + sala grande."""
    a, b, c, m = (f"{dst}.{x}.wav" for x in "abcm")
    sox(src, "-r", str(SR), a, *TRIM, "pitch", "-650", "bass", "+8", "110", "overdrive", "10",
        "lowpass", "4200", "gain", "-n", "-1")
    sox(src, "-r", str(SR), b, *TRIM, "pitch", "-1300", "bass", "+6", "90", "lowpass", "2500", "gain", "-n", "-5")
    sox(src, "-r", str(SR), c, *TRIM, "pitch", "+250", "highpass", "700", "lowpass", "4500",
        "delay", "0.035", "reverb", "50", "50", "100", "gain", "-n", "-14")
    sox("-m", a, b, c, m)
    sox(m, dst, "reverb", "45", "40", "100", "100", "12", "0",
        "compand", "0.01,0.2", "-60,-60,-30,-10,-6,-3", "-2", "gain", "-n", "-1")

def vowels(w): return max(1, len(re.findall(r"[aeiouáéíóúâêôãõà]", w.lower())))
def word_times(text, dur):
    ws = text.split(); v = np.array([vowels(w) + 0.4 for w in ws], float)
    starts = np.concatenate([[0], np.cumsum(v)[:-1]]) / v.sum() * dur
    return list(starts)

GAP = int(0.12 * SR)
phr, phr_dem = {}, {}
for sid, phrases in SCENES:
    for k, (txt, *_r) in enumerate(phrases):
        xs, dem, pos = [], [], 0
        for j, (seg, is_demon) in enumerate(parts(txt)):
            src, dst = f"{B}/vo_{sid}_{k}_{j}.wav", f"{B}/vp_{sid}_{k}_{j}.wav"
            (demon_voice if is_demon else natural_voice)(src, dst)
            if sid == "end":  # "Temos vagas" bem lento
                sox(dst, f"{B}/vp_end_slow.wav", "tempo", "-s", "0.85"); dst = f"{B}/vp_end_slow.wav"
            x, _ = sf.read(dst)
            if x.ndim > 1: x = x.mean(1)
            if is_demon: x = x * 1.15
            if j > 0: xs.append(np.zeros(GAP)); pos += GAP
            if is_demon: dem.append((pos / SR, (pos + len(x)) / SR))
            xs.append(x); pos += len(x)
        phr[(sid, k)] = np.concatenate(xs); phr_dem[(sid, k)] = dem

# ---- linha do tempo (as imagens trocam junto com as frases) ----
LEAD = {"intro": 0.9, "end": 0.9}; TAIL = {"intro": 0.1, "end": 2.4}
timeline, t = [], 0.0
for sid, phrases in SCENES:
    s = {"id": sid, "start": t, "phrases": []}
    t += LEAD.get(sid, 0.3)
    for k, (txt, screen, img, look, pause) in enumerate(phrases):
        x = phr[(sid, k)]; d = len(x) / SR
        s["phrases"].append({"text": screen, "img": img, "look": look,
                             "title": screen.startswith(("REGRA N", "E por último", "DIÁRIA", "ALUGUEL")),
                             "start": t, "end": t + d,
                             "words": [t + w for w in word_times(clean(txt), d)],
                             "dem": [[t + a, t + b] for a, b in phr_dem[(sid, k)]]})
        t += d + pause
    t += TAIL.get(sid, 0.15)
    s["end"] = t; timeline.append(s)
TOTAL = t; N = int(TOTAL * SR) + SR
S = {s["id"]: s for s in timeline}
def P(sid, k): return S[sid]["phrases"][k]
def ease(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)

# ---- âncoras compartilhadas com o vídeo ----
A = {}
A["dem_iv"] = [iv for s in timeline for p in s["phrases"] for iv in p["dem"]]
A["cuts"] = [max(0.0, p["start"] - 0.25) if (si or k) else 0.0
             for si, s in enumerate(timeline) for k, p in enumerate(s["phrases"])]
A["titles"] = [p["start"] for s in timeline for p in s["phrases"] if p["title"]]
A["knocks"] = ([P("r4", 1)["end"] + 0.25 + 0.42 * i for i in range(3)] +     # "alguém vai bater na sua porta"
               [P("r5", 2)["end"] + 0.15 + 0.33 * i for i in range(4)])
A["elev"] = (P("r1", 1)["start"], P("r1", 2)["start"] + 1.0)               # o elevador desce
A["stop"] = P("r1", 2)["words"][2]                                         # "parar": ding e a porta desliza
A["creak"] = P("r2", 2)["start"]                                           # a porta do outro quarto range
A["steps"] = (P("r3", 2)["start"] + 0.2, P("r3", 2)["start"] + 3.6)        # passos no teto
A["pen"] = (P("r5", 1)["start"], P("r5", 1)["end"])                        # a caneta escrevendo o aviso

# ---- helpers de som ----
def T(sec): return np.arange(int(sec * SR)) / SR
def place(buf, x, at, g=1.0):
    i = int(at * SR); j = min(len(buf), i + len(x))
    if j > i >= 0: buf[i:j] += x[: j - i] * g
def env(n, a=0.01, r=0.1):
    e = np.ones(n); na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e
def filt(x, lo=0, hi=None):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(f)
    if lo: m *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi: m *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(X * m, len(x))

# ---- voz seca + respirações, depois sala ----
voice = np.zeros(N)
def breath(d=0.45, g=0.05):
    x = filt(rng.standard_normal(int(d * SR)), 400, 2600)
    return x * np.sin(np.linspace(0, np.pi, len(x))) ** 1.5 * g
for s in timeline:
    for k, p in enumerate(s["phrases"]):
        place(voice, phr[(s["id"], k)], p["start"])
        if k == 0 and s["id"] in ("intro", "r5", "end"):
            place(voice, breath(0.42, 0.04), p["start"] - 0.5)
sf.write(f"{B}/voice_dry.wav", voice.astype(np.float32), SR)
sox(f"{B}/voice_dry.wav", f"{B}/voice_wet.wav", "reverb", "20", "50", "40", "100", "8", "0",
    "echo", "0.85", "0.8", "60", "0.10", "gain", "-n", "-1")
voice, _ = sf.read(f"{B}/voice_wet.wav")
if voice.ndim > 1: voice = voice.mean(1)
voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]

# ---- trilha: drone, vento, grilos distantes e chiado de fita ----
tt = np.arange(N) / SR
swell = np.clip(tt / TOTAL, 0, 1) ** 1.5
drone = (np.sin(2 * np.pi * 49 * tt) + 0.7 * np.sin(2 * np.pi * 49.6 * tt + 1) +
         0.35 * np.sin(2 * np.pi * 73.4 * tt)) * (0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * tt) ** 2)
wind = filt(rng.standard_normal(N), 150, 900) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.11 * tt + 2) ** 2)
buzz = filt(0.03 * np.sign(np.sin(2 * np.pi * 120 * tt)) + 0.04 * np.sin(2 * np.pi * 240 * tt), 0, 1200)
hiss = filt(rng.standard_normal(N), 3000, 9000) * 0.5
crick = np.sin(2 * np.pi * 4300 * tt) * (np.sin(2 * np.pi * 14 * tt) > 0.2) * (np.sin(2 * np.pi * 0.6 * tt) > 0.3) * 0.004
bed = drone * (0.06 + 0.08 * swell) + wind * 0.05 + buzz * 0.5 + hiss * 0.010 + crick

sfx = np.zeros(N)
def glitch_whoosh(at, g=0.4):
    d = 0.22; n = int(d * SR); x = T(d)
    nz = filt(rng.standard_normal(n), 600, 7000) * np.sin(np.pi * x / d) ** 1.5
    place(sfx, nz * 0.6 + np.sin(2 * np.pi * (300 + 900 * x / d) * x) * 0.05, at, g)
def title_hit(at, g=0.8):
    x = T(1.6)
    place(sfx, np.sin(2 * np.pi * (46 + 40 * np.exp(-x * 8)) * x) * np.exp(-x * 3) +
          filt(rng.standard_normal(len(x)), 0, 400) * np.exp(-x * 5) * 1.5, at, g)
def growl(at, g=0.5):
    x = T(0.9); n = len(x)
    sub = np.sin(2 * np.pi * (38 + 10 * np.sin(x * 9)) * x) * np.exp(-x * 2.2)
    gr = filt(rng.standard_normal(n) * np.sin(2 * np.pi * 28 * x) ** 2, 80, 900) * np.exp(-x * 3) * 2
    place(sfx, sub + gr, at - 0.05, g)
def knock(power=1.0):
    x = T(0.22)
    thump = np.sin(2 * np.pi * (95 + 60 * np.exp(-x * 40)) * x) * np.exp(-x * 28)
    glass = filt(rng.standard_normal(len(x)), 1200, 4500) * np.exp(-x * 60) * 0.5
    ring = (np.sin(2 * np.pi * 2310 * x) + 0.6 * np.sin(2 * np.pi * 3470 * x)) * np.exp(-x * 18) * 0.08
    return (thump + glass + ring) * power
def phone(at, g=0.35):
    x = T(1.0)
    tone = np.sin(2 * np.pi * 425 * x) * (np.sin(2 * np.pi * 20 * x) > 0) * env(len(x), 0.01, 0.05)
    place(sfx, filt(tone, 300, 3000), at, g)
def truck(start, stop, end):
    d = end - start; x = T(d); n = len(x)
    rpm = np.where(x < stop - start, 1.0 - 0.45 * (x / (stop - start)) ** 2, 0.55)
    ph = np.cumsum(2 * np.pi * 31 * rpm / SR)
    eng = np.sin(ph) + 0.5 * np.sin(2 * ph + 0.4) + 0.09 * np.sign(np.sin(3 * ph))
    eng = filt(eng + filt(rng.standard_normal(n), 0, 140) * 3 * rpm, 0, 400)
    vol = np.where(x < stop - start, 0.2 + 0.8 * np.clip(x / 2.5, 0, 1) ** 1.3, 0.7)
    place(sfx, eng * vol * env(n, 0.5, 1.0), start, 0.55)
    xb = T(1.2); place(sfx, filt(rng.standard_normal(len(xb)), 2500, 9000) * env(len(xb), 0.01, 0.8), stop + 0.1, 0.28)
def elevator(start, end, g=0.45):
    d = end - start; x = T(d); n = len(x)
    f = 50 + 8 * np.sin(x * 3)
    ph = np.cumsum(2 * np.pi * f / SR)
    mot = np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.15 * np.sign(np.sin(3 * ph))
    mot = filt(mot + filt(rng.standard_normal(n), 0, 200) * 1.5, 0, 500) * env(n, 0.4, 0.5)
    place(sfx, mot, start, g)
def ding(at, g=0.35):
    x = T(1.4)
    place(sfx, (np.sin(2 * np.pi * 880 * x) + 0.4 * np.sin(2 * np.pi * 1760 * x)) * np.exp(-x * 4), at, g)
    place(sfx, (np.sin(2 * np.pi * 660 * x) + 0.3 * np.sin(2 * np.pi * 1320 * x)) * np.exp(-x * 4), at + 0.35, g)
def door_slide(at, d=1.1, g=0.4):
    n = int(d * SR); x = T(d)
    v = filt(rng.standard_normal(n), 600, 3200) * np.sin(np.pi * x / d) ** 0.7
    place(sfx, v, at, g)
def steps_above(start, end, g=0.45):
    t0 = start
    while t0 < end:
        x = T(0.3)
        th = np.sin(2 * np.pi * (55 + 25 * np.exp(-x * 30)) * x) * np.exp(-x * 14) + filt(rng.standard_normal(len(x)), 80, 450) * np.exp(-x * 25) * 0.8
        place(sfx, th, t0, g * (0.7 + 0.5 * rng.random()))
        t0 += 0.5 + 0.2 * rng.random()
def creak(at, d=1.4, g=0.25):
    x = T(d); n = len(x)
    f = 420 + 260 * np.sin(np.pi * x / d) + 40 * np.sin(x * 40)
    ph = np.cumsum(2 * np.pi * f / SR)
    v = (np.sign(np.sin(ph)) * 0.4 + np.sin(ph) * 0.6) * (0.5 + 0.5 * np.sin(2 * np.pi * 9 * x)) * np.sin(np.pi * x / d)
    place(sfx, filt(v, 300, 2500), at, g)
def pen(start, end, g=0.13):
    d = end - start; n = int(d * SR); x = T(d)
    v = filt(rng.standard_normal(n), 2500, 7500) * (0.4 + 0.6 * np.sin(2 * np.pi * 7 * x) ** 2) * (rng.random(n) > 0.0) * env(n, 0.05, 0.2)
    place(sfx, v, start, g)
def heartbeat(a, b, g=0.45):
    t0 = a
    while t0 < b:
        x = T(0.18); bt = np.sin(2 * np.pi * 52 * x) * np.exp(-x * 25)
        place(sfx, bt, t0, g); place(sfx, bt, t0 + 0.24, g * 0.7)
        t0 += 0.95 - 0.25 * (t0 - a) / max(b - a, 1)
def boom(at, g=0.9):
    x = T(3.5)
    place(sfx, np.sin(2 * np.pi * (34 + 50 * np.exp(-x * 6)) * x) * np.exp(-x * 1.3) + filt(rng.standard_normal(len(x)), 0, 300) * np.exp(-x * 2) * 3, at, g)
def screech(at, d=1.6, g=0.08):
    x = T(d); s_ = sum(np.sin(2 * np.pi * f * x + p) for f, p in [(1870, 0), (1913, 1), (2540, 2)])
    place(sfx, s_ * env(len(x), 0.4, 0.6), at, g)

for c in A["cuts"][1:]: glitch_whoosh(c)
for tm in A["titles"]: title_hit(tm - 0.05)
for a, b in A["dem_iv"]: growl(a)
elevator(*A["elev"]); ding(A["stop"] + 0.1); door_slide(A["stop"] + 0.5)
creak(A["creak"])
steps_above(*A["steps"])
pen(*A["pen"])
for i, k in enumerate(A["knocks"]):
    place(sfx, knock((0.7 if i < 3 else 1.0) * (1 + 0.08 * rng.standard_normal())), k)
heartbeat(S["r3"]["start"], S["r5"]["end"])
boom(P("end", 0)["start"] - 0.05); screech(P("end", 0)["start"] - 0.4)

cut = np.ones(N); cut[int(S["end"]["start"] * SR):] = 0.25
bed *= filt(cut, 0, 3)
mix = voice * 1.0 + bed + sfx * 0.6
fo = int(1.2 * SR); mix[int(TOTAL * SR) - fo:int(TOTAL * SR)] *= np.linspace(1, 0, fo); mix[int(TOTAL * SR):] = 0
mix = np.tanh(mix * 1.1); mix = mix / np.abs(mix).max() * 0.89
sf.write(f"{B}/mix.wav", mix[:int(TOTAL * SR)].astype(np.float32), SR)
json.dump({"total": TOTAL, "scenes": timeline, "anchors": A}, open(f"{B}/timeline.json", "w"), indent=1, ensure_ascii=False)
print("total", round(TOTAL, 2), "voz:", open(f"{B}/VOICE_SOURCE").read() if os.path.exists(f"{B}/VOICE_SOURCE") else "?")
for s in timeline: print(s["id"], round(s["start"], 2), round(s["end"], 2), [round(p["end"] - p["start"], 2) for p in s["phrases"]])
