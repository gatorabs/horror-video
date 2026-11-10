"""Lê o roteiro.txt de um episódio.

Formato:
    titulo: O Lorde Pálido          (cabeçalho: titulo, subtitulo, fonte, voz)
    ---
    @fundo 01 verde                 (troca o fundo daqui em diante; a cor só vale se não houver fundos/01.jpg)
    Parágrafo um.

    Parágrafo dois.
"""
import os
import re

MAX_CHARS = 1100  # parágrafo maior que isso é dividido em frases (cabe melhor na tela e na voz)


def _dividir(texto):
    if len(texto) <= MAX_CHARS:
        return [texto]
    frases = re.split(r"(?<=[.!?…])\s+", texto)
    partes, atual = [], ""
    for f in frases:
        if atual and len(atual) + len(f) + 1 > MAX_CHARS * 0.7:
            partes.append(atual)
            atual = f
        else:
            atual = (atual + " " + f).strip()
    if atual:
        partes.append(atual)
    return partes


def carregar(pasta):
    caminho = os.path.join(pasta, "roteiro.txt")
    bruto = open(caminho, encoding="utf-8").read().replace("\r\n", "\n")
    cab, _, corpo = bruto.partition("\n---\n")
    meta = {}
    for linha in cab.splitlines():
        if ":" in linha:
            k, v = linha.split(":", 1)
            meta[k.strip().lower()] = v.strip()
    meta.setdefault("titulo", os.path.basename(os.path.abspath(pasta)))
    meta.setdefault("subtitulo", "")

    unidades = []
    fundo = ("01", "cinza")
    novo = True
    for bloco in re.split(r"\n\s*\n", corpo.strip()):
        linhas = []
        for linha in bloco.strip().splitlines():
            m = re.match(r"@fundo\s+(\S+)(?:\s+(\S+))?", linha.strip())
            if m:
                fundo = (m.group(1), m.group(2) or "cinza")
                novo = True
            elif linha.strip():
                linhas.append(linha.strip())
        if not linhas:
            continue
        for parte in _dividir(" ".join(linhas)):
            unidades.append({"texto": parte, "fundo": fundo, "novo_fundo": novo})
            novo = False
    return meta, unidades
