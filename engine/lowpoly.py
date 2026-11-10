"""Mini-motor 3D low-poly no estilo PS2 (rasterizador por algoritmo do pintor, direto no PIL, em 480x270).

Tudo é geometria simples (caixas, cilindros, esferas, quadrados), sombreamento plano, luzes pontuais, névoa e vértices
"colados" na grade de pixels (o tremidinho típico). A matemática de vértices é vetorizada em numpy; o PIL só preenche polígonos.
Só serve para cenários, itens e objetos. O dithering e a quantização de cor ficam em ps2.py (pós-processamento)."""
import math
import numpy as np
from PIL import Image, ImageDraw
from .core import font

RW, RH = 480, 270
K = 12                     # nº máximo de vértices por face (faces menores repetem o último vértice)

def _pad(v):
    v = np.asarray(v, float)
    if len(v) < K: v = np.vstack([v, np.repeat(v[-1:], K - len(v), 0)])
    return v

class Scene:
    def __init__(self, bg=(6, 8, 10), fog=None, fog_near=4.0, fog_far=22.0, ambient=0.38, light=(-0.35, 0.85, -0.4)):
        self.bg, self.fog = bg, fog or bg
        self.fog_near, self.fog_far, self.ambient = fog_near, fog_far, ambient
        L = np.array(light, float); self.L = L / np.linalg.norm(L)
        self.V, self.col, self.emis, self.layer, self.ctr, self.two = [], [], [], [], [], []
        self.lights, self.labels, self.bg_draw = [], [], []

    # ---------------- primitivas
    def face(self, verts, color, emis=False, layer=1, center=None, two_sided=False):
        self.V.append(_pad(verts)); self.col.append(color); self.emis.append(emis); self.layer.append(layer)
        self.ctr.append(np.full(3, np.nan) if center is None else np.asarray(center, float)); self.two.append(two_sided)

    def quad(self, p0, p1, p2, p3, color, emis=False, layer=1):
        """Quadrado solto (chão, parede, painel): visível dos dois lados."""
        self.face([p0, p1, p2, p3], color, emis, layer, None, True)

    def box(self, c, s, color, yaw=0.0, emis=False, layer=1, top=None):
        cx, cy, cz = c; hx, hy, hz = s[0] / 2, s[1] / 2, s[2] / 2
        pts = np.array([[x, y, z] for x in (-hx, hx) for y in (-hy, hy) for z in (-hz, hz)])
        if yaw:
            cs, sn = math.cos(yaw), math.sin(yaw); pts = np.c_[pts[:, 0] * cs + pts[:, 2] * sn, pts[:, 1], -pts[:, 0] * sn + pts[:, 2] * cs]
        pts = pts + np.array(c, float)
        for q in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 1, 5, 4), (2, 3, 7, 6), (0, 2, 6, 4), (1, 3, 7, 5)):
            col = top if (top and q == (2, 3, 7, 6)) else color
            self.face(pts[list(q)], col, emis, layer, c)

    def cyl(self, c, r, h, color, n=8, emis=False, layer=1, r_top=None):
        """Cilindro/cone de n lados em pé (c = centro da base)."""
        r_top = r if r_top is None else r_top
        ang = [2 * math.pi * i / n for i in range(n)]
        bot = [(c[0] + r * math.cos(a), c[1], c[2] + r * math.sin(a)) for a in ang]
        topv = [(c[0] + r_top * math.cos(a), c[1] + h, c[2] + r_top * math.sin(a)) for a in ang]
        ctr = (c[0], c[1] + h / 2, c[2])
        for i in range(n):
            j = (i + 1) % n; self.face([bot[i], bot[j], topv[j], topv[i]], color, emis, layer, ctr)
        self.face(topv, color, emis, layer, ctr)

    def sphere(self, c, r, color, lat=4, lon=8, emis=False, layer=1, sy=1.0):
        """Esfera low-poly (sy < 1 achata, sy > 1 estica na vertical)."""
        rows = []
        for i in range(lat + 1):
            phi = math.pi * i / lat - math.pi / 2
            rows.append([(c[0] + r * math.cos(phi) * math.cos(2 * math.pi * j / lon), c[1] + r * sy * math.sin(phi), c[2] + r * math.cos(phi) * math.sin(2 * math.pi * j / lon)) for j in range(lon)])
        for i in range(lat):
            for j in range(lon):
                k = (j + 1) % lon; self.face([rows[i][j], rows[i][k], rows[i + 1][k], rows[i + 1][j]], color, emis, layer, c)

    def ring(self, c, r0, r1, color, n=16, y_axis=True, emis=True, layer=1, phase=0.0):
        """Anel plano (horizontal se y_axis, senão vertical de frente para +z)."""
        for i in range(n):
            a0, a1 = phase + 2 * math.pi * i / n, phase + 2 * math.pi * (i + 1) / n
            def pt(r, a): return (c[0] + r * math.cos(a), c[1], c[2] + r * math.sin(a)) if y_axis else (c[0] + r * math.cos(a), c[1] + r * math.sin(a), c[2])
            self.quad(pt(r0, a0), pt(r1, a0), pt(r1, a1), pt(r0, a1), color, emis, layer)

    def checker(self, x0, x1, z0, z1, y, tile, c1, c2, layer=0):
        """Chão em xadrez (a 'textura' do PS2)."""
        xs = np.arange(x0, x1, tile)
        for i, x in enumerate(xs):
            for j, z in enumerate(np.arange(z0, z1, tile)):
                self.quad((x, y, z), (x + tile, y, z), (x + tile, y, z + tile), (x, y, z + tile), c1 if (i + j) % 2 == 0 else c2, False, layer)

    def light(self, pos, color, power=1.0): self.lights.append((np.asarray(pos, float), np.asarray(color, float) / 255.0, power))
    def label(self, pos, text, color, size=1.0, mono=True): self.labels.append((np.asarray(pos, float), text, color, size, mono))

    # ---------------- render
    def render(self, pos, yaw, pitch, fov=70.0, tint=None):
        img = Image.new("RGB", (RW, RH), self.bg); d = ImageDraw.Draw(img)
        for fn in self.bg_draw: fn(d)
        pos = np.asarray(pos, float)
        cy_, sy_, cp, sp = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch)
        Ry = np.array([[cy_, 0, -sy_], [0, 1, 0], [sy_, 0, cy_]])            # Ry(-yaw)
        Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
        M = Rx @ Ry
        f = (RW / 2) / math.tan(math.radians(fov) / 2)
        if not self.V: return img
        V = np.array(self.V); col = np.array(self.col, float); emis = np.array(self.emis); layer = np.array(self.layer)
        ctr = np.array(self.ctr); two = np.array(self.two)
        cam = (V - pos) @ M.T                                               # (F,K,3)
        ok = cam[:, :, 2].min(1) > 0.12
        fc = V.mean(1)                                                       # centro de cada face (mundo)
        n = np.cross(V[:, 1] - V[:, 0], V[:, 2] - V[:, 0]); n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-9)
        has_c = ~np.isnan(ctr[:, 0])
        flip = np.where(has_c, ((fc - ctr) * n).sum(1) < 0, ((pos - fc) * n).sum(1) < 0)
        n = np.where(flip[:, None], -n, n)
        facing = ((fc - pos) * n).sum(1) < 0                                 # de frente para a câmera
        ok &= facing | two
        sx = RW / 2 + f * cam[:, :, 0] / np.maximum(cam[:, :, 2], 0.12); sy = RH / 2 - f * cam[:, :, 1] / np.maximum(cam[:, :, 2], 0.12)
        sx, sy = np.round(sx * 2) / 2, np.round(sy * 2) / 2                  # vértices colados na grade (tremidinho PS2)
        ok &= ~((sx.max(1) < 0) | (sx.min(1) > RW) | (sy.max(1) < 0) | (sy.min(1) > RH))
        depth = cam[:, :, 2].mean(1)
        # sombreamento plano + luzes pontuais + névoa
        lit = self.ambient + 0.62 * np.clip((n * self.L).sum(1), 0, 1)
        shade = np.repeat(lit[:, None], 3, 1)
        for lp, lc, pw in self.lights:
            dv = lp - fc; dist2 = (dv ** 2).sum(1); ndl = np.clip((n * dv / (np.sqrt(dist2)[:, None] + 1e-9)).sum(1), 0, 1)
            shade += (pw * ndl / (1 + 0.55 * dist2))[:, None] * lc
        rgb = np.where(emis[:, None], col, np.clip(col * shade, 0, 255))
        ff = np.clip((depth - self.fog_near) / (self.fog_far - self.fog_near), 0, 1)[:, None]
        ff = np.where(emis[:, None], ff * 0.35, ff)
        rgb = rgb * (1 - ff) + np.array(self.fog, float) * ff
        idx = np.where(ok)[0]
        order = sorted(idx, key=lambda i: (layer[i], -depth[i]))
        for i in order:
            pts = list(zip(sx[i], sy[i])); d.polygon(pts, fill=tuple(int(c) for c in rgb[i]))
        for p, text, c, size, mono in self.labels:                           # textos 3D (ex.: dígitos do relógio)
            q = (p - pos) @ M.T
            if q[2] > 0.2:
                px, py = RW / 2 + f * q[0] / q[2], RH / 2 - f * q[1] / q[2]
                d.text((px, py), text, font=font("FreeMonoBold.ttf" if mono else "FreeSansBold.ttf", max(5, int(size * f / q[2]))), fill=c, anchor="mm")
        return img

def look_at(pos, target):
    """yaw/pitch para olhar de pos para target."""
    d = np.asarray(target, float) - np.asarray(pos, float)
    return math.atan2(d[0], d[2]), math.atan2(d[1], math.hypot(d[0], d[2]))
