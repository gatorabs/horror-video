import os, sys, json, wave, hashlib, subprocess, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from script import SCENES, parts

# Narração trecho por trecho (vo_{cena}_{frase}_{trecho}.wav).
# 1) ElevenLabs, se houver chave em ~/.elevenlabs_key e plano que permita a voz (VOICE_ID abaixo).
# 2) Se a API recusar (ex.: plano gratuito + voz da biblioteca) cai para o Piper "jeff" como RASCUNHO
#    e grava build/VOICE_SOURCE = "piper". Só publique com build/VOICE_SOURCE = "eleven".
# Para forçar um dos dois: VOICE=piper  ou  VOICE=eleven.
VOICE_ID = "EbiSUflQjzm4g7S895SC"
MODEL_ID = "eleven_multilingual_v2"
KEYFILE = os.path.expanduser("~/.elevenlabs_key")
PIPER_MODEL = os.path.expanduser("~/piper-voices/pt_BR-jeff-medium/pt_BR-jeff-medium.onnx")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "build")
os.makedirs(OUT, exist_ok=True)

def eleven(text, fn, demon, key):
    """Gera 1 trecho no ElevenLabs (PCM 24 kHz). Só gasta crédito se o texto/voz mudou (cache por hash)."""
    tag = hashlib.sha1(f"{VOICE_ID}|{MODEL_ID}|{demon}|{text}".encode()).hexdigest()
    if os.path.exists(fn) and os.path.exists(fn + ".sha") and open(fn + ".sha").read() == tag:
        return
    body = json.dumps({"text": text, "model_id": MODEL_ID, "language_code": "pt",
                       "voice_settings": {"stability": 0.4, "similarity_boost": 0.8, "style": 0.35,
                                          "use_speaker_boost": True, "speed": 0.8 if demon else 0.92}}).encode()
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}?output_format=pcm_24000",
        data=body, headers={"xi-api-key": key, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r: pcm = r.read()
    with wave.open(fn, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(pcm)
    open(fn + ".sha", "w").write(tag)

def piper(text, fn, demon):
    subprocess.run([sys.executable, "-m", "piper", "-m", PIPER_MODEL, "--length-scale", "1.8" if demon else "1.3",
                    "--noise-scale", "0.7", "--noise-w", "0.8", "-f", fn],
                   input=text.encode(), check=True, stderr=subprocess.DEVNULL)

want = os.environ.get("VOICE", "auto")
key = open(KEYFILE).read().strip() if os.path.exists(KEYFILE) else ""
use_eleven = want != "piper" and bool(key)
source = "eleven" if use_eleven else "piper"
for sid, phrases in SCENES:
    for k, (txt, *_r) in enumerate(phrases):
        for j, (seg, demon) in enumerate(parts(txt)):
            fn = os.path.join(OUT, f"vo_{sid}_{k}_{j}.wav")
            if use_eleven:
                try:
                    eleven(seg, fn, demon, key)
                except urllib.error.HTTPError as e:
                    msg = e.read().decode(errors="ignore")[:300]
                    if want == "eleven":
                        raise SystemExit(f"ElevenLabs recusou ({e.code}): {msg}")
                    print(f"!! ElevenLabs recusou ({e.code}): {msg}\n!! Caindo para o Piper (RASCUNHO).")
                    use_eleven, source = False, "piper"
                    piper(seg, fn, demon)
            else:
                piper(seg, fn, demon)
            print(source, sid, k, j, "DEMON" if demon else "", seg)
open(os.path.join(OUT, "VOICE_SOURCE"), "w").write(source)
print("VOICE_SOURCE =", source)
