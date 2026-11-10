"""Quadros de texto: um painel escuro translúcido com os parágrafos, o atual em destaque."""
import os

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
MARGEM_X = 90
PAD = 38
ALTURA_MAX = 900
TAM_TEXTO = 35
LINHA = 49
ENTRE_PARAGRAFOS = 26
COR_PAINEL = (20, 9, 6, 218)
COR_ATUAL = (246, 240, 232, 255)
COR_ANTES = (140, 134, 128, 255)
COR_DEPOIS = (190, 184, 178, 255)
COR_DESTAQUE = (200, 40, 36, 255)


def _fonte(nomes, tam):
    pastas = [r"C:\Windows\Fonts", "/System/Library/Fonts/Supplemental", "/usr/share/fonts/truetype/dejavu",
              "/usr/share/fonts/truetype/liberation", "/usr/share/fonts/liberation", "/usr/share/fonts/dejavu"]
    for n in nomes:
        for p in pastas:
            f = os.path.join(p, n)
            if os.path.exists(f):
                return ImageFont.truetype(f, tam)
    return ImageFont.load_default()


FONTE = _fonte(["arial.ttf", "Arial.ttf", "LiberationSans-Regular.ttf", "DejaVuSans.ttf"], TAM_TEXTO)
FONTE_TITULO = _fonte(["georgiab.ttf", "Georgia Bold.ttf", "DejaVuSerif-Bold.ttf"], 92)
FONTE_SUB = _fonte(["georgia.ttf", "Georgia.ttf", "DejaVuSerif.ttf"], 36)


def quebrar(texto, fonte, largura):
    palavras, linhas, atual = texto.split(), [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if fonte.getlength(teste) <= largura:
            atual = teste
        else:
            linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def paginar(unidades):
    """Agrupa parágrafos consecutivos que cabem no painel. Retorna (paginas, indice_da_pagina_por_unidade)."""
    largura = W - 2 * MARGEM_X - 2 * PAD - 18
    quebras = [quebrar(u["texto"], FONTE, largura) for u in unidades]
    paginas, atual, h = [], [], 0
    for i, q in enumerate(quebras):
        altura = len(q) * LINHA
        extra = ENTRE_PARAGRAFOS if atual else 0
        if atual and h + extra + altura > ALTURA_MAX - 2 * PAD:
            paginas.append(atual)
            atual, h, extra = [], 0, 0
        atual.append(i)
        h += extra + altura
    if atual:
        paginas.append(atual)
    por_unidade = {i: n for n, pag in enumerate(paginas) for i in pag}
    return paginas, por_unidade, quebras


def quadro_pagina(pagina, atual, quebras):
    """RGBA 1920x1080 transparente, com o painel da página; 'atual' é o índice do parágrafo em destaque (ou None)."""
    altura = sum(len(quebras[i]) * LINHA for i in pagina) + ENTRE_PARAGRAFOS * (len(pagina) - 1) + 2 * PAD
    topo = (H - altura) // 2
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([MARGEM_X, topo, W - MARGEM_X, topo + altura], fill=COR_PAINEL)
    y = topo + PAD
    for i in pagina:
        cor = COR_ATUAL if i == atual else (COR_ANTES if (atual is not None and i < atual) else COR_DEPOIS)
        if atual is None:
            cor = COR_DEPOIS
        for linha in quebras[i]:
            d.text((MARGEM_X + PAD + 18, y), linha, font=FONTE, fill=cor)
            y += LINHA
        if i == atual:
            d.rectangle([MARGEM_X + PAD - 4, y - len(quebras[i]) * LINHA + 6, MARGEM_X + PAD, y - 6], fill=COR_DESTAQUE)
        y += ENTRE_PARAGRAFOS
    return img


def quadro_titulo(titulo, subtitulo):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([0, H // 2 - 170, W, H // 2 + 170], fill=(10, 4, 3, 200))
    if subtitulo:
        d.text((W // 2, H // 2 - 105), subtitulo.upper(), font=FONTE_SUB, fill=COR_DESTAQUE, anchor="mm")
    d.text((W // 2, H // 2 - 15), titulo, font=FONTE_TITULO, fill=COR_ATUAL, anchor="mm")
    d.line([W // 2 - 90, H // 2 + 70, W // 2 + 90, H // 2 + 70], fill=COR_DESTAQUE, width=3)
    return img


def capa(fundo_png, titulo, subtitulo, saida):
    """Miniatura 1280x720."""
    base = Image.open(fundo_png).convert("RGB").resize((1280, 720), Image.LANCZOS)
    img = base.convert("RGBA")
    d = ImageDraw.Draw(img)
    fonte = _fonte(["georgiab.ttf", "Georgia Bold.ttf", "DejaVuSerif-Bold.ttf"], 150)
    linhas = quebrar(titulo.upper(), fonte, 1100)
    y = 360 - len(linhas) * 90 + 60
    for l in linhas:
        d.text((640, y), l, font=fonte, fill=(240, 232, 224, 255), anchor="mm", stroke_width=6, stroke_fill=(0, 0, 0, 255))
        y += 170
    if subtitulo:
        d.text((640, 90), subtitulo.upper(), font=_fonte(["georgiab.ttf", "Georgia Bold.ttf", "DejaVuSerif-Bold.ttf"], 52), fill=COR_DESTAQUE,
               anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0, 255))
    img.convert("RGB").save(saida, quality=92)
