# Episódio NOVO — copie para episodios/NN-nome/script.py (ou rode: python -m engine.new episodios/NN-nome)
# Este arquivo é só CONTEÚDO. O motor cuida de voz, mixagem e render:  python -m engine.build episodios/NN-nome
#
# SCENES: (id, look, cutscene|None, {parâmetros}, [(narrado, tela|None, pausa_s), ...])
#   look:      "sepia" | "teal" | "bw" (tom do fundo)
#   cutscene:  None = só texto lido palavra por palavra. Ou um nome de engine/cutscenes.py:
#              clock, bed, hospital, void, island, columns, orbs, days, roulette, phone, peephole,
#              pomegranate, melt, yolks, wake, vortex, claw, timer   (só cenários e objetos: sem rostos/humanos)
#   narrado:   o que a voz diz (números por extenso). tela: o que aparece escrito (None = igual ao narrado).
#   parâmetros: veja a docstring de cada cutscene. Âncoras de tempo: (k, i) = palavra i da frase k da cena;
#              (k,) = início da frase k; ou segundos desde o início da cena.
# A última cena deve se chamar "end" (cartão final "Temos vagas").
# HITS: impactos (boom + tremor) presos a uma palavra: (cena, frase, palavra|None, deslocamento_s).
# Dica de duração: ~130 palavras por minuto de narração (+ pausas). Para 8 min, mire em ~1.000 palavras.

CONFIG = {
    "voice_id": "h96v1HCJtcisNNeagp0R",          # ElevenLabs
    "kicker": "RELATO DO REDDIT",                 # linha pequena acima do título
    "title": ["Título do vídeo", "em duas linhas"],
    "intro_time": 3.2,                            # segundos de abertura antes da narração
    "emph": ["medo", "sangue"],                   # palavras destacadas em vermelho
    "cards": [],                                  # textos de tela exibidos como cartão grande (ex.: "PARTE 2")
    "heart": None,                                # ("cena_ini", "cena_fim"): batimento cardíaco nesse trecho
    "screeches": [],                              # [(cena, frase, palavra|None, deslocamento_s)]
    "end_question": "O que você faria no lugar dele?",
    "end_note": "Se inscreva e ative o sininho.",
    "channel": "@temosvagas.terror",
}

HITS = [
    ("end", 0, None, 0.0),
]

SCENES = [
    ("s01", "teal", "clock", {}, [
        ("Acontece toda noite, à uma e dezoito da madrugada.", "Acontece toda noite, à 1h18 da madrugada.", 0.7),
        ("Eu vou para o inferno.", None, 0.8),
    ]),
    ("s02", "sepia", None, {}, [
        ("Uma cena só de texto, lido palavra por palavra.", None, 1.0),
    ]),
    ("end", "teal", None, {}, [
        ("Dez minutos era o combinado.", None, 1.0),
    ]),
]
