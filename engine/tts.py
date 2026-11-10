"""Narração frase a frase no ElevenLabs. Uso:  python3 -m engine.tts episodios/NN-nome
Gera build/vo_<cena>_<frase>_0.wav (PCM 24 kHz). Só gasta crédito do que mudou (cache por hash do texto/voz/modelo).
A chave fica em ~/.elevenlabs_key (nunca no repositório nem no chat)."""
import hashlib, json, os, sys, urllib.error, urllib.request, wave
from .episode import Episode

KEYFILE = os.path.expanduser("~/.elevenlabs_key")

def synth(text, fn, cfg, key):
    tag = hashlib.sha1(f"{cfg['voice_id']}|{cfg['model_id']}|False|{text}".encode()).hexdigest()
    if os.path.exists(fn) and os.path.exists(fn + ".sha") and open(fn + ".sha").read() == tag:
        return False
    body = json.dumps({"text": text, "model_id": cfg["model_id"], "language_code": cfg["language"],
                       "voice_settings": {"stability": cfg["stability"], "similarity_boost": cfg["similarity"], "style": cfg["style"],
                                          "use_speaker_boost": True, "speed": cfg["voice_speed"]}}).encode()
    req = urllib.request.Request(f"https://api.elevenlabs.io/v1/text-to-speech/{cfg['voice_id']}?output_format=pcm_24000",
                                 data=body, headers={"xi-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r: pcm = r.read()
    with wave.open(fn, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
    open(fn + ".sha", "w").write(tag)
    return True

def run(ep):
    if not os.path.exists(KEYFILE): raise SystemExit(f"Chave do ElevenLabs não encontrada em {KEYFILE}")
    key = open(KEYFILE).read().strip()
    new = 0
    for s in ep.scenes:
        for k, p in enumerate(s.phrases):
            fn = str(ep.build / f"vo_{s.id}_{k}_0.wav")
            try:
                fresh = synth(p["text"].strip(), fn, ep.cfg, key)
            except urllib.error.HTTPError as e:
                raise SystemExit(f"ElevenLabs recusou ({e.code}): {e.read().decode(errors='ignore')[:300]}")
            new += fresh
            print("novo " if fresh else "cache", s.id, k, p["text"][:60])
    print(f"narração pronta: {new} frases geradas agora, o resto veio do cache")

if __name__ == "__main__":
    run(Episode(sys.argv[1]))
