"""Fundos do vídeo: usa fundos/NN.(jpg|png|webp) se existir; senão gera uma névoa escura procedural."""
import hashlib
import os

import numpy as np
from PIL import Image, ImageFilter

W, H = 1920, 1080
PALETAS = {  # cor da névoa (RGB 0-255)
    "verde": (46, 74, 58), "vermelho": (96, 28, 24), "sepia": (92, 66, 40),
    "rosa": (96, 52, 70), "azul": (34, 52, 84), "cinza": (62, 62, 66),
}


def _ruido(rng, w, h):
    """Névoa: soma de ruídos suaves em várias escalas."""
    acc = np.zeros((h, w), np.float32)
    amp, total = 1.0, 0.0
    for lado in (3, 6, 12, 24, 48):
        pequeno = (rng.random((max(2, lado * h // w), lado)) * 255).astype(np.uint8)
        grande = Image.fromarray(pequeno).resize((w, h), Image.BICUBIC)
        acc += np.asarray(grande, np.float32) / 255 * amp
        total += amp
        amp *= 0.55
    return acc / total


def _vinheta(img, escuro=0.62):
    a = np.asarray(img, np.float32)
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]]
    d = np.sqrt(((xx - a.shape[1] / 2) / (a.shape[1] / 2)) ** 2 + ((yy - a.shape[0] / 2) / (a.shape[0] / 2)) ** 2)
    v = np.clip(1.15 - 0.62 * d ** 1.6, 0.08, 1.0)[..., None]
    return Image.fromarray(np.clip(a * v * escuro, 0, 255).astype(np.uint8))


def procedural(nome, cor, w=W, h=H):
    rng = np.random.default_rng(int(hashlib.sha1(nome.encode()).hexdigest()[:8], 16))
    n = _ruido(rng, w // 2, h // 2)
    n = np.clip((n - 0.28) / 0.55, 0, 1) ** 1.8
    base = np.array(PALETAS.get(cor, PALETAS["cinza"]), np.float32)
    grad = np.linspace(0.55, 1.0, h // 2, dtype=np.float32)[:, None]  # mais claro embaixo, como neblina no chão
    rgb = (n * grad)[..., None] * base * 1.9 + 8
    img = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    grao = (rng.normal(0, 5, (h, w, 1))).astype(np.float32)
    img = Image.fromarray(np.clip(np.asarray(img, np.float32) + grao, 0, 255).astype(np.uint8))
    return _vinheta(img, 1.0)


def _cobrir(img, w=W, h=H):
    r = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def preparar(fundo, pasta_fundos, saida):
    """fundo = (nome, cor). Grava saida (png 1920x1080 já escurecida e com vinheta)."""
    nome, cor = fundo
    for ext in ("jpg", "jpeg", "png", "webp"):
        p = os.path.join(pasta_fundos, f"{nome}.{ext}")
        if os.path.exists(p):
            img = _cobrir(Image.open(p).convert("RGB"))
            img = img.filter(ImageFilter.GaussianBlur(1.2))  # leve, para o texto mandar
            a = np.asarray(img, np.float32) * 0.55
            img = _vinheta(Image.fromarray(a.astype(np.uint8)), 0.9)
            break
    else:
        img = procedural(nome, cor)
    img.save(saida)
    return saida
