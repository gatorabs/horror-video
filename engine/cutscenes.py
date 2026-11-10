"""Biblioteca de cutscenes 2D animadas: só cenários e objetos (sem rostos nem figuras humanas, que ficam esquisitos).

Cada cutscene é uma função fn(C) -> array float32 (720, 1280, 3), 0..255. C = Ctx (veja core.py).
No script do episódio, uma cena usa uma cutscene assim:  ("s05", "teal", "hospital", {"vanish_at": (0, 10)}, [...frases...])
Os parâmetros de tempo aceitam (k, i) = palavra i da frase k, (k,) = início da frase k, ou segundos. Todos têm um padrão.

Catálogo: clock, bed, hospital, void, island, columns, orbs, days, roulette, phone, peephole, pomegranate, melt, yolks,
wake, vortex, claw, timer."""
import math
from .core import *
from .core import _noise

# ---------------------------------------------------------------- helpers de desenho
def _orb(a, x, y, r, col, k=1.0):
    g = xp.exp(-(((XX - x) ** 2 + (YY - y) ** 2) / (2.0 * r * r)))[..., None]
    return a + g * xp.array(col, xp.float32) * k

def _column(d, x, y0, y1, w, col):
    d.rectangle([x - w, y0, x + w, y1], fill=col); d.rectangle([x - w * 1.5, y0 - 8, x + w * 1.5, y0], fill=col); d.rectangle([x - w * 1.4, y1, x + w * 1.4, y1 + 8], fill=col)

def sea(a, t, hy=420):
    im, d = canvas()
    for i in range(26):
        y = hy + i * i * 0.45 + 4
        if y > H0: break
        amp = 1.5 + i * 0.35
        pts = [(x, y + amp * math.sin(x / (60 + i * 6) + t * (1.0 + i * 0.05) + i)) for x in range(0, W0 + 20, 20)]
        d.line(pts, fill=(36, 56, 60) if i % 2 else (22, 34, 38), width=2 + i // 6)
    return a + arr(im)

_RR = xp.sqrt((XX - 640.0) ** 2 + (YY - 360.0) ** 2)
_TH = xp.arctan2(YY - 360.0, XX - 640.0)

# ---------------------------------------------------------------- quarto / relógio / cama
def _room(C, mounds=1, clock=("1:17", "1:18"), creep=0.0, flash_at=None):
    t = C.t
    a = gradient((12, 14, 20), (5, 5, 8))
    im, d = canvas((0, 0, 0))
    d.rectangle([90, 90, 420, 400], fill=(86, 108, 150)); d.line([255, 90, 255, 400], fill=(14, 16, 24), width=8)
    d.line([90, 245, 420, 245], fill=(14, 16, 24), width=8); d.rectangle([90, 90, 420, 400], outline=(14, 16, 24), width=12)
    d.polygon([(90, 400), (420, 400), (900, 640), (330, 640)], fill=(34, 42, 60))
    d.rectangle([60, 450, 1010, 580], fill=(70, 74, 96)); d.rectangle([40, 380, 100, 660], fill=(34, 28, 32))
    br = 3 * math.sin(t * 1.6)
    for i in range(mounds):
        x0 = 130 + i * 160
        d.ellipse([x0 - 10, 412 + br, x0 + 110, 480 + br], fill=(120, 124, 150))              # travesseiro
        d.ellipse([x0 + 40, 426 + br, x0 + 800 - i * 170, 524], fill=(92, 98, 126))           # volume sob a coberta
    d.rectangle([1040, 520, 1260, 700], fill=(18, 16, 18))
    d.rectangle([1050, 400, 1250, 520], fill=(8, 8, 10), outline=(44, 44, 50), width=4)
    a = arr(im) + a * (arr(im).sum(2, keepdims=True) < 1)
    txt = clock[0] if (flash_at is None or t < flash_at) else clock[1]
    im2, d2 = canvas()
    if int(t * 2) % 2 == 0 or t > (flash_at or 0): d2.text((1150, 460), txt, font=F(70, True), fill=(70, 255, 130), anchor="mm")
    else: d2.text((1150, 460), txt.replace(":", " "), font=F(70, True), fill=(70, 255, 130), anchor="mm")
    a = a + arr(im2)
    a += fog(t, 3)[..., None] * xp.array([10, 14, 20])
    if creep > 0:                                           # sombras rastejando dos cantos
        im3, d3 = canvas(); k = creep
        for sx, sy in [(0, 0), (W0, 0), (0, H0), (W0, H0)]:
            for j in range(6):
                ang = j * 0.5 + 0.4 + t * 0.2
                ex = sx + (-1 if sx else 1) * (200 + 420 * k) * math.cos(ang * 0.6); ey = sy + (-1 if sy else 1) * (160 + 300 * k) * math.sin(ang * 0.7 + 0.4)
                d3.line([sx, sy, ex, ey], fill=(255, 255, 255), width=int(26 * k + 6))
        m = arr(im3.filter(ImageFilter.GaussianBlur(22)))[..., :1] / 255
        a = a * (1 - 0.85 * m)
    return bloom(a, 120, 1.1, 20)

def clock(C):
    """Quarto escuro com um relógio digital que vira de hora; depois o vermelho toma conta.
    params: times=("1:17","1:18"), flash_at=segundos da virada, red_at=âncora em que o vermelho começa."""
    times = C.prm("times", ("1:17", "1:18")); fl = C.prm("flash_at", 1.4)
    a = _room(C, 1, times, flash_at=fl)
    red = ease((C.t - C.at("red_at", (1,))) / 2.4)
    a += red * xp.array([60, -8, -8]) * (0.6 + 0.4 * math.sin(C.t * 9))
    if fl < C.t < fl + 0.15: a += 60
    return finish(a)

def bed(C):
    """Cama de casal, sombras rastejando dos cantos e um clarão vermelho. params: times, flash_at, hit_at=âncora do clarão."""
    p2 = C.at("hit_at", (2,))
    a = _room(C, 2, C.prm("times", ("1:17", "1:18")), creep=ease(C.t / (p2 + 1)), flash_at=C.prm("flash_at", 2.0))
    if C.t > p2 + 0.9: a += ease(1 - (C.t - p2 - 0.9) / 0.5) * xp.array([90, 10, 10])
    return finish(a)

# ---------------------------------------------------------------- hospital
def hospital(C):
    """Corredor de hospital com camas; os vultos sob os lençóis somem. params: vanish_at (padrão (0,10))."""
    t = C.t; vp = (640, 290); Fo = 520
    pr = lambda X, Y, z: (vp[0] + X * Fo / z, vp[1] + Y * Fo / z)
    im, d = canvas((6, 12, 12)); cam = t * 0.22; far = 40
    d.polygon([pr(-1.6, -1.3, .8), pr(1.6, -1.3, .8), pr(1.6, -1.3, far), pr(-1.6, -1.3, far)], fill=(16, 26, 26))
    d.polygon([pr(-1.6, 1.3, .8), pr(1.6, 1.3, .8), pr(1.6, 1.3, far), pr(-1.6, 1.3, far)], fill=(26, 40, 38))
    for s in (-1, 1):
        d.polygon([pr(s * 1.6, -1.3, .8), pr(s * 1.6, 1.3, .8), pr(s * 1.6, 1.3, far), pr(s * 1.6, -1.3, far)], fill=(20, 34, 34))
    d.rectangle([*pr(-1.6, -1.3, far), *pr(1.6, 1.3, far)], fill=(4, 6, 6))
    tv = C.at("vanish_at", (0, 10))
    for bz in (3.0, 5.6, 8.2, 10.8, 13.4, 16.0):
        z = bz - cam
        if z < 1.0: continue
        for s in (-1, 1):
            d.polygon([pr(s * 1.0, .55, z), pr(s * 1.0, .55, z + 1.7), pr(s * 1.0, 1.3, z + 1.7), pr(s * 1.0, 1.3, z)], fill=(40, 52, 52))
            d.polygon([pr(s * 1.0, .55, z), pr(s * 1.0, .55, z + 1.7), pr(s * 1.58, .55, z + 1.7), pr(s * 1.58, .55, z)], fill=(150, 168, 164))
            vis = 1.0 if t < tv else max(0.0, 1 - (t - tv) / 0.5) * (1 if int(t * 25) % 2 else 0.4)
            if vis > 0.05:
                cx_, cy_ = pr(s * 1.3, .42, z + 0.9); rr = Fo / (z + 0.9)
                d.ellipse([cx_ - .34 * rr, cy_ - .13 * rr, cx_ + .34 * rr, cy_ + .13 * rr], fill=tuple(int(v * vis + 150 * (1 - vis)) for v in (96, 108, 106)))
    for k in range(9):
        z = 2 + k * 2.6 - (cam % 2.6)
        if z < 1.0: continue
        fl = 1.0 if ((int(t * 12) + k * 7) % 11) else 0.25
        x0, y0 = pr(-.4, -1.3, z); x1, y1 = pr(.4, -1.3, z + .6)
        d.rectangle([x0, y0 - 2, x1, y1 + 2], fill=tuple(int(c * fl) for c in (210, 255, 240)))
    a = arr(im) + fog(t, 5)[..., None] * xp.array([8, 14, 14])
    return finish(bloom(a, 150, 1.0, 22), 1.0)

# ---------------------------------------------------------------- vazio, ilha, colunas
def void(C):
    """Vazio escuro: anéis de som (gritos) e duas luzes à deriva. params: rings_at (padrão (1,))."""
    t = C.t; tr = C.at("rings_at", (1,))
    a = gradient((6, 12, 14), (2, 4, 5)) + (fog(t, 1)[..., None] * 0.9 + fog(t * 1.3, 2, 18, 1)[..., None] * 0.5) * xp.array([22, 38, 42])
    k = 0.35 + 0.65 * ease((t - tr) / 2.0) if t > tr else 0.3
    im, d = canvas()
    for src in ((80, 120), (1200, 600), (1180, 90), (100, 640)):
        for j in range(5):
            ph = ((t * 0.5 + j / 5.0 + src[0] * 0.001) % 1.0)
            r = 40 + 700 * ph; al = int(255 * (1 - ph) ** 2 * k * 0.5)
            d.ellipse([src[0] - r, src[1] - r, src[0] + r, src[1] + r], outline=(al, al, al), width=2)
    a += arr(im) * xp.array([0.5, 0.8, 0.9])
    cx = 640 + 120 * math.sin(t * 0.35); cy = 360 + 60 * math.sin(t * 0.5)
    a = _orb(a, cx - 38, cy, 46, (150, 200, 210), 0.9); a = _orb(a, cx + 38, cy + 6, 46, (200, 190, 150), 0.9)
    rr = onp.random.default_rng(3); imp, dp = canvas()
    for x, y, s in rr.random((70, 3)):
        yy = (y * H0 - t * (10 + 30 * s)) % H0; xx = (x * W0 + 12 * math.sin(t + s * 9)) % W0
        dp.ellipse([xx, yy, xx + 2 + 3 * s, yy + 2 + 3 * s], fill=(120, 150, 150))
    a += arr(imp) * 0.7
    return finish(bloom(a, 150, 0.6), 1.0)

def island(C):
    """Ilha de mármore com colunas num mar escuro, câmera se aproximando."""
    t = C.t
    a = gradient((14, 20, 22), (4, 6, 8))
    a += xp.exp(-(((XX - 640) / 420.0) ** 2 + ((YY - 380) / 150.0) ** 2))[..., None] * xp.array([70, 86, 84]) * 0.55
    im, d = canvas(); hy = 420
    d.rectangle([0, hy, W0, H0], fill=(6, 10, 12))
    d.ellipse([360, hy - 40, 920, hy + 40], fill=(120, 130, 126))
    for i, x in enumerate(range(430, 880, 64)):
        h = 110 + 30 * ((i * 7) % 3); _column(d, x, hy - h, hy - 10, 10, (140, 150, 146))
    d.arc([470, hy - 170, 640, hy - 30], 180, 360, fill=(140, 150, 146), width=8)
    a = sea(a + arr(im), t, hy + 6)
    a = zoom(a, 1 + 0.35 * ease(t / C.d), 0.5, 0.58)
    a += fog(t, 4)[..., None] * xp.array([14, 18, 18])
    return finish(bloom(a, 150, 0.7), 1.0)

def columns(C):
    """Salão de colunas e uma gota que cai num espelho d'água, abrindo anéis. params: drop_at (padrão (1,))."""
    t = C.t; t0 = C.at("drop_at", (1,))
    a = gradient((14, 20, 22), (3, 5, 6)) + xp.exp(-(((XX - 640) / 520.0) ** 2 + ((YY - 300) / 160.0) ** 2))[..., None] * xp.array([60, 74, 72]) * 0.5
    im, d = canvas(); d.rectangle([0, 430, W0, H0], fill=(30, 40, 42))
    for x in (110, 330, 950, 1170): _column(d, x, 90, 430, 22, (118, 128, 124))
    d.rectangle([40, 430, W0 - 40, 446], fill=(150, 158, 152))
    a = a * (arr(im).sum(2, keepdims=True) == 0) + arr(im)
    imw, dw = canvas(); tt = (t - t0) if t > t0 else -1
    period = 2.6
    if tt > 0:
        ph = (tt % period) / period
        if ph < 0.35:
            y = 60 + 460 * (ph / 0.35) ** 2
            dw.ellipse([634, y - 10, 646, y + 14], fill=(220, 240, 255)); a += arr(imw) * 1.3
        else:
            k = (ph - 0.35) / 0.65
            for j in range(4):
                r = 20 + 260 * k - j * 26
                if r > 6: dw.ellipse([640 - r, 560 - r * 0.28, 640 + r, 560 + r * 0.28], outline=(int(190 * (1 - k)),) * 3, width=3)
            a += arr(imw)
    a += fog(t, 4)[..., None] * xp.array([14, 18, 18])
    return finish(bloom(a, 150, 0.7), 1.0)

def orbs(C):
    """Duas luzes lado a lado; uma tentáculo de sombra arranca uma delas. params: dim_at=(2,), grab_at=(3,)."""
    t = C.t; tg = C.at("grab_at", (3,))
    a = gradient((12, 18, 20), (3, 5, 6)) + fog(t, 2)[..., None] * xp.array([18, 26, 28])
    a += xp.exp(-(((XX - 640) / 520.0) ** 2 + ((YY - 340) / 180.0) ** 2))[..., None] * xp.array([50, 62, 60]) * 0.4
    im, d = canvas(); d.rectangle([0, 560, W0, H0], fill=(40, 46, 44)); a = a * (arr(im).sum(2, keepdims=True) == 0) + arr(im)
    mx = 700 + (0 if t < tg else 560 * ease((t - tg) / 1.0)); my = 430 - (0 if t < tg else 60 * ease((t - tg) / 1.0))
    sz = 38 * (1 - (0 if t < tg else ease((t - tg) / 1.2)) * 0.9)
    a = _orb(a, 560, 440 + 4 * math.sin(t * 2), 40, (210, 200, 150), 1.1)
    if sz > 3: a = _orb(a, mx, my, sz, (200, 220, 230), 1.1)
    if t >= tg:
        k = ease((t - tg) / 0.3); im2, d2 = canvas()
        d2.line([(W0 + 40, 300), (1050, 360 + 20 * math.sin(t * 6)), (mx + 20, my)], fill=(255, 255, 255), width=int(30 * k + 4))
        m = arr(im2)[..., :1] / 255; a = a * (1 - m) + m * xp.array([3, 2, 5])
        if t - tg < 0.2: a += 140 * (1 - (t - tg) / 0.2)
        rr = onp.random.default_rng(9); imp, dp = canvas()
        for i in range(60):
            px = mx + rr.normal(0, 30) + (t - tg) * rr.normal(120, 90); py = my + rr.normal(0, 40) - (t - tg) * rr.random() * 100
            s = 2 + rr.random() * 4; dp.ellipse([px, py, px + s, py + s], fill=(200, 210, 210))
        a += arr(imp) * max(0, 1 - (t - tg) / 3.0)
    else:
        td = C.at("dim_at", (2,))
        a *= 1 - 0.55 * (ease((t - td) / 3.0) if t > td else 0)
    return finish(bloom(a, 130, 0.9, 18), 1.0)

# ---------------------------------------------------------------- objetos: calendário, roleta, celular, olho mágico
def days(C):
    """Calendário em que X vermelhos vão marcando os dias. params: title="SUMIÇO", count=3, first=0.5, step=0.9."""
    t = C.t; n_days = C.prm("count", 3); t0 = C.prm("first", 0.5); step = C.prm("step", 0.9)
    a = gradient((10, 10, 12), (4, 4, 5)) + fog(t, 8)[..., None] * 6
    im, d = canvas(); d.rectangle([560, 40, 1120, 520], fill=(214, 208, 190)); d.rectangle([560, 40, 1120, 120], fill=(150, 30, 30))
    d.text((840, 82), C.prm("title", "SUMIÇO"), font=F(48), fill=(235, 220, 210), anchor="mm")
    for r in range(4):
        for c in range(7):
            x, y = 590 + c * 74, 150 + r * 90
            d.rectangle([x, y, x + 58, y + 70], outline=(90, 86, 76), width=2)
    for n in range(n_days):
        tt = t0 + n * step
        if t > tt:
            k = ease((t - tt) / 0.25); x, y = 590 + n * 74, 150 + 90
            d.line([x + 4, y + 6, x + 4 + 50 * k, y + 6 + 58 * k], fill=(190, 20, 20), width=7)
            d.line([x + 54, y + 6, x + 54 - 50 * k, y + 6 + 58 * k], fill=(190, 20, 20), width=7)
    k = min(n_days, int((t - t0) / step) + 1) if t > t0 else 0
    if k: d.text((260, 300), f"DIA {k}", font=F(120 + (int(6 * math.sin(t * 6)) if k == n_days and t > t0 + step * n_days else 0)), fill=(220, 40, 40) if k == n_days else (230, 220, 200), anchor="mm")
    a += arr(im)
    return finish(a)

def roulette(C):
    """Roleta de nomes que trava em itens no tempo das palavras e termina em ?????.
    params: items=[...], locks=[((k,i), item_index), ...], end_at=(1,), end_text="??????"."""
    t = C.t
    items = C.prm("items", ["GAFANHOTOS", "GELO", "GUERRA SEM FIM", "FOGO", "SILÊNCIO", "AFOGAMENTO", "ESPELHOS", "DESERTO"])
    locks = [(C.when(w), idx) for w, idx in C.prm("locks", [((0, 6), 0), ((0, 7), 1), ((0, 11), 2)])]
    locked = {items[idx] for _, idx in locks}; end_text = C.prm("end_text", "??????")
    a = gradient((18, 8, 8), (6, 2, 2)) + fog(t, 3)[..., None] * xp.array([30, 6, 6])
    im, d = canvas()
    d.rounded_rectangle([250, 210, 1030, 510], radius=30, fill=(14, 10, 10), outline=(170, 30, 30), width=8)
    show = None
    for tl, idx in locks:
        if tl <= t < tl + 0.9: show = items[idx]
    if show is None:
        show = end_text if t > C.at("end_at", (1,)) + 1.5 else items[int(t * 13) % len(items)]
    stable = show in locked or show == end_text
    jitter = 0 if stable else 20 * math.sin(t * 55)
    d.text((640, 360 + jitter), show, font=F(86 if len(show) < 12 else 70), fill=(236, 220, 200) if show in locked else (150, 60, 60), anchor="mm")
    for i in range(3):
        d.rectangle([220, 224 + i * 100, 240, 244 + i * 100], fill=(200, 40, 40) if int(t * 4 + i) % 2 else (70, 20, 20))
    a += arr(im)
    if show in locked and any(tl <= t < tl + 0.12 for tl, _ in locks): a += 60
    return finish(bloom(a, 150, 0.8))

def phone(C):
    """Celular vibrando com notificações; depois o chip (SIM) é retirado. params: sim_at (padrão (2,))."""
    t = C.t; t1 = C.at("sim_at", (2,))
    a = gradient((10, 12, 14), (3, 4, 5)) + fog(t, 6)[..., None] * 6
    im, d = canvas()
    sh = int(6 * math.sin(t * 60)) if (int(t * 3) % 2 == 0 and t < t1) else 0
    d.rounded_rectangle([450 + sh, 20, 830 + sh, 600], radius=44, fill=(8, 8, 10), outline=(70, 74, 80), width=5)
    if t < t1:
        d.rounded_rectangle([464 + sh, 40, 816 + sh, 580], radius=34, fill=(20, 40, 56))
        for i in range(6):
            tt = 1.3 + i * 0.35
            if t > tt:
                k = ease((t - tt) / 0.25); y = 70 + i * 82
                d.rounded_rectangle([480 + sh, y - 26 * (1 - k), 800 + sh, y + 64], radius=14, fill=(230, 236, 240))
                d.rectangle([500 + sh, y + 12, 700 + sh, y + 20], fill=(90, 100, 110)); d.rectangle([500 + sh, y + 34, 640 + sh, y + 40], fill=(140, 150, 160))
                d.ellipse([770 + sh, y + 6, 790 + sh, y + 26], fill=(220, 40, 40))
    else:
        k = ease((t - t1) / 1.2)
        d.rounded_rectangle([590 + 300 * k, 300, 650 + 300 * k, 380], radius=8, fill=(214, 176, 60)); d.rectangle([600 + 300 * k, 310, 640 + 300 * k, 330], fill=(120, 96, 30))
    a += arr(im)
    return finish(bloom(a, 150, 0.8))

def peephole(C):
    """Vista de um olho mágico: corredor quente e uma sombra comprida que cresce no chão."""
    t = C.t; k = ease(t / max(C.d, 1)); cx, cy, R = 640, 320, 290
    hall = gradient((150, 116, 72), (70, 50, 30))
    ih = Image.fromarray(to_cpu(hall).astype(onp.uint8)); dh = ImageDraw.Draw(ih)
    dh.polygon([(0, 720), (W0, 720), (760, 400), (520, 400)], fill=(54, 38, 24)); dh.rectangle([520, 250, 760, 400], fill=(24, 14, 10))
    for x in (110, 1170): dh.rectangle([x - 40, 180, x + 40, 470], fill=(48, 34, 20))
    fl = 1.0 if int(t * 9) % 13 else 0.4
    dh.ellipse([590, 130, 690, 190], fill=tuple(int(c * fl) for c in (255, 230, 170)))
    sh = ih.copy(); dsh = ImageDraw.Draw(sh)
    L = 40 + 520 * k
    dsh.polygon([(100, 720), (100 + 140, 720), (640 + 30, 640 - L * 0.35), (640 - 30, 640 - L * 0.35)], fill=(10, 8, 6))
    ih = Image.blend(ih, sh, 0.85 * k)
    mask = Image.new("L", (W0, H0), 0); ImageDraw.Draw(mask).ellipse([cx - R, cy - R, cx + R, cy + R], fill=255); mask = mask.filter(ImageFilter.GaussianBlur(2))
    a = arr(ih) * (arr(mask) / 255)[..., None]
    a *= (1 - 0.7 * xp.clip(xp.sqrt((XX - cx) ** 2 + (YY - cy) ** 2) / R, 0, 1) ** 2)[..., None]
    im2, d2 = canvas(); d2.ellipse([cx - R - 14, cy - R - 14, cx + R + 14, cy + R + 14], outline=(120, 96, 46), width=14)
    return xp.clip(bloom(a + arr(im2), 160, 0.5), 0, 255)

def pomegranate(C):
    """Diagrama de uma romã: casca = barreira, grãos = mundos, fronteiras entre eles.
    params: cells_at=(1,), shell_at=(1,14), borders_at=(1,24), visit_at=(2,), shell_label, borders_label."""
    t = C.t; cx, cy, R = 640, 330, 245
    a = gradient((18, 12, 10), (6, 4, 4)) + fog(t, 9)[..., None] * xp.array([18, 10, 8])
    im, d = canvas()
    p0 = ease(t / 1.6); tcell = C.at("cells_at", (1,)); tv = C.at("visit_at", (2,))
    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=(52, 14, 14))
    n = int(36 * ease((t - tcell) / 2.5)) if t > tcell else 0
    cells = []
    for i in range(36):
        r_ = (R - 40) * math.sqrt((i + 0.5) / 36); th = i * 2.39996
        cells.append((cx + r_ * math.cos(th), cy + r_ * math.sin(th)))
    for i, (x, y) in enumerate(cells[:n]):
        d.ellipse([x - 26, y - 26, x + 26, y + 26], fill=(110, 20, 24), outline=(30, 6, 8), width=3)
    tc, tf = C.at("shell_at", (1, 14)), C.at("borders_at", (1, 24))
    ring = (210, 70, 40) if tc <= t < tc + 2.5 else (140, 40, 30)
    if tc < t < tc + 3.0: d.text((cx + R + 40, cy - R * 0.8), C.prm("shell_label", "CASCA = barreira"), font=F(34), fill=(235, 210, 190), anchor="lm")
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=ring, width=int(10 + 14 * p0))
    if tf <= t < tf + 3.5:
        for i, (x, y) in enumerate(cells[:n]):
            d.ellipse([x - 30, y - 30, x + 30, y + 30], outline=(255, 230, 120), width=2)
        d.text((cx - R - 40, cy + R * 0.7), C.prm("borders_label", "fronteiras"), font=F(34), fill=(255, 230, 120), anchor="rm")
    if t > tv:
        for i, (x, y) in enumerate(cells[:n]):
            if (t - tv) * 12 > i: d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(255, 245, 230))
    a += arr(im)
    return finish(bloom(a, 150, 0.7))

def _melt_clock(d, x, y, r, drip, t):
    pts = [(x - r + 2 * r * i / 16, y + r * .1 + drip * (0.55 + 0.45 * math.sin(i * 1.3 + t * .8)) * math.sin(math.pi * i / 16) ** 0.6) for i in range(17)]
    d.polygon([(x - r, y - r * .1), (x + r, y - r * .1)] + pts[::-1], fill=(226, 212, 176), outline=(60, 40, 26))
    d.ellipse([x - r, y - r * .6, x + r, y + r * .5], fill=(232, 220, 186), outline=(60, 40, 26), width=4)
    for k in range(12):
        a_ = k * math.pi / 6; d.line([x + r * .8 * math.cos(a_), y - .05 * r + r * .38 * math.sin(a_), x + r * .9 * math.cos(a_), y - .05 * r + r * .43 * math.sin(a_)], fill=(40, 24, 14), width=3)
    d.line([x, y - .05 * r, x + r * .5 * math.cos(t * .5), y - .05 * r + r * .3 * math.sin(t * .5)], fill=(40, 24, 14), width=5)
    d.line([x, y - .05 * r, x - r * .2, y - r * .38], fill=(40, 24, 14), width=5)

def melt(C):
    """Paisagem surreal (estilo Dalí): relógios derretendo e o chão ondulando."""
    t = C.t
    a = gradient((226, 160, 96), (110, 70, 44))
    im, d = canvas((0, 0, 0)); d.rectangle([0, 440, W0, H0], fill=(86, 56, 36))
    d.polygon([(760, 440), (900, 300), (1080, 440)], fill=(100, 66, 42)); d.polygon([(60, 440), (180, 340), (340, 440)], fill=(120, 80, 50))
    d.rectangle([380, 230, 410, 450], fill=(40, 26, 16)); d.polygon([(405, 250), (640, 220), (650, 240), (405, 280)], fill=(40, 26, 16))
    d.polygon([(380, 420), (300, 470), (340, 470), (400, 440)], fill=(40, 26, 16))
    a = a * (arr(im).sum(2, keepdims=True) == 0) + arr(im)
    im2, d2 = canvas(); dr = 40 + 40 * ease(t / 6)
    _melt_clock(d2, 600, 290, 70, dr + 20 * math.sin(t), t); _melt_clock(d2, 900, 420, 80, dr * 1.4, t)
    _melt_clock(d2, 230, 480, 60, dr, t); d2.ellipse([150, 560, 350, 600], fill=(60, 40, 26))
    m = (arr(im2).sum(2, keepdims=True) > 0)
    a = a * (1 - m) + arr(im2) * m
    off = (16 * xp.sin(YY / 26.0 + t * 1.6) + 8 * xp.sin(YY / 9.0 - t * 2.3)).astype(int)
    a = a[YY, (XX + off) % W0]
    a *= 0.8
    return finish(a, 0.9)

def yolks(C):
    """Duas gemas numa frigideira que escorrem e se fundem numa só (ovo de gema dupla). params: at (padrão (0,13))."""
    t = C.t; tl = C.at("at", (0, 13)); s = ease((t - tl) / 2.6)
    a = gradient((18, 16, 14), (4, 4, 4)) + fog(t, 2)[..., None] * 6
    im, d = canvas(); cx, cy = 640, 330
    d.ellipse([cx - 330, cy - 200, cx + 330, cy + 220], fill=(52, 54, 58), outline=(90, 94, 98), width=10)
    d.ellipse([cx - 300, cy - 175, cx + 300, cy + 195], fill=(30, 30, 32))
    x1 = lerp(540, 610, s); x2 = lerp(740, 670, s); w_ = lerp(110, 190, s)
    if s > 0.7: d.ellipse([cx - w_ * 1.5, cy - w_ * 0.9, cx + w_ * 1.5, cy + w_ * 0.9], fill=(236, 232, 222))
    else:
        d.ellipse([x1 - 100, cy - 80, x1 + 100, cy + 80], fill=(236, 232, 222)); d.ellipse([x2 - 100, cy - 80, x2 + 100, cy + 80], fill=(236, 232, 222))
    d.ellipse([x1 - 46, cy - 46, x1 + 46, cy + 46], fill=(240, 176, 30)); d.ellipse([x2 - 46, cy - 46, x2 + 46, cy + 46], fill=(240, 176, 30))
    d.ellipse([x1 - 20, cy - 36, x1 - 2, cy - 18], fill=(255, 226, 120)); d.ellipse([x2 - 20, cy - 36, x2 - 2, cy - 18], fill=(255, 226, 120))
    a += arr(im) * 0.85
    off = (4 * s * xp.sin(YY / 12.0 + t * 3)).astype(int); a = a[YY, (XX + off) % W0]
    return finish(a, 1.0)

# ---------------------------------------------------------------- mar, redemoinho, riscos, contador
def wake(C):
    """Mar escuro e a esteira de algo seguindo rumo a uma ilha distante."""
    t = C.t
    a = gradient((10, 14, 16), (3, 4, 5))
    a += xp.exp(-(((XX - 1020) / 160.0) ** 2 + ((YY - 330) / 70.0) ** 2))[..., None] * xp.array([80, 96, 94])
    im, d = canvas(); d.ellipse([950, 320, 1100, 350], fill=(120, 130, 126))
    for x in (980, 1020, 1060): _column(d, x, 270, 330, 4, (130, 140, 136))
    a += arr(im); a = sea(a, t, 340)
    im2, d2 = canvas(); p = ease(t / max(C.d, 1)); x = 160 + 760 * p; y = 520 - 140 * p
    for j in range(6):
        L = 40 + j * 28
        d2.line([x, y, x - L * 1.6, y - L * 0.55], fill=(150, 190, 190), width=3); d2.line([x, y, x - L * 1.6, y + L * 0.55], fill=(150, 190, 190), width=3)
    d2.ellipse([x - 8, y - 5, x + 8, y + 5], fill=(220, 235, 235))
    a += arr(im2).clip(0, 90) * 0.9 * (1 - 0.3 * onp.random.default_rng(int(t * 10)).random())
    a += fog(t, 4)[..., None] * xp.array([10, 14, 14])
    return finish(bloom(a, 150, 0.7))

def vortex(C):
    """Fumaça em redemoinho e um núcleo de luz violeta que pulsa (sem rosto). params: core_at (padrão (1,7))."""
    t = C.t; te = C.at("core_at", C.params.get("eyes_at", (1, 7)))
    ix = (((_TH + t * 1.1 + _RR * 0.012) / (2 * math.pi)) % 1 * 959).astype(int); iy = xp.clip(_RR / 800 * 539, 0, 539).astype(int)
    n = NZ[1][iy, ix]
    a = xp.zeros((H0, W0, 3), xp.float32) + xp.array([6, 4, 10], xp.float32)
    a += (n ** 1.5)[..., None] * xp.array([120, 70, 170]) * xp.clip(1.3 - _RR / 700, 0, 1)[..., None]
    core = xp.exp(-(((XX - 640) / 150.0) ** 2 + ((YY - 340) / 230.0) ** 2))[..., None]
    a = a * (1 - 0.75 * core * (0.6 + 0.4 * n[..., None]))
    if t > te:
        k = ease((t - te) / 0.8); pulse = 0.8 + 0.2 * math.sin(t * 5)
        a += k * pulse * xp.exp(-(((XX - 640) / 90.0) ** 2 + ((YY - 330) / 90.0) ** 2))[..., None] * xp.array([170, 70, 255])
        a += k * xp.exp(-(((XX - 640) / 26.0) ** 2 + ((YY - 330) / 26.0) ** 2))[..., None] * xp.array([255, 210, 255])
    return finish(bloom(a, 120, 1.0, 20), 1.0)

vortex_core = vortex

def claw(C):
    """Quatro riscos que se abrem numa parede, pingando. params: at (padrão (0,13))."""
    t = C.t; tc = C.at("at", (0, 13))
    a = xp.zeros((H0, W0, 3), xp.float32) + xp.array([112, 98, 76], xp.float32) * (0.6 + 0.5 * fog(t * 0.2, 2, 4, 1)[..., None])
    for x in range(0, W0, 80): a[:, x:x + 2] *= 0.88
    if t > tc:
        k = ease((t - tc) / 0.5); im2, d2 = canvas()
        for i in range(4):
            x0, y0 = 420 + i * 62, 140 + i * 4
            d2.line([x0, y0, x0 + 190 * k, y0 + 440 * k], fill=(24, 10, 8), width=14)
            d2.line([x0 + 2, y0, x0 + 2 + 190 * k, y0 + 440 * k], fill=(150, 8, 8), width=6)
            for j in range(3):
                if k > 0.9: yy = y0 + 280 + ((t - tc) * (60 + 20 * j) + j * 30) % 200; d2.ellipse([x0 + 150 + j * 12, yy, x0 + 160 + j * 12, yy + 16], fill=(130, 6, 6))
        a = a + arr(im2) * 0.95
        if t - tc < 0.18: a += 150 * (1 - (t - tc) / 0.18)
    return finish(a * 0.85, 1.0)

def timer(C):
    """Relógio parado e depois um contador que passa do combinado e fica vermelho.
    params: clock_text="1:30", label="TEMPO NO INFERNO", start_at=(1,), over_at=(1,10), limit=600 (s), over=720 (s)."""
    t = C.t; t1 = C.at("start_at", (1,)); tz = C.at("over_at", (1, 10)); lim = C.prm("limit", 600); over = C.prm("over", 720)
    a = gradient((6, 6, 7), (2, 2, 2)); im, d = canvas()
    if t < t1:
        d.text((640, 300), C.prm("clock_text", "1:30"), font=F(260, True), fill=(70, 255, 130), anchor="mm")
        a += arr(im)
    else:
        if t < tz: sec = lim * ease((t - t1) / 3.4); col = (70, 255, 130)
        else: sec = over; col = (255, 40, 40)
        sh = int(10 * math.sin(t * 80)) if 0 <= t - tz < 0.6 else 0
        d.text((640 + sh, 290), f"{int(sec // 60):02d}:{int(sec % 60):02d}", font=F(280, True), fill=col, anchor="mm")
        d.text((640, 490), C.prm("label", "TEMPO NO INFERNO"), font=F(44), fill=(160, 160, 160), anchor="mm")
        a += arr(im)
        if 0 <= t - tz < 0.2: a += 80
    return finish(bloom(a, 100, 1.2, 24))

# ---------------------------------------------------------------- registro (nomes antigos mantidos como apelidos)
CUTSCENES = {
    "clock": clock, "bed": bed, "hospital": hospital, "void": void, "island": island, "columns": columns, "orbs": orbs,
    "days": days, "roulette": roulette, "phone": phone, "peephole": peephole, "pomegranate": pomegranate, "melt": melt,
    "yolks": yolks, "wake": wake, "vortex": vortex, "claw": claw, "timer": timer,
    # apelidos usados nos primeiros scripts
    "clock118": clock, "statues": columns, "tear": orbs, "dali": melt, "eye": yolks, "swim": wake, "shadow": vortex,
}
