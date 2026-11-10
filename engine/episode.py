"""Carrega um episódio: a pasta episodios/NN-nome/ só precisa de um script.py com o CONTEÚDO (texto, cenas, cutscenes).

script.py:
    CONFIG = {...}                       # título, voz, destaques, tempos (veja DEFAULTS)
    SCENES = [(id, look, cutscene|None, {params}, [(narrado, tela|None, pausa), ...]), ...]
    HITS   = [(cena, frase, palavra|None, deslocamento_s), ...]    # impactos (boom + tremor) presos ao texto
Não importa PIL/numpy/cupy: roda igual no WSL (tts/mix) e no Windows (render)."""
import importlib.util
from pathlib import Path

DEFAULTS = {
    "voice_id": "h96v1HCJtcisNNeagp0R", "model_id": "eleven_multilingual_v2", "language": "pt",
    "voice_speed": 0.95, "stability": 0.5, "similarity": 0.8, "style": 0.25,
    "style": "ps2",                               # "ps2" (low-poly PS2, legenda amarela) ou "elegant" (serifa, brilho, cenas 2D)
    "kicker": "RELATO DO REDDIT",                 # linha pequena acima do título (só no estilo elegant)
    "title": ["Título do vídeo"],                 # linhas do título de abertura
    "intro_time": 3.2,                            # segundos de abertura antes da 1ª frase
    "emph": [],                                   # palavras que ganham destaque vermelho
    "cards": [],                                  # textos de tela exibidos como cartão grande ("Parte 2")
    "lead": {}, "tail": {"end": 4.5},             # folga (s) antes/depois de cada cena, por id
    "heart": None,                                # ("cena_ini", "cena_fim"): batimento cardíaco no trecho
    "screeches": [],                              # [(cena, frase, palavra|None, deslocamento)] rangidos agudos
    "end_scene": "end",                           # cena final (cartão "Temos vagas")
    "end_question": "", "end_note": "Se inscreva e ative o sininho.", "channel": "@temosvagas.terror",
}

class Scene:
    def __init__(s, sid, look, cut, params, phrases):
        s.id, s.look, s.cut, s.params = sid, look, cut, params
        s.phrases = [{"text": n, "screen": (t if t else n), "pause": p} for n, t, p in phrases]

class Episode:
    def __init__(self, path):
        self.dir = Path(path).resolve()
        self.name = self.dir.name
        spec = importlib.util.spec_from_file_location(f"_ep_{self.name.replace('-', '_')}", self.dir / "script.py")
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        self.cfg = {**DEFAULTS, **getattr(mod, "CONFIG", {})}
        self.scenes = [Scene(*s) for s in mod.SCENES]
        self.hits = list(getattr(mod, "HITS", []))
        self.build = self.dir / "build"
        self.build.mkdir(exist_ok=True)

    def words(self):
        return sum(len(p["text"].split()) for s in self.scenes for p in s.phrases)

if __name__ == "__main__":
    import sys
    ep = Episode(sys.argv[1])
    print(f"{ep.name}: {len(ep.scenes)} cenas, {sum(1 for s in ep.scenes if s.cut)} cutscenes, {ep.words()} palavras narradas "
          f"(~{ep.words() / 130:.1f} min + pausas)")
