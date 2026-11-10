import json, os, sys, math, glob, bisect, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Padrão "imagens de IA + legenda dourada": uma imagem por frase (imagens/NN.jpg), zoom lento (Ken Burns),
# glitch curto nos cortes, legenda dourada em itálico com contorno e franjas de cor, cartões "REGRA N°x",
# moldura de TV antiga com cantos arredondados, linhas de varredura e grão.
W, H, FPS = 1080, 1920, 30
B = "build"
TL = json.load(open(f"{B}/timeline.json"))
A = TL["anchors"]
TOTAL = TL["total"]
IMG_DIR = "imagens"
rng = np.random.default_rng(21)

FF = "/usr/share/fonts/truetype/freefont/"
F_OBL = FF + "FreeSansBoldOblique.ttf"
F_SANS = FF + "FreeSans.ttf"
F_MONO = FF + "FreeMonoBold.ttf"
F_SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"
def font(p, s): return ImageFont.truetype(p, s)
def ease(x): x = min(1, max(0, x)); return x * x * (3 - 2 * x)
def lerp(a, b, x): return a + (b - a) * x

GOLD, RED = (255, 196, 28), (255, 52, 48)

# ---------------- plano de cortes ----------------
SHOTS = []   # um por frase
for s in TL["scenes"]:
    for p in s["phrases"]:
        SHOTS.append({"p": p, "scene": s["id"]})
for i, sh in enumerate(SHOTS):
    sh["start"] = A["cuts"][i]
    sh["end"] = A["cuts"][i + 1] if i + 1 < len(SHOTS) else TOTAL
STARTS = [sh["start"] for sh in SHOTS]

def dem_level(t):
    for s, e in A["dem_iv"]:
        a, b = s - 0.05, e + 0.1
        if a <= t <= b: return min(1.0, (t - a) / 0.08, (b - t) / 0.15)
    return 0.0

# ---------------- imagens ----------------
BW, BH = int(W * 1.3), int(H * 1.3)
BIG = {}
sys.path.insert(0, os.getcwd())
import script as _script
from script import IMAGES
END_Q = getattr(_script, 'END_QUESTION', 'Você aguentaria até as 7h?')

def placeholder(img_id, look):
    """Imagem provisória (até você colocar a imagem gerada por IA em imagens/NN.jpg)."""
    base = {"sepia": (52, 38, 24), "bw": (40, 40, 42), "teal": (18, 46, 40)}.get(look, (40, 40, 40))
    yy = np.linspace(0, 1, H)[:, None, None]
    arr = np.zeros((H, W, 3), np.float32) + np.array(base, np.float32) * (0.55 + 0.9 * (1 - yy))
    arr += rng.normal(0, 6, (H, W, 1))
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
    lk, desc, prompt = IMAGES.get(img_id, (look, "", ""))
    d.text((W / 2, 1240), f"IMAGEM {img_id}", font=font(F_MONO, 110), fill=(230, 220, 200), anchor="mm")
    d.text((W / 2, 1370), desc, font=font(F_SANS, 52), fill=(230, 220, 200), anchor="mm")
    d.text((W / 2, 1470), f"coloque o arquivo imagens/{img_id}.jpg", font=font(F_SANS, 34), fill=(170, 160, 140), anchor="mm")
    return im

def grade(arr, look):
    lum = (arr[..., 0] * 0.299 + arr[..., 1] * 0.587 + arr[..., 2] * 0.114)[..., None]
    if look == "sepia":
        out = 0.55 * arr + 0.45 * lum * np.array([1.08, 0.93, 0.72], np.float32)
    elif look == "teal":
        out = 0.62 * arr + 0.38 * lum * np.array([0.70, 1.06, 0.94], np.float32)
    else:
        out = lum * np.array([0.97, 1.0, 1.04], np.float32)
    out = 255.0 * np.clip(out / 255.0, 0, 1) ** 1.1
    return np.clip(out * 1.05, 0, 255)

def load_big(img_id, look):
    key = (img_id, look)
    if key in BIG: return BIG[key]
    path = next(iter(glob.glob(f"{IMG_DIR}/{img_id}.*")), None)
    im = Image.open(path).convert("RGB") if path else placeholder(img_id, look)
    iw, ih = im.size
    sc = max(BW / iw, BH / ih)
    im = im.resize((int(iw * sc) + 1, int(ih * sc) + 1), Image.LANCZOS)
    if sc > 1.5: im = im.filter(ImageFilter.UnsharpMask(radius=2.2, percent=70, threshold=3))
    l, t_ = (im.width - BW) // 2, (im.height - BH) // 2
    im = im.crop((l, t_, l + BW, t_ + BH))
    arr = grade(np.asarray(im).astype(np.float32), look)
    BIG[key] = Image.fromarray(arr.astype(np.uint8))
    return BIG[key]

def kenburns(i):
    r = np.random.default_rng(1000 + i)
    mode = i % 4
    if mode == 0:   z0, z1, c0, c1 = 1.08, 1.30, (0.5, 0.5), (0.5, 0.42)
    elif mode == 1: z0, z1, c0, c1 = 1.30, 1.08, (0.5, 0.45), (0.5, 0.5)
    elif mode == 2: z0, z1, c0, c1 = 1.18, 1.18, (0.38, 0.5), (0.62, 0.5)
    else:           z0, z1, c0, c1 = 1.08, 1.28, (0.55, 0.55), (0.45, 0.4)
    return z0, z1, c0, c1

def shot_image(i, t):
    sh = SHOTS[i]; p = sh["p"]
    big = load_big(p["img"], p["look"])
    lt = (t - sh["start"]) / max(0.1, sh["end"] - sh["start"])
    z0, z1, c0, c1 = kenburns(i)
    zf = lerp(z0, z1, ease(lt))
    vw, vh = BW / zf, BH / zf
    cx = lerp(c0[0], c1[0], ease(lt)) * BW + 5 * math.sin(t * 1.9) + 2.5 * math.sin(t * 8.3)
    cy = lerp(c0[1], c1[1], ease(lt)) * BH + 6 * math.sin(t * 1.3 + 1) + 3 * math.sin(t * 7.1)
    left = min(max(cx - vw / 2, 0), BW - vw); top = min(max(cy - vh / 2, 0), BH - vh)
    im = big.resize((W, H), Image.BILINEAR, box=(left, top, left + vw, top + vh))
    return np.asarray(im).astype(np.float32)

# ---------------- legenda dourada ----------------
SUB_F = font(F_OBL, 72)
TITLE_F = font(F_OBL, 132)
SMALL_TITLE_F = font(F_OBL, 84)

def parse_words(text):
    out, inside = [], False
    for tok in text.split(" "):
        if "[[" in tok: inside = True
        out.append((tok.replace("[[", "").replace("]]", ""), inside))
        if "]]" in tok: inside = False
    return out

def layout(items, f, maxw=900):
    lines, cur = [], []
    for w, fl in items:
        test = " ".join([c[0] for c in cur] + [w])
        if cur and f.getlength(test) > maxw: lines.append(cur); cur = [(w, fl)]
        else: cur.append((w, fl))
    if cur: lines.append(cur)
    return lines

def draw_line(d, glow_d, y, ln, f, t):
    total = sum(f.getlength(w + " ") for w, _ in ln) - f.getlength(" ")
    x = (W - total) / 2
    for w, fl in ln:
        col = RED if fl else GOLD
        fx = 4 + 2 * math.sin(t * 17)
        d.text((x - fx, y + 3), w, font=f, fill=(40, 220, 110, 150))     # franja verde
        d.text((x + fx, y - 3), w, font=f, fill=(230, 40, 40, 170))      # franja vermelha
        d.text((x, y), w, font=f, fill=col + (255,), stroke_width=7, stroke_fill=(0, 0, 0, 255))
        if fl: glow_d.text((x, y), w, font=f, fill=(255, 40, 40, 255), stroke_width=7, stroke_fill=(255, 40, 40, 255))
        x += f.getlength(w + " ")

def draw_subtitle(t, i):
    sh = SHOTS[i]; p = sh["p"]
    if not p["text"]: return None
    nxt = SHOTS[i + 1]["p"]["start"] if i + 1 < len(SHOTS) else 1e9
    t0, t1 = p["start"] - 0.05, min(p["end"] + 0.4, nxt - 0.1)
    if not (t0 <= t <= t1): return None
    a = min(1.0, (t - t0) / 0.1, (t1 - t) / 0.1)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0)); gd = ImageDraw.Draw(glow)
    text = p["text"]
    if p["title"]:
        if text.startswith(("DIÁRIA", "ALUGUEL")):   # cartão do valor: palavra pequena + valor grande
            lines = [(SMALL_TITLE_F, [(text.split(" ")[0], False)]), (TITLE_F, [(w, False) for w in text.split(" ")[1:]])]
        else:
            pre, _, rule = text.partition("REGRA")
            lines = ([(SMALL_TITLE_F, [(w, False) for w in pre.strip().split(" ")])] if pre.strip() else []) + \
                    [(TITLE_F, [("REGRA", False), (rule.strip(), False)])]
        pulse = 1 + 0.03 * math.sin(t * 14)
        total_h = sum(110 if f is SMALL_TITLE_F else 150 for f, _ in lines)
        y = H * 0.40 - total_h / 2
        for f, ln in lines:
            draw_line(d, gd, y, ln, f, t); y += 110 if f is SMALL_TITLE_F else 150
    else:
        lines = layout(parse_words(text), SUB_F)
        y = H * 0.40 - len(lines) * 90 / 2
        for ln in lines:
            draw_line(d, gd, y, ln, SUB_F, t); y += 90
    g = glow.filter(ImageFilter.GaussianBlur(16))
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    base.alpha_composite(g); base.alpha_composite(layer)
    arr = np.asarray(base).astype(np.float32)
    arr[..., 3] *= a
    return arr

# ---------------- moldura, varredura, grão ----------------
_m = Image.new("L", (W, H), 0)
ImageDraw.Draw(_m).rounded_rectangle([16, 16, W - 16, H - 16], radius=58, fill=255)
FRAME = (np.asarray(_m.filter(ImageFilter.GaussianBlur(1.6))).astype(np.float32) / 255)[..., None]
EDGE = (np.asarray(_m.filter(ImageFilter.GaussianBlur(46))).astype(np.float32) / 255)[..., None]
SHADE = 0.62 + 0.38 * np.clip(EDGE * 1.25, 0, 1)
yy, xx = np.mgrid[0:H, 0:W]
VIG = (1 - 0.5 * np.clip((((xx - W / 2) / (W * 0.8)) ** 2 + ((yy - H / 2) / (H * 0.75)) ** 2), 0, 1)).astype(np.float32)[..., None]
SCAN = np.ones((H, 1, 1), np.float32); SCAN[::3] = 0.88
MOIRE = (1 - 0.05 * np.sin(xx * 1.9 + yy * 0.7)).astype(np.float32)[..., None]
GRAIN = [rng.normal(0, 11, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1) for _ in range(6)]

def glitch(f, lt, strength=1.0):
    """Corte com glitch: fatias deslocadas, separação RGB e clarão."""
    k = max(0.0, 1 - lt / 0.2)
    for _ in range(int(9 * k) + 1):
        y0 = int(rng.integers(0, H - 120)); hgt = int(rng.integers(12, 140))
        f[y0:y0 + hgt] = np.roll(f[y0:y0 + hgt], int(rng.integers(-90, 90) * k), axis=1)
    sh = int(14 * k * strength)
    f[..., 0] = np.roll(f[..., 0], sh, axis=1); f[..., 2] = np.roll(f[..., 2], -sh, axis=1)
    f *= 1 + 0.55 * k
    return f

def end_card(t, p):
    img = Image.new("RGB", (W, H), (6, 6, 6)); d = ImageDraw.Draw(img, "RGBA")
    k = int(t * 4.2); r = (k * 2654435761) % 1000 / 1000
    on = (0.55 if r < 0.12 else 1.0) if t > p["start"] - 0.1 else 0
    if on > 0:
        col = (int(230 * on), int(25 * on), int(25 * on))
        glow = Image.new("RGB", (W, H)); gd = ImageDraw.Draw(glow)
        gd.text((W / 2, 860), "TEMOS", font=font(F_SERIF, 150), fill=col, anchor="mm")
        gd.text((W / 2, 1020), "VAGAS", font=font(F_SERIF, 150), fill=col, anchor="mm")
        gl = np.asarray(glow.filter(ImageFilter.GaussianBlur(22))).astype(np.float32)
        img = Image.fromarray(np.clip(np.asarray(img).astype(np.float32) + gl * 1.3 + np.asarray(glow) * 0.9, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img, "RGBA")
    if t > p["end"] + 0.2:
        a = min(1, (t - p["end"] - 0.2) / 0.5)
        d.text((W / 2, 1200), END_Q, font=font(F_SANS, 52), fill=(230, 225, 215, int(255 * a)), anchor="mm")
        d.text((W / 2, 1290), "@temosvagas.terror", font=font(F_MONO, 46), fill=(200, 30, 30, int(255 * a)), anchor="mm")
    return np.asarray(img).astype(np.float32)

# ---------------- quadro ----------------
def frame(t):
    i = max(0, bisect.bisect_right(STARTS, t) - 1)
    sh = SHOTS[i]; p = sh["p"]; lt = t - sh["start"]
    lvl = dem_level(t)
    if sh["scene"] == "end":
        f = end_card(t, p)
    else:
        f = shot_image(i, t)
        # cintilação de filme antigo
        f *= 1 + 0.05 * math.sin(t * 47) + 0.03 * math.sin(t * 13.1) + (0.07 if (int(t * 24) * 2654435761) % 1000 < 25 else 0)
        f[..., 0] += 36 * lvl
        sub = draw_subtitle(t, i)
        if sub is not None:
            a = sub[..., 3:4] / 255.0
            f = f * (1 - a) + sub[..., :3] * a
    if sh["scene"] != "end":
        f = f * VIG * SCAN * MOIRE
        f[..., 0] = np.roll(f[..., 0], 2, axis=1); f[..., 2] = np.roll(f[..., 2], -2, axis=1)
    if lt < 0.2 and i > 0: f = glitch(f, lt)
    if lvl > 0.4:
        sx = int(14 * lvl * math.sin(t * 90))
        f = np.roll(f, sx, axis=1)
        for _ in range(4):
            y0 = int(rng.integers(0, H - 80)); hgt = int(rng.integers(8, 60))
            f[y0:y0 + hgt] = np.roll(f[y0:y0 + hgt], int(rng.integers(-40, 40)), axis=1)
    for k_ in A["knocks"]:
        if 0 <= t - k_ < 0.16: f = np.roll(f, int(16 * (1 - (t - k_) / 0.16) * (1 if int(t * 90) % 2 else -1)), axis=1)
    f = f * SHADE
    f = f * FRAME + (1 - FRAME) * 9.0
    f = f + GRAIN[int(t * FPS) % 6]
    if t < 0.5: f *= t / 0.5
    if t > TOTAL - 1.0: f *= max(0, (TOTAL - t) / 1.0)
    return np.clip(f, 0, 255).astype(np.uint8)

if __name__ == "__main__":
    if sys.argv[1] == "preview":
        for ts in sys.argv[2:]:
            Image.fromarray(frame(float(ts))).save(f"{B}/prev_{ts}.png")
        sys.exit()
    # render por faixas de cena, em paralelo seria possível; aqui sequencial, um arquivo por cena
    sid = sys.argv[2] if len(sys.argv) > 2 else None
    for s in TL["scenes"]:
        if sid and s["id"] != sid: continue
        f0, f1 = round(s["start"] * FPS), round(s["end"] * FPS)
        tmp = f"{B}/scene_{s['id']}.tmp.mp4"
        pr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                               "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", tmp],
                              stdin=subprocess.PIPE)
        for fi in range(f0, f1):
            pr.stdin.write(frame(fi / FPS).tobytes())
        pr.stdin.close()
        if pr.wait() == 0:
            os.replace(tmp, f"{B}/scene_{s['id']}.mp4"); print("ok", s["id"], f1 - f0)
