"""Narração ElevenLabs, um arquivo por parágrafo, com cache (só gasta crédito do que mudou)."""
import hashlib
import json
import os
import subprocess
import urllib.error
import urllib.request
import wave

import ambiente

VOZ_PADRAO = "oJebhZNaPllxk6W0LSBA"
MODELO = "eleven_multilingual_v2"
AJUSTES = {"stability": 0.5, "similarity_boost": 0.8, "style": 0.2, "use_speaker_boost": True, "speed": 0.95}


def chave():
    k = ambiente.chave_eleven()
    if not k:
        raise SystemExit("Chave do ElevenLabs não encontrada. Abra a interface (youtube/abrir.bat) e cole a chave, "
                         "ou defina ELEVENLABS_API_KEY / crie ~/.elevenlabs_key.")
    return k


def _gerar(texto, anterior, proximo, voz, k):
    corpo = {"text": texto, "model_id": MODELO, "voice_settings": AJUSTES}
    if anterior:
        corpo["previous_text"] = anterior[-400:]
    if proximo:
        corpo["next_text"] = proximo[:400]
    req = urllib.request.Request(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voz}?output_format=pcm_24000",
        data=json.dumps(corpo).encode(),
        headers={"xi-api-key": k, "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def gerar_todos(unidades, saida, voz=VOZ_PADRAO):
    """Retorna a lista de caminhos .wav (24 kHz mono), um por unidade."""
    os.makedirs(saida, exist_ok=True)
    k = None
    caminhos = []
    for i, u in enumerate(unidades):
        ant = unidades[i - 1]["texto"] if i else ""
        prox = unidades[i + 1]["texto"] if i + 1 < len(unidades) else ""
        tag = hashlib.sha1(f"{voz}|{MODELO}|{json.dumps(AJUSTES, sort_keys=True)}|{u['texto']}".encode()).hexdigest()
        fn = os.path.join(saida, f"vo_{i:03d}.wav")
        if not (os.path.exists(fn) and os.path.exists(fn + ".sha") and open(fn + ".sha").read() == tag):
            k = k or chave()
            try:
                pcm = _gerar(u["texto"], ant, prox, voz, k)
            except urllib.error.HTTPError as e:
                raise SystemExit(f"ElevenLabs recusou ({e.code}): {e.read().decode(errors='ignore')[:300]}")
            with wave.open(fn, "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(24000)
                w.writeframes(pcm)
            open(fn + ".sha", "w").write(tag)
            print(f"  voz {i + 1}/{len(unidades)} ({len(u['texto'])} caracteres)")
        caminhos.append(fn)
    return caminhos


def duracao(fn):
    with wave.open(fn) as w:
        return w.getnframes() / w.getframerate()
