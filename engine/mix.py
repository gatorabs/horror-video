"""Mixagem: narração tratada + trilha contínua (drone, vento, chiado) + efeitos presos ao texto (batimento, impactos).
Uso:  python3 -m engine.mix episodios/NN-nome     (precisa de sox; roda no WSL)
Gera build/mix.wav e build/timeline.json (tempos de cada cena/frase/palavra, que o render usa)."""
import json, re, subprocess, sys
import numpy as np, soundfile as sf
from .episode import Episode

SR = 48000
TRIM = ["silence", "1", "0.02", "0.3%", "reverse", "silence", "1", "0.02", "0.3%", "reverse"]

def sox(*a): subprocess.run(["sox", *a], check=True, stderr=subprocess.DEVNULL)

def natural_voice(src, dst):
    sox(src, "-r", str(SR), dst, *TRIM, "highpass", "70", "bass", "+3", "150", "treble", "-1",
        "compand", "0.01,0.15", "-60,-60,-30,-15,-10,-8", "-3", "gain", "-n", "-2")

def vowels(w): return max(1, len(re.findall(r"[aeiouáéíóúâêôãõà]", w.lower())))
def word_times(text, dur):
    """Tempo de início de cada palavra: peso = sílabas + pausa que a voz faz depois de vírgula/ponto."""
    ws = text.split()
    v = np.array([vowels(w) + 0.4 + (1.3 if w.endswith((",", ":", ";")) else 2.2 if w.endswith((".", "?", "!", "…")) and i < len(ws) - 1 else 0)
                  for i, w in enumerate(ws)], float)
    return list(np.concatenate([[0], np.cumsum(v)[:-1]]) / v.sum() * dur)

def run(ep):
    B, cfg = str(ep.build), ep.cfg
    rng = np.random.default_rng(404)
    end_id = cfg["end_scene"]
    phr = {}
    for s in ep.scenes:
        for k, p in enumerate(s.phrases):
            src, dst = f"{B}/vo_{s.id}_{k}_0.wav", f"{B}/vp_{s.id}_{k}_0.wav"
            natural_voice(src, dst)
            if s.id == end_id:
                sox(dst, f"{B}/vp_end_slow.wav", "tempo", "-s", "0.88"); dst = f"{B}/vp_end_slow.wav"
            x, _ = sf.read(dst)
            phr[(s.id, k)] = x.mean(1) if x.ndim > 1 else x

    # ---- linha do tempo
    timeline, t = [], 0.0
    lead = {ep.scenes[0].id: cfg["intro_time"], **cfg["lead"]}
    for s in ep.scenes:
        sc = {"id": s.id, "start": t, "phrases": []}
        t += lead.get(s.id, 0.35)
        for k, p in enumerate(s.phrases):
            x = phr[(s.id, k)]; d = len(x) / SR
            sc["phrases"].append({"text": p["screen"], "look": s.look, "title": p["screen"] in cfg["cards"],
                                  "start": t, "end": t + d, "words": [t + w for w in word_times(p["text"], d)]})
            t += d + p["pause"]
        t += cfg["tail"].get(s.id, 0.2)
        sc["end"] = t; timeline.append(sc)
    TOTAL = t; N = int(TOTAL * SR) + SR
    S = {s["id"]: s for s in timeline}
    def when(ref):
        sid, k, w, dt = ref
        p = S[sid]["phrases"][k]
        return (p["start"] if w is None else p["words"][w]) + dt

    hits = [when(h) for h in ep.hits]
    A = {"cuts": [0.0 if i == 0 else max(0.0, s["phrases"][0]["start"] - 0.3) for i, s in enumerate(timeline)],
         "titles": [p["start"] for s in timeline for p in s["phrases"] if p["title"]],
         "intro_title": [0.3, cfg["intro_time"]], "hits": hits, "knocks": hits}

    # ---- sons
    def T(sec): return np.arange(int(sec * SR)) / SR
    def place(buf, x, at, g=1.0):
        i = int(at * SR); j = min(len(buf), i + len(x))
        if j > i >= 0: buf[i:j] += x[: j - i] * g
    def filt(x, lo=0, hi=None):
        X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); m = np.ones_like(f)
        if lo: m *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
        if hi: m *= 1 / (1 + (f / hi) ** 4)
        return np.fft.irfft(X * m, len(x))

    voice = np.zeros(N)
    for s in timeline:
        for k, p in enumerate(s["phrases"]): place(voice, phr[(s["id"], k)], p["start"])
    sf.write(f"{B}/voice_dry.wav", voice.astype(np.float32), SR)
    sox(f"{B}/voice_dry.wav", f"{B}/voice_wet.wav", "reverb", "14", "50", "40", "100", "6", "0", "gain", "-n", "-1")
    voice, _ = sf.read(f"{B}/voice_wet.wav")
    if voice.ndim > 1: voice = voice.mean(1)
    voice = np.pad(voice, (0, max(0, N - len(voice))))[:N]

    tt = np.arange(N) / SR
    swell = np.clip(tt / TOTAL, 0, 1) ** 1.3
    drone = (np.sin(2 * np.pi * 49 * tt) + 0.7 * np.sin(2 * np.pi * 49.6 * tt + 1) + 0.35 * np.sin(2 * np.pi * 73.4 * tt)) \
            * (0.6 + 0.4 * np.sin(2 * np.pi * 0.05 * tt) ** 2)
    wind = filt(rng.standard_normal(N), 150, 900) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * tt + 2) ** 2)
    hiss = filt(rng.standard_normal(N), 3000, 9000) * 0.5
    dark = filt(rng.standard_normal(N), 40, 220) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.03 * tt) ** 2)
    bed = drone * (0.05 + 0.09 * swell) + wind * (0.04 + 0.03 * swell) + hiss * 0.008 + dark * 0.05 * swell

    sfx = np.zeros(N)
    def boom(at, g=0.9):
        x = T(3.2)
        place(sfx, np.sin(2 * np.pi * (34 + 50 * np.exp(-x * 6)) * x) * np.exp(-x * 1.3) + filt(rng.standard_normal(len(x)), 0, 300) * np.exp(-x * 2) * 3, at - 0.03, g)
    def whoosh(at, g=0.25):
        d = 0.5; x = T(d)
        place(sfx, filt(rng.standard_normal(len(x)), 400, 5000) * np.sin(np.pi * x / d) ** 2, at, g)
    def heartbeat(a, b, g=0.4):
        t0 = a
        while t0 < b:
            x = T(0.18); bt = np.sin(2 * np.pi * 52 * x) * np.exp(-x * 25)
            place(sfx, bt, t0, g); place(sfx, bt, t0 + 0.24, g * 0.7)
            t0 += 1.0 - 0.3 * (t0 - a) / max(b - a, 1)
    def screech(at, d=1.8, g=0.06):
        x = T(d); s_ = sum(np.sin(2 * np.pi * f * x + p) for f, p in [(1870, 0), (1913, 1), (2540, 2)])
        place(sfx, s_ * np.minimum(1, x / 0.4) * np.minimum(1, (d - x) / 0.6), at, g)

    for c in A["cuts"][1:]: whoosh(c - 0.05)
    for h in hits: boom(h)
    if cfg["title"]: boom(0.3, 0.6)
    for tm in A["titles"]: boom(tm - 0.05, 0.7)
    if cfg["heart"]: heartbeat(S[cfg["heart"][0]]["start"], S[cfg["heart"][1]]["end"])
    for ref in cfg["screeches"]: screech(when(ref) + 0.3)

    mix = voice * 1.0 + bed + sfx * 0.6
    fo = int(2.0 * SR); mix[int(TOTAL * SR) - fo:int(TOTAL * SR)] *= np.linspace(1, 0, fo); mix[int(TOTAL * SR):] = 0
    mix = np.tanh(mix * 1.1); mix = mix / np.abs(mix).max() * 0.89
    sf.write(f"{B}/mix.wav", mix[:int(TOTAL * SR)].astype(np.float32), SR)
    json.dump({"total": TOTAL, "scenes": timeline, "anchors": A}, open(f"{B}/timeline.json", "w"), indent=1, ensure_ascii=False)
    print(f"mix pronto: {TOTAL:.1f}s = {TOTAL / 60:.2f} min")

if __name__ == "__main__":
    run(Episode(sys.argv[1]))
