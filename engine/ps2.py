"""Cutscenes no estilo PS2: cenários 3D low-poly em 480x270 (sombreamento plano, névoa, vértices colados na grade),
sem nenhuma figura humana, só lugares, itens e objetos. O pós-processamento (quantização + dithering) é feito pelo render.

Cada cena é fn(C) -> array float32 (270, 480, 3) 0..255. Mesmos nomes e parâmetros de tempo de cutscenes.py.
Cenas "planas" (calendário, roleta, celular, romã, relógios do Dalí, gemas, riscos, contador) reaproveitam cutscenes.py,
reduzidas para 480x270 (efeito pixelado)."""
import math
import numpy as onp
from .core import xp, ease, lerp, resize_img, blur_img, arr as _arr2d, H0, W0
from .lowpoly import Scene, look_at, RW, RH
from . import cutscenes as flat

def to_arr(img): return xp.asarray(onp.asarray(img)).astype(xp.float32)

def pix(fn):
    """Cena 2D (720p) -> 480x270 (pixelada) para entrar no pipeline PS2."""
    def g(C):
        return resize_img(blur_img(fn(C), 1.2), RH, RW)
    return g

# ---------------------------------------------------------------- bayer 8x8 (dithering)
_b = onp.array([[0]])
for _ in range(3): _b = onp.block([[4 * _b, 4 * _b + 2], [4 * _b + 3, 4 * _b + 1]])
BAYER = (onp.tile(_b / 64.0, (RH // 8 + 1, RW // 8 + 1))[:RH, :RW]).astype(onp.float32)

def post(a, levels=32):
    """Quantiza para poucos níveis de cor com dithering ordenado (a cara do PS2)."""
    v = a / 255.0 * (levels - 1) + xp.asarray(BAYER)[..., None]
    return xp.clip(xp.floor(v), 0, levels - 1) * (255.0 / (levels - 1))

# ---------------------------------------------------------------- quarto, relógio, cama
def _room(C, two=False, creep=0.0, clock=("1:17", "1:18"), flash_at=None):
    t = C.t; p = ease(t / max(C.d, 1))
    s = Scene(bg=(6, 7, 12), fog=(6, 7, 12), fog_near=5, fog_far=16, ambient=0.34, light=(-0.3, 0.8, -0.5))
    s.checker(-3, 3, -4, 4, 0, 1.0, (70, 52, 42), (60, 44, 36))
    s.quad((-3, 2.8, -4), (3, 2.8, -4), (3, 2.8, 4), (-3, 2.8, 4), (34, 34, 42), layer=0)
    for z in range(-4, 4):
        s.quad((-3, 0, z), (-3, 0, z + 1), (-3, 2.8, z + 1), (-3, 2.8, z), (64, 68, 88), layer=0)
        s.quad((3, 0, z), (3, 0, z + 1), (3, 2.8, z + 1), (3, 2.8, z), (58, 62, 82), layer=0)
    for x in range(-3, 3): s.quad((x, 0, 4), (x + 1, 0, 4), (x + 1, 2.8, 4), (x, 2.8, 4), (72, 76, 96), layer=0)
    s.quad((-2.97, 1.0, 0.6), (-2.97, 1.0, 2.8), (-2.97, 2.3, 2.8), (-2.97, 2.3, 0.6), (140, 170, 225), True)           # janela (luar)
    s.box((-2.94, 1.65, 1.7), (0.06, 1.3, 0.08), (22, 24, 34)); s.box((-2.94, 1.65, 1.7), (0.06, 0.08, 2.2), (22, 24, 34))
    s.quad((-2.9, 0.012, 0.6), (-2.9, 0.012, 2.8), (-0.6, 0.012, 3.7), (-0.6, 0.012, 1.5), (62, 78, 118), True)         # feixe de luar
    s.light((-2.5, 1.7, 1.7), (130, 160, 235), 1.5)
    s.box((0, 0.25, 1.2), (2.0, 0.5, 2.3), (78, 56, 44)); s.box((0, 0.58, 1.45), (1.92, 0.2, 1.75), (82, 88, 118), top=(96, 102, 134))
    s.box((0, 0.95, 2.4), (2.1, 1.0, 0.12), (66, 46, 36))
    for px in ((-0.5, 0.5) if two else (0.0,)): s.box((px, 0.74, 0.55), (0.75, 0.16, 0.42), (190, 190, 205))
    s.box((1.7, 0.35, 2.0), (0.6, 0.7, 0.5), (66, 48, 38)); s.box((1.7, 0.82, 1.95), (0.46, 0.24, 0.2), (18, 18, 22))
    s.quad((1.47, 0.72, 1.84), (1.93, 0.72, 1.84), (1.93, 0.92, 1.84), (1.47, 0.92, 1.84), (8, 38, 20), True)
    txt = clock[0] if (flash_at is None or t < flash_at) else clock[1]
    if int(t * 2) % 2 or (flash_at is not None and t > flash_at): s.label((1.7, 0.82, 1.83), txt, (80, 255, 130), 0.16)
    else: s.label((1.7, 0.82, 1.83), txt.replace(":", " "), (80, 255, 130), 0.16)
    s.light((1.7, 0.95, 1.6), (60, 255, 120), 0.8)
    if creep > 0:                                                                    # colunas de sombra crescendo nos cantos
        for sx in (-2.7, 2.7):
            for z in (3.6, 1.6, -1.0, -3.4):
                s.box((sx, 1.4 * creep, z), (0.3 + 0.9 * creep, 2.8 * creep + 0.02, 0.3 + 0.9 * creep), (2, 2, 4))
    pos = (lerp(0.7, 0.35, p), lerp(1.4, 1.25, p), lerp(-3.7, -2.7, p))
    yaw, pitch = look_at(pos, (0.35, 0.75, 1.7))
    return s.render(pos, yaw, pitch, 72)

def clock(C):
    """Quarto escuro e um relógio digital que vira de hora; depois o vermelho toma conta."""
    fl = C.prm("flash_at", 1.4)
    a = to_arr(_room(C, False, clock=C.prm("times", ("1:17", "1:18")), flash_at=fl))
    red = ease((C.t - C.at("red_at", (1,))) / 2.4)
    a[..., 0] += red * 70 * (0.6 + 0.4 * math.sin(C.t * 9)); a[..., 1:] -= red * 14
    if fl < C.t < fl + 0.15: a += 50
    return a

def bed(C):
    """Cama de casal vazia, sombras crescendo nos cantos e um clarão vermelho."""
    p2 = C.at("hit_at", (2,))
    a = to_arr(_room(C, True, creep=ease(C.t / (p2 + 1)), clock=C.prm("times", ("1:17", "1:18")), flash_at=C.prm("flash_at", 2.0)))
    if C.t > p2 + 0.9: a[..., 0] += ease(1 - (C.t - p2 - 0.9) / 0.5) * 120
    return a

# ---------------------------------------------------------------- hospital
def hospital(C):
    """Corredor de hospital com camas vazias; elas somem uma a uma. params: vanish_at."""
    t = C.t; tv = C.at("vanish_at", (0, 10)); zc = t * 0.9
    s = Scene(bg=(8, 16, 16), fog=(8, 18, 18), fog_near=3, fog_far=17, ambient=0.46)
    s.checker(-1.5, 1.5, -3, 60, 0, 1.0, (62, 80, 74), (54, 70, 64))
    for z in range(-3, 60):
        s.quad((-1.5, 0, z), (-1.5, 0, z + 1), (-1.5, 2.8, z + 1), (-1.5, 2.8, z), (74, 98, 92), layer=0)
        s.quad((1.5, 0, z), (1.5, 0, z + 1), (1.5, 2.8, z + 1), (1.5, 2.8, z), (68, 92, 86), layer=0)
        s.quad((-1.5, 2.8, z), (1.5, 2.8, z), (1.5, 2.8, z + 1), (-1.5, 2.8, z + 1), (30, 40, 40), layer=0)
    s.quad((-1.5, 0, 60), (1.5, 0, 60), (1.5, 2.8, 60), (-1.5, 2.8, 60), (4, 6, 6), layer=0)
    for k in range(16):
        z = 2 + 4 * k
        if z < zc - 2 or z > zc + 30: continue
        fl = 1.0 if ((int(t * 12) + k * 7) % 11) else 0.25
        c = tuple(int(v * fl) for v in (215, 255, 240))
        s.quad((-0.35, 2.78, z), (0.35, 2.78, z), (0.35, 2.78, z + 1.2), (-0.35, 2.78, z + 1.2), c, True)
        if k < 14 and zc - 2 < z < zc + 10: s.light((0, 2.5, z + 0.6), (200, 255, 235), 1.2 * fl)
    vis = 1.0 if t < tv else (0.0 if t > tv + 0.7 else (1.0 if int(t * 22) % 2 else 0.0))
    for k in range(9):
        bz = 5 + 4 * k
        if bz < zc - 2 or bz > zc + 30: continue
        for sd in (-1, 1):
            s.box((sd * 1.46, 1.0, bz + 3.3), (0.08, 2.0, 0.95), (70, 52, 40))                       # porta
            if vis:
                s.box((sd * 0.95, 0.3, bz + 1), (1.0, 0.45, 2.0), (118, 122, 120)); s.box((sd * 0.95, 0.58, bz + 1), (0.92, 0.14, 1.8), (150, 160, 158))
                s.box((sd * 0.95, 0.72, bz + 0.2), (0.6, 0.12, 0.36), (200, 204, 200)); s.cyl((sd * 0.45, 0, bz + 1.9), 0.03, 1.9, (140, 144, 140), n=5); s.box((sd * 0.45, 1.9, bz + 1.9), (0.22, 0.3, 0.06), (160, 190, 200))
    pos = (0.05 * math.sin(t * 0.9), 1.5, zc)
    yaw, pitch = look_at(pos, (0.0, 1.45, zc + 6))
    return to_arr(s.render(pos, yaw, pitch, 72))

# ---------------------------------------------------------------- vazio
def void(C):
    """Espaço escuro com destroços à deriva e anéis de som que se expandem (os gritos). params: rings_at."""
    t = C.t; tr = C.at("rings_at", (1,))
    s = Scene(bg=(3, 8, 9), fog=(3, 8, 9), fog_near=3, fog_far=16, ambient=0.55)
    rng = onp.random.default_rng(5)
    for i in range(44):
        r = 4 + rng.random() * 10; th = rng.random() * 6.283; ph = (rng.random() - 0.5) * 1.5; sp = 0.1 + rng.random() * 0.25; sz = 0.3 + rng.random() * 1.1
        base = onp.array([r * math.cos(th) * math.cos(ph), r * math.sin(ph) * 0.8, r * math.sin(th) * math.cos(ph)])
        pos = base + onp.array([math.sin(t * sp + i), math.sin(t * sp * 0.7 + i * 2), math.cos(t * sp + i)]) * 0.8
        g = int(46 + rng.random() * 50)
        s.box(pos, (sz, sz * (0.4 + rng.random()), sz), (g, int(g * 1.15), int(g * 1.15)), yaw=t * sp + i)
    period = 1.2 if t > tr else 3.0
    for j in range(4):
        ph = ((t / period) + j / 4.0) % 1.0
        r = 0.6 + 9 * ph; c = int(190 * (1 - ph) ** 1.5)
        if c > 8: s.ring((0, 0.0, 9), r, r + 0.07, (c, int(c * 1.1), int(c * 1.15)), n=18, y_axis=False)
    s.light((0, 0, 0), (120, 190, 200), 0.5)
    pos = (0, 0, 0); yaw = 0.2 * math.sin(t * 0.2)
    return to_arr(s.render(pos, yaw, 0.0, 74))

# ---------------------------------------------------------------- ilha, salão de colunas, mar
def _sea(s, t, x0=-36, x1=36, z0=-24, z1=60, tile=4):
    def h(x, z): return 0.14 * math.sin(x * 0.55 + t * 1.3) * math.cos(z * 0.4 + t * 0.9)
    for i, x in enumerate(range(x0, x1, tile)):
        for j, z in enumerate(range(z0, z1, tile)):
            s.quad((x, h(x, z), z), (x + tile, h(x + tile, z), z), (x + tile, h(x + tile, z + tile), z + tile), (x, h(x, z + tile), z + tile),
                   (14, 36, 42) if (i + j) % 2 else (11, 30, 36), layer=0)

def _columns_ring(s, n=7, rad=4.6, h=3.2):
    for k in range(n):
        a = 2 * math.pi * k / n; x, z = rad * math.cos(a), rad * math.sin(a)
        s.cyl((x, 0.5, z), 0.3, h, (176, 182, 172), n=8); s.box((x, 0.5 + h + 0.12, z), (0.9, 0.24, 0.9), (190, 196, 186)); s.box((x, 0.56, z), (0.8, 0.12, 0.8), (160, 166, 156))

def island(C):
    """Ilha de mármore com colunas num mar escuro; a câmera se aproxima."""
    t = C.t; p = ease(t / max(C.d, 1))
    s = Scene(bg=(5, 9, 11), fog=(6, 12, 14), fog_near=10, fog_far=42, ambient=0.5)
    s.bg_draw.append(lambda d: d.ellipse([120, 30, 360, 130], fill=(22, 34, 38)))
    _sea(s, t)
    s.cyl((0, 0.0, 0), 7, 0.5, (150, 156, 148), n=10); _columns_ring(s)
    s.box((0, 0.3, 0), (14, 0.02, 0.02), (150, 156, 148))
    s.light((0, 5, 0), (170, 190, 200), 1.3)
    pos = (lerp(-5, -2, p), 2.2, lerp(-22, -12, p)); yaw, pitch = look_at(pos, (0, 1.8, 0))
    return to_arr(s.render(pos, yaw, pitch, 66))

def columns(C):
    """Salão de colunas e uma gota que cai num espelho d'água, abrindo anéis. params: drop_at."""
    t = C.t; t0 = C.at("drop_at", (1,))
    s = Scene(bg=(5, 8, 9), fog=(6, 10, 11), fog_near=6, fog_far=26, ambient=0.5)
    s.checker(-6, 6, -8, 18, 0, 1.5, (116, 122, 116), (94, 100, 96))
    for k in range(6):
        for x in (-3.8, 3.8):
            z = k * 3.2; s.cyl((x, 0, z), 0.45, 4.4, (156, 162, 152), n=8); s.box((x, 4.5, z), (1.3, 0.26, 1.3), (176, 182, 172)); s.box((x, 0.1, z), (1.2, 0.2, 1.2), (140, 146, 138))
    s.quad((-2.2, 0.025, 5), (2.2, 0.025, 5), (2.2, 0.025, 9), (-2.2, 0.025, 9), (6, 16, 20))
    tt = t - t0
    if tt > 0:
        ph = (tt % 2.8) / 2.8
        if ph < 0.35: s.sphere((0, 0.15 + 5.5 * (1 - (ph / 0.35)) ** 2, 7), 0.13, (225, 242, 255), 3, 6, emis=True)
        else:
            k = (ph - 0.35) / 0.65
            for j in range(3):
                r = 0.15 + 2.0 * k - j * 0.5
                if r > 0.1: s.ring((0, 0.04, 7), r, r + 0.07, (int(190 * (1 - k)),) * 3, n=14)
    s.light((0, 4.0, 7), (170, 195, 210), 1.2)
    pos = (0, 1.7, -5.5); yaw, pitch = look_at(pos, (0, 1.3, 7))
    return to_arr(s.render(pos, yaw, pitch, 68))

def _lantern(s, x, z, scale, col, y=0.0):
    s.cyl((x, y, z), 0.17, 0.07, (60, 52, 44), n=6); s.sphere((x, y + 0.27, z), 0.14 * scale, col, 3, 6, emis=True)
    s.cyl((x, y + 0.4, z), 0.2, 0.14, (70, 60, 50), n=6, r_top=0.03); s.light((x, y + 0.3, z), col, 1.8 * scale)

def orbs(C):
    """Duas lanternas lado a lado; uma garra de sombra arranca uma delas. params: dim_at, grab_at."""
    t = C.t; tg = C.at("grab_at", (3,)); td = C.at("dim_at", (2,))
    dim = 0.5 if t >= tg else (ease((t - td) / 3.0) if t > td else 0.0)
    s = Scene(bg=(4, 7, 8), fog=(4, 7, 8), fog_near=3 - dim, fog_far=15 - 7 * dim, ambient=0.4 - 0.15 * dim)
    s.checker(-8, 8, -3, 16, 0, 1.2, (96, 102, 98), (70, 76, 72))
    ax = -0.7; bx = 0.7 + (0 if t < tg else 11 * ease((t - tg) / 1.4))
    _lantern(s, ax, 3, 1.0 + 0.04 * math.sin(t * 9), (235, 205, 140))
    sc = 1.0 if t < tg else max(0.1, 1 - 0.9 * ease((t - tg) / 1.6))
    if bx < 11: _lantern(s, bx, 3, sc, (200, 225, 240))
    tip = (7 - 5.6 * ease((t - td) / (tg - td + 0.01)) if t < tg else bx + 0.3)
    if t > td:
        for i in range(16):
            u = i / 15; x = lerp(12, tip, u)
            s.box((x, 0.18 + 0.16 * math.sin(u * 7 + t * 3) * (1 - u * 0.5), 3.4 - 0.4 * u + 0.15 * math.sin(u * 5 + t * 2)), (0.5, 0.2, 0.28), (26, 18, 34), yaw=0.3 * math.sin(i + t))
    pos = (0, 0.95, -0.9); yaw, pitch = look_at(pos, (0, 0.5, 3))
    a = to_arr(s.render(pos, yaw, pitch, 70))
    if tg <= t < tg + 0.18: a += 160 * (1 - (t - tg) / 0.18)
    return a

# ---------------------------------------------------------------- corredor visto pelo olho mágico
def peephole(C):
    """Visto por um olho mágico: corredor, lâmpada que pisca e uma porta ao fundo que se abre devagar."""
    t = C.t; k = ease(t / max(C.d, 1))
    s = Scene(bg=(2, 2, 3), fog=(10, 8, 6), fog_near=4, fog_far=18, ambient=0.5)
    s.checker(-1.2, 1.2, -2, 17, 0, 0.8, (84, 62, 44), (72, 54, 38))
    for z in range(-2, 17):
        s.quad((-1.2, 0, z), (-1.2, 0, z + 1), (-1.2, 2.6, z + 1), (-1.2, 2.6, z), (132, 114, 90), layer=0)
        s.quad((1.2, 0, z), (1.2, 0, z + 1), (1.2, 2.6, z + 1), (1.2, 2.6, z), (122, 106, 84), layer=0)
        s.quad((-1.2, 2.6, z), (1.2, 2.6, z), (1.2, 2.6, z + 1), (-1.2, 2.6, z + 1), (62, 56, 50), layer=0)
    for z in (3.5, 7.0, 10.5):
        s.box((-1.17, 1.0, z), (0.08, 2.0, 0.95), (64, 44, 32)); s.box((1.17, 1.0, z), (0.08, 2.0, 0.95), (64, 44, 32))
    hx, hz = -0.55, 15.6; a = k * 1.15                                  # porta do fundo abrindo
    s.quad((hx, 0, hz), (hx + 1.1 * math.cos(a), 0, hz + 1.1 * math.sin(a)), (hx + 1.1 * math.cos(a), 2.0, hz + 1.1 * math.sin(a)), (hx, 2.0, hz), (84, 58, 40), layer=1)
    s.quad((-0.6, 0.0, 15.65), (0.6, 0.0, 15.65), (0.6, 2.1, 15.65), (-0.6, 2.1, 15.65), (2, 2, 3), True, layer=0)
    s.quad((-0.5, 0.012, 15.6), (0.5, 0.012, 15.6), (0.5 + 0.9 * k, 0.012, 13.2), (-0.5 - 0.9 * k, 0.012, 13.2), (int(150 * k), int(105 * k), int(55 * k)), True)
    fl = 1.0 if int(t * 9) % 13 else 0.35
    s.quad((-0.3, 2.58, 6), (0.3, 2.58, 6), (0.3, 2.58, 7), (-0.3, 2.58, 7), tuple(int(v * fl) for v in (255, 230, 170)), True)
    s.light((0, 2.3, 6.5), (255, 220, 160), 1.6 * fl)
    pos = (0.03 * math.sin(t), 1.55, -0.8); yaw, pitch = look_at(pos, (0, 1.4, 10))
    img = s.render(pos, yaw, pitch, 78)
    from PIL import Image, ImageDraw
    mask = Image.new("L", (RW, RH), 0); ImageDraw.Draw(mask).ellipse([240 - 112, 135 - 112, 240 + 112, 135 + 112], fill=255)
    out = Image.new("RGB", (RW, RH), (2, 2, 2)); out.paste(img, (0, 0), mask)
    ImageDraw.Draw(out).ellipse([240 - 116, 135 - 116, 240 + 116, 135 + 116], outline=(150, 120, 52), width=3)
    return to_arr(out)

def wake(C):
    """Mar escuro, uma lanterna à deriva e a esteira em V rumo a uma ilha distante."""
    t = C.t; p = ease(t / max(C.d, 1))
    s = Scene(bg=(5, 9, 11), fog=(6, 12, 14), fog_near=8, fog_far=40, ambient=0.5)
    s.bg_draw.append(lambda d: d.ellipse([260, 40, 440, 120], fill=(24, 36, 40)))
    _sea(s, t * 1.4)
    s.cyl((6, 0, 44), 5, 0.5, (150, 156, 148), n=8)
    for k in range(5): a = 6.28 * k / 5; s.cyl((6 + 3.4 * math.cos(a), 0.5, 44 + 3.4 * math.sin(a)), 0.22, 2.6, (176, 182, 172), n=6)
    z = 6 + 26 * p; x = 1.2 * math.sin(t * 0.5)
    s.sphere((x, 0.28, z), 0.3, (235, 220, 150), 3, 6, emis=True); s.light((x, 0.6, z), (235, 220, 150), 2.2)
    for j in range(1, 7):
        zz = z - j * 1.1; w = 0.4 + 0.5 * j; c = int(120 * (1 - j / 7))
        s.quad((x - w, 0.03, zz), (x - w - 0.12, 0.03, zz), (x - w - 0.12 + 0.5, 0.03, zz - 1.0), (x - w + 0.5, 0.03, zz - 1.0), (c, c + 20, c + 20), True)
        s.quad((x + w, 0.03, zz), (x + w + 0.12, 0.03, zz), (x + w + 0.12 - 0.5, 0.03, zz - 1.0), (x + w - 0.5, 0.03, zz - 1.0), (c, c + 20, c + 20), True)
    pos = (0.5, 1.0, -1); yaw, pitch = look_at(pos, (x * 0.5, 0.45, 30))
    return to_arr(s.render(pos, yaw, pitch, 66))

# ---------------------------------------------------------------- objetos: calendário, roleta, celular, romã, relógios, ovo, riscos, contador
def days(C):
    """Calendário de parede em que X vermelhos marcam os dias. params: title="SUMIÇO", count=3, first=0.5, step=0.9."""
    t = C.t; n_days = C.prm("count", 3); t0 = C.prm("first", 0.5); step = C.prm("step", 0.9)
    s = Scene(bg=(4, 4, 6), fog=(4, 4, 6), fog_near=8, fog_far=22, ambient=0.6)
    s.box((0, 1.5, 3.2), (3.0, 3.1, 0.08), (214, 208, 190)); s.box((0, 2.75, 3.14), (3.0, 0.55, 0.06), (150, 30, 30))
    s.label((0, 2.75, 3.1), C.prm("title", "SUMIÇO"), (236, 222, 210), 0.3, mono=False)
    for r in range(4):
        for c in range(7): s.box((-1.2 + c * 0.4, 2.05 - r * 0.5, 3.15), (0.32, 0.4, 0.03), (190, 184, 166))
    for n in range(n_days):
        tt = t0 + n * step
        if t > tt:
            k = ease((t - tt) / 0.25); x, y = -1.2 + n * 0.4, 1.55
            for sg in (1, -1):
                s.box((x, y, 3.1), (0.5 * k, 0.05, 0.03), (190, 20, 20), emis=True)       # base da barra
                s.quad((x - 0.17 * k, y + 0.19 * sg * k, 3.09), (x - 0.13 * k, y + 0.19 * sg * k, 3.09), (x + 0.17 * k, y - 0.19 * sg * k, 3.09), (x + 0.13 * k, y - 0.19 * sg * k, 3.09), (200, 20, 20), True)
    k = min(n_days, int((t - t0) / step) + 1) if t > t0 else 0
    if k: s.label((-2.7, 1.5, 3.0), f"DIA {k}", (225, 40, 40) if k == n_days else (230, 220, 200), 0.55 + (0.04 * math.sin(t * 6) if k == n_days else 0), mono=False)
    s.light((0, 2.5, 0), (255, 240, 220), 1.2)
    pos = (0.3 * math.sin(t * 0.4), 1.5, -1.8); yaw, pitch = look_at(pos, (0, 1.5, 3))
    return to_arr(s.render(pos, yaw, pitch, 66))

def roulette(C):
    """Máquina caça-níquel de nomes que trava em itens no tempo das palavras e termina em ?????."""
    t = C.t
    items = C.prm("items", ["GAFANHOTOS", "GELO", "GUERRA SEM FIM", "FOGO", "SILÊNCIO", "AFOGAMENTO", "ESPELHOS", "DESERTO"])
    locks = [(C.when(w), idx) for w, idx in C.prm("locks", [((0, 6), 0), ((0, 7), 1), ((0, 11), 2)])]
    locked = {items[idx] for _, idx in locks}; end_text = C.prm("end_text", "??????")
    show = None
    for tl, idx in locks:
        if tl <= t < tl + 0.9: show = items[idx]
    if show is None: show = end_text if t > C.at("end_at", (1,)) + 1.5 else items[int(t * 13) % len(items)]
    s = Scene(bg=(8, 3, 3), fog=(8, 3, 3), fog_near=8, fog_far=24, ambient=0.5)
    s.box((0, 1.4, 3.4), (3.8, 2.8, 1.4), (96, 24, 24)); s.box((0, 2.85, 3.4), (4.0, 0.25, 1.5), (150, 30, 30))
    s.box((0, 1.55, 2.68), (3.0, 1.0, 0.06), (6, 6, 8)); s.box((0, 0.35, 2.7), (3.4, 0.5, 0.3), (60, 14, 14))
    ok = show in locked or show == end_text
    s.label((0, 1.55, 2.62), show, (240, 224, 200) if show in locked else (160, 70, 70), 0.34 if len(show) < 12 else 0.26, mono=False)
    for i in range(5):
        on = int(t * 4 + i) % 2
        s.sphere((-1.4 + i * 0.7, 2.35, 2.66), 0.11, (230, 60, 50) if on else (90, 20, 20), 3, 6, emis=bool(on))
    s.light((0, 1.5, 2.2), (255, 90, 80), 1.2)
    pos = (0.25 * math.sin(t * 0.5), 1.5, -1.5); yaw, pitch = look_at(pos, (0, 1.6, 3.2))
    a = to_arr(s.render(pos, yaw, pitch, 62))
    if show in locked and any(tl <= t < tl + 0.12 for tl, _ in locks): a += 50
    return a

def phone(C):
    """Celular sobre uma mesa vibrando com notificações; depois o chip (SIM) é retirado. params: sim_at."""
    t = C.t; t1 = C.at("sim_at", (2,))
    s = Scene(bg=(4, 5, 6), fog=(4, 5, 6), fog_near=6, fog_far=18, ambient=0.5)
    s.checker(-4, 4, -1, 8, 0, 1.0, (46, 40, 34), (40, 34, 29))
    sh = 0.03 * math.sin(t * 60) if (int(t * 3) % 2 == 0 and t < t1) else 0
    s.box((sh, 0.05, 2.2), (1.0, 0.1, 1.9), (18, 18, 22))
    if t < t1:
        s.quad((-0.44 + sh, 0.106, 1.32), (0.44 + sh, 0.106, 1.32), (0.44 + sh, 0.106, 3.08), (-0.44 + sh, 0.106, 3.08), (22, 44, 60), True)
        for i in range(6):
            tt = 1.3 + i * 0.35
            if t > tt:
                z = 2.95 - i * 0.27; k = ease((t - tt) / 0.25)
                s.quad((-0.4 + sh, 0.112, z - 0.1 * k), (0.4 + sh, 0.112, z - 0.1 * k), (0.4 + sh, 0.112, z + 0.1), (-0.4 + sh, 0.112, z + 0.1), (232, 238, 242), True)
                s.quad((0.3 + sh, 0.118, z - 0.04), (0.36 + sh, 0.118, z - 0.04), (0.36 + sh, 0.118, z + 0.04), (0.3 + sh, 0.118, z + 0.04), (225, 40, 40), True)
    else:
        k = ease((t - t1) / 1.2)
        s.box((0.9 + 1.6 * k, 0.04, 2.2), (0.3, 0.05, 0.42), (214, 176, 60), emis=True)
    s.light((0, 1.8, 1.5), (180, 200, 220), 0.8)
    pos = (0, 2.4, 0.2); yaw, pitch = look_at(pos, (0.2, 0, 2.2))
    return to_arr(s.render(pos, yaw, pitch, 64))

def pomegranate(C):
    """Romã em corte (cubinhos): casca = barreira, grãos = mundos, fronteiras entre eles.
    params: cells_at=(1,), shell_at=(1,14), borders_at=(1,24), visit_at=(2,)."""
    t = C.t; tcell = C.at("cells_at", (1,)); tc = C.at("shell_at", (1, 14)); tf = C.at("borders_at", (1, 24)); tv = C.at("visit_at", (2,))
    s = Scene(bg=(14, 8, 8), fog=(14, 8, 8), fog_near=8, fog_far=22, ambient=0.6)
    n = int(36 * ease((t - tcell) / 2.5)) if t > tcell else 0
    shell_hot = tc <= t < tc + 2.5; grow = ease(t / 1.6)
    for i in range(int(44 * grow)):
        a = 2 * math.pi * i / 44; col = (230, 90, 40) if shell_hot else (150, 44, 34)
        s.box((2.7 * math.cos(a), 2.7 * math.sin(a), 0), (0.5, 0.5, 0.5), col, yaw=a)
    for i in range(n):
        r = 2.25 * math.sqrt((i + 0.5) / 36); th = i * 2.39996
        edge = tf <= t < tf + 3.5
        s.box((r * math.cos(th), r * math.sin(th), 0), (0.42, 0.42, 0.42), (255, 226, 120) if edge else (120, 24, 28), yaw=th)
        if t > tv and (t - tv) * 12 > i: s.box((r * math.cos(th), r * math.sin(th), -0.26), (0.12, 0.12, 0.05), (255, 246, 230), emis=True)
    if tc < t < tc + 3.0: s.label((4.6, 2.3, 0), C.prm("shell_label", "CASCA = barreira"), (235, 210, 190), 0.35, mono=False)
    if tf <= t < tf + 3.5: s.label((-4.6, -2.4, 0), C.prm("borders_label", "fronteiras"), (255, 230, 120), 0.35, mono=False)
    s.light((0, 0, -4), (255, 200, 180), 1.4)
    ang = 0.35 * math.sin(t * 0.3); pos = (6 * math.sin(ang), 0.2, -6 * math.cos(ang)); yaw, pitch = look_at(pos, (0, 0, 0))
    return to_arr(s.render(pos, yaw, pitch, 62))

def melt(C):
    """Deserto surreal (estilo Dalí): relógios derretendo sobre um galho e o chão ondulando."""
    t = C.t; dr = 0.5 + 0.6 * ease(t / 6)
    s = Scene(bg=(200, 140, 90), fog=(190, 130, 85), fog_near=14, fog_far=44, ambient=0.6)
    def sky(d):
        for y in range(0, 150): c = lerp(0, 1, y / 150); d.line([(0, y), (RW, y)], fill=(int(lerp(120, 226, 1 - c)), int(lerp(76, 160, 1 - c)), int(lerp(48, 96, 1 - c))))
    s.bg_draw.append(sky)
    s.checker(-30, 30, -4, 50, 0, 6, (150, 100, 62), (140, 92, 56))
    s.cyl((-12, 0, 24), 7, 4.5, (128, 84, 52), n=7, r_top=0.4); s.cyl((14, 0, 30), 9, 6.5, (110, 72, 46), n=7, r_top=0.5)
    s.cyl((-1.5, 0, 9), 0.18, 3.4, (36, 24, 14), n=5); s.box((0.2, 3.2, 9), (3.4, 0.22, 0.22), (36, 24, 14), yaw=0.15)
    for (x, y, z, r, d_) in ((1.2, 3.0, 9, 0.95, dr), (4.5, 0.5, 11, 1.1, dr * 1.4), (-4.0, 0.45, 8, 0.8, dr)):
        s.sphere((x, y, z), r, (232, 220, 186), 4, 8, sy=0.5)
        s.sphere((x, y - 0.45 * d_, z), r * 0.8, (226, 212, 176), 3, 8, sy=0.9 + d_ * 0.3)
        s.box((x, y + r * 0.3, z - r * 0.55), (0.08, 0.5, 0.04), (40, 24, 14), emis=True)
    s.light((0, 6, 0), (255, 220, 170), 1.0)
    pos = (0, 1.8, -1); yaw, pitch = look_at(pos, (0, 1.6, 12))
    a = to_arr(s.render(pos, yaw, pitch, 68))
    off = (3 * xp.sin(xp.arange(RH) / 6.0 + t * 1.6)).astype(int)[:, None]                  # chão ondulando
    return a[xp.arange(RH)[:, None], (xp.arange(RW)[None, :] + off) % RW]

def yolks(C):
    """Duas gemas numa frigideira escorrem e se fundem numa só (ovo de gema dupla). params: at (padrão (0,13))."""
    t = C.t; tl = C.at("at", (0, 13)); k = ease((t - tl) / 2.6)
    s = Scene(bg=(8, 7, 6), fog=(8, 7, 6), fog_near=8, fog_far=22, ambient=0.6)
    s.cyl((0, 0, 4), 2.6, 0.22, (54, 56, 60), n=12); s.cyl((0, 0.22, 4), 2.35, 0.02, (28, 28, 30), n=12)
    s.box((3.6, 0.1, 4), (2.2, 0.12, 0.35), (44, 44, 48))
    xs = lerp(1.0, 0.35, k); rw = lerp(1.05, 1.55, k)
    for sd in (-1, 1): s.cyl((sd * xs, 0.24, 4), rw, 0.06, (236, 232, 222), n=10)
    for sd in (-1, 1): s.sphere((sd * lerp(1.0, 0.45, k), 0.3, 4), 0.46, (240, 176, 30), 4, 8, sy=0.65)
    s.light((0, 3, 3), (255, 235, 200), 1.2)
    pos = (0, 5.6, 0.8); yaw, pitch = look_at(pos, (0, 0, 4))
    return to_arr(s.render(pos, yaw, pitch, 60))

def claw(C):
    """Quatro riscos que se abrem numa parede listrada, pingando. params: at (padrão (0,13))."""
    t = C.t; tc = C.at("at", (0, 13))
    s = Scene(bg=(8, 6, 4), fog=(8, 6, 4), fog_near=8, fog_far=22, ambient=0.6)
    for i in range(16): s.box((-4.8 + i * 0.64, 1.5, 4), (0.32, 3.6, 0.06), (122, 106, 82) if i % 2 else (108, 94, 72))
    s.box((0, 0.1, 3.9), (10, 0.2, 0.2), (60, 44, 32))
    if t > tc:
        k = ease((t - tc) / 0.5)
        for i in range(4):
            x0 = -1.0 + i * 0.6
            s.quad((x0, 3.0, 3.9), (x0 + 0.1, 3.0, 3.9), (x0 + 0.1 + 0.9 * k, 3.0 - 2.6 * k, 3.9), (x0 + 0.9 * k, 3.0 - 2.6 * k, 3.9), (26, 10, 8), emis=True)
            s.quad((x0 + 0.03, 3.0, 3.88), (x0 + 0.07, 3.0, 3.88), (x0 + 0.07 + 0.9 * k, 3.0 - 2.6 * k, 3.88), (x0 + 0.03 + 0.9 * k, 3.0 - 2.6 * k, 3.88), (170, 10, 10), True)
            if k > 0.9:
                for j in range(2):
                    y = 1.0 - ((t - tc) * (0.5 + 0.2 * j) + j * 0.3) % 0.9; s.box((x0 + 0.95, y, 3.87), (0.06, 0.14, 0.02), (140, 6, 6), emis=True)
    s.light((0, 2.5, 1), (255, 225, 190), 1.1)
    pos = (0.15 * math.sin(t * 0.5), 1.5, -1.5); yaw, pitch = look_at(pos, (0, 1.5, 4))
    a = to_arr(s.render(pos, yaw, pitch, 62))
    if 0 <= t - tc < 0.18: a += 150 * (1 - (t - tc) / 0.18)
    return a

def timer(C):
    """Relógio digital de mesa: 1:30 parado e depois um contador que passa do combinado e fica vermelho.
    params: clock_text="1:30", label="TEMPO NO INFERNO", start_at=(1,), over_at=(1,10), limit=600 (s), over=720 (s)."""
    t = C.t; t1 = C.at("start_at", (1,)); tz = C.at("over_at", (1, 10)); lim = C.prm("limit", 600); over = C.prm("over", 720)
    if t < t1: txt, col = C.prm("clock_text", "1:30"), (80, 255, 130)
    else:
        sec = lim * ease((t - t1) / 3.4) if t < tz else over
        txt, col = f"{int(sec // 60):02d}:{int(sec % 60):02d}", (80, 255, 130) if t < tz else (255, 50, 50)
    s = Scene(bg=(3, 3, 4), fog=(3, 3, 4), fog_near=8, fog_far=22, ambient=0.5)
    s.checker(-4, 4, -2, 8, 0, 1.0, (40, 34, 30), (34, 29, 25))
    sh = 0.05 * math.sin(t * 80) if 0 <= t - tz < 0.6 else 0
    s.box((sh, 0.9, 3.2), (3.2, 1.6, 0.9), (22, 22, 26)); s.quad((-1.4 + sh, 0.35, 2.74), (1.4 + sh, 0.35, 2.74), (1.4 + sh, 1.45, 2.74), (-1.4 + sh, 1.45, 2.74), (4, 14, 8) if col[0] < 200 else (22, 4, 4), True)
    s.label((sh, 0.95, 2.72), txt, col, 0.55)
    if t >= t1: s.label((0, 0.5, 2.72), C.prm("label", "TEMPO NO INFERNO"), (160, 160, 160), 0.12, mono=False)
    s.light((0, 1.0, 2.2), col, 1.0)
    pos = (0, 1.2, -1.2); yaw, pitch = look_at(pos, (0, 0.9, 3))
    a = to_arr(s.render(pos, yaw, pitch, 60))
    if 0 <= t - tz < 0.2: a += 70
    return a

def vortex(C):
    """Túnel em redemoinho: anéis roxos girando e um núcleo de luz violeta que pulsa (sem rosto). params: core_at."""
    t = C.t; te = C.at("core_at", C.params.get("eyes_at", (1, 7)))
    s = Scene(bg=(5, 3, 9), fog=(5, 3, 9), fog_near=2, fog_far=16, ambient=0.8)
    for j in range(16):
        z = ((j - t * 1.6) % 16) + 1.4; r = 2.6 + 0.35 * math.sin(j + t)
        c = (96 + 14 * (j % 3), 44, 150 + 10 * (j % 2))
        s.ring((0, 0, z), r - 0.6, r, c, n=8, y_axis=False, phase=t * 0.5 + j * 0.4)
    if t > te:
        k = ease((t - te) / 0.8); pulse = 0.8 + 0.2 * math.sin(t * 5)
        s.sphere((0, 0, 14), 1.4 * k * pulse, (200, 120, 255), 4, 8, emis=True); s.light((0, 0, 12), (200, 120, 255), 2 * k)
    return to_arr(s.render((0, 0, 0), 0, 0, 80))

# ---------------------------------------------------------------- registro
PS2 = {
    "clock": clock, "bed": bed, "hospital": hospital, "void": void, "island": island, "columns": columns, "orbs": orbs,
    "peephole": peephole, "wake": wake, "vortex": vortex, "days": days, "roulette": roulette, "phone": phone,
    "pomegranate": pomegranate, "melt": melt, "yolks": yolks, "claw": claw, "timer": timer,
}
PS2.update({"clock118": clock, "statues": columns, "tear": orbs, "dali": melt, "eye": yolks, "swim": wake, "shadow": vortex})
