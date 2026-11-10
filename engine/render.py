"""Render do estilo "leitura elegante" (YouTube 16:9, 1920x1080): tipografia serifada, palavras que surgem no ritmo da voz,
palavras-chave em destaque, poeira de luz, barras de cinema e cutscenes 2D só de cenários/objetos (cutscenes.py).
Compõe o fundo em 720p e sobe para 1080p uma vez; o texto e o brilho são aplicados só na área que muda.
Uso (normalmente via engine.build):  python -m engine.render episodios/NN-nome [all|preview t|cena:seg ...]"""
import bisect, math, os, re, subprocess, sys, time
import numpy as np
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFilter
from . import core
from .core import xp, GPU, to_cpu, resize_img, font, ease, Ctx, arr as pil_arr
from .cutscenes import CUTSCENES
from .episode import Episode

W, H, FPS = 1920, 1080, 30
IVORY, ACCENT, GOLD = (240, 232, 214), (238, 70, 56), (232, 190, 96)
BASE = {"sepia": (34, 24, 15), "teal": (9, 28, 28), "bw": (24, 24, 27)}
BAR = 58
NCH = 14

class S: pass          # estado do episódio carregado (preenchido por setup(), também em cada processo do Pool)
S.ready = None

def setup(ep_path):
    import json
    if S.ready == str(ep_path): return
    ep = Episode(ep_path)
    S.ep, S.cfg = ep, ep.cfg
    S.TL = json.load(open(ep.build / "timeline.json", encoding="utf-8"))
    S.A, S.TOTAL = S.TL["anchors"], S.TL["total"]
    S.OUT = ep.build / "chunks"; S.OUT.mkdir(exist_ok=True)
    S.rng = np.random.default_rng(33)
    S.cut = {s.id: (s.cut, s.params) for s in ep.scenes if s.cut}
    S.emph = {re.sub(r"[^\wÀ-ÿ]", "", w.lower()) for w in S.cfg["emph"]}
    S.shots = [{"s": sc, "start": S.A["cuts"][i]} for i, sc in enumerate(S.TL["scenes"])]
    for i, sh in enumerate(S.shots): sh["end"] = S.shots[i + 1]["start"] if i + 1 < len(S.shots) else S.TOTAL
    S.starts = [sh["start"] for sh in S.shots]
    S.dust = np.random.default_rng(8).random((46, 4))
    S.ly_, S.lx_ = xp.mgrid[0:180, 0:320]
    # máscaras e grão já no backend (GPU ou CPU)
    m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).rounded_rectangle([10, 10, W - 10, H - 10], radius=38, fill=255)
    S.FRAME = (pil_arr(m.filter(ImageFilter.GaussianBlur(1.6))) / 255)[..., None]
    S.FRAME_I = (1 - S.FRAME) * 6.0
    y7, x7 = xp.mgrid[0:720, 0:1280]
    S.VIG = (1 - 0.55 * xp.clip((((x7 - 640) / (1280 * 0.72)) ** 2 + ((y7 - 360) / (720 * 0.78)) ** 2), 0, 1)).astype(xp.float32)[..., None]
    S.BAND = (1 - 0.55 * xp.clip((y7 - 720 * 0.60) / (720 * 0.3), 0, 1)).astype(xp.float32)[..., None]
    S.VIGBAND = S.VIG * S.BAND
    S.GRAIN = [xp.asarray(S.rng.normal(0, 8, (H // 2, W // 2, 1)).astype(np.float32).repeat(2, 0).repeat(2, 1)) for _ in range(6)]
    S.style = S.cfg["style"]
    if S.style == "ps2":
        from . import ps2
        S.ps2 = ps2
        S.SCAN = xp.ones((H, 1, 1), xp.float32); S.SCAN[3::4] = 0.84        # linhas de varredura entre os pixels grandes
    S.ready = str(ep_path)

def is_emph(w): return re.sub(r"[^\wÀ-ÿ]", "", w.lower()) in S.emph

def ctx_for(i, t):
    sh = S.shots[i]; s0 = sh["start"]
    ph = [{"start": p["start"] - s0, "end": p["end"] - s0, "words": [w - s0 for w in p["words"]]} for p in sh["s"]["phrases"]]
    name, params = S.cut[sh["s"]["id"]]
    return Ctx(t - s0, sh["end"] - s0, ph, params), name

YELLOW = (255, 236, 0)

def draw_words_ps2(layer, phrase, t, mode):
    """Legenda amarela padrão (sans bold, contorno preto), cada palavra surge quando é narrada."""
    d = ImageDraw.Draw(layer)
    words = phrase["text"].split(" "); ts = phrase["words"]
    if len(ts) != len(words):
        ts = [phrase["start"] + (phrase["end"] - phrase["start"]) * i / max(1, len(words)) for i in range(len(words))]
    if mode == "cap": sizes, maxw, yc, stroke = [58, 54, 50], 1560, H * 0.865, 5
    else: sizes, maxw, yc, stroke = [92, 84, 76, 68, 60], 1500, H * 0.5, 6
    for sz in sizes:
        f = font("FreeSansBold.ttf", sz); lines = wrap(words, f, maxw)
        if (mode == "cap" and len(lines) <= 2) or (mode == "big" and len(lines) <= 5): break
    lh = int(sz * 1.28); y = yc - len(lines) * lh / 2; gi = 0
    for ln in lines:
        x = (W - f.getlength(" ".join(ln))) / 2
        for w in ln:
            a = ease((t - ts[gi]) / 0.06)
            if a > 0: d.text((x, y), w, font=f, fill=YELLOW + (int(255 * a),), stroke_width=stroke, stroke_fill=(0, 0, 0, int(255 * a)))
            x += f.getlength(w + " "); gi += 1
        y += lh

def overlay_ps2(t, i):
    sh = S.shots[i]; phrases = sh["s"]["phrases"]; cutscene = sh["s"]["id"] in S.cut
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer); ia = S.A["intro_title"]
    if i == 0 and S.cfg["title"] and ia[0] <= t <= ia[1]:
        a = min(1.0, (t - ia[0]) / 0.3, (ia[1] - t) / 0.4)
        for n, line in enumerate(S.cfg["title"]):
            d.text((W / 2, H * 0.36 + n * 118), line.upper(), font=font("FreeSansBold.ttf", 96 if n == 0 else 84), fill=YELLOW + (int(255 * a),),
                   stroke_width=6, stroke_fill=(0, 0, 0, int(255 * a)), anchor="mm")
    else:
        for k, p in enumerate(phrases):
            nxt = phrases[k + 1]["start"] if k + 1 < len(phrases) else (S.shots[i + 1]["s"]["phrases"][0]["start"] if i + 1 < len(S.shots) else 1e9)
            t0, t1 = p["start"] - 0.05, min(p["end"] + 0.6, nxt - 0.1)
            if not (t0 <= t <= t1) or not p["text"]: continue
            if p["title"]:
                d.text((W / 2, H * 0.44), p["text"].upper(), font=font("FreeSansBold.ttf", 150), fill=YELLOW + (255,), stroke_width=8, stroke_fill=(0, 0, 0, 255), anchor="mm")
            else: draw_words_ps2(layer, p, t, "cap" if cutscene else "big")
            a = min(1.0, (t1 - t) / 0.25)
            if a < 1: layer.putalpha(layer.getchannel("A").point(lambda v: int(v * max(0, a))))
            break
    bb = layer.getchannel("A").getbbox()
    if bb is None: return None
    box = (max(0, bb[0] - 4), max(0, bb[1] - 4), min(W, bb[2] + 4), min(H, bb[3] + 4))
    return box, pil_arr(layer.crop(box))

def end_card_ps2(t, sh):
    p = sh["s"]["phrases"][0]; cfg = S.cfg
    img = Image.new("RGB", (W, H), (4, 4, 6)); d = ImageDraw.Draw(img, "RGBA")
    if t > p["start"] - 0.1: d.text((W / 2, 420), "TEMOS VAGAS", font=font("FreeSansBold.ttf", 170), fill=YELLOW + (255,), stroke_width=8, stroke_fill=(0, 0, 0, 255), anchor="mm")
    if t > p["end"] + 0.4:
        a = int(255 * min(1, (t - p["end"] - 0.4) / 0.6))
        d.text((W / 2, 640), cfg["end_question"], font=font("FreeSansBold.ttf", 56), fill=YELLOW + (a,), anchor="mm")
        d.text((W / 2, 730), cfg["end_note"], font=font("FreeSans.ttf", 40), fill=(220, 220, 200, a), anchor="mm")
        d.text((W / 2, 810), cfg["channel"], font=font("FreeSansBold.ttf", 44), fill=YELLOW + (a,), anchor="mm")
    return pil_arr(img)

def frame_ps2(t):
    i = max(0, bisect.bisect_right(S.starts, t) - 1)
    sh = S.shots[i]; sid = sh["s"]["id"]; lt = t - sh["start"]
    if sid == S.cfg["end_scene"]:
        f = end_card_ps2(t, sh)
    else:
        if sid in S.cut:
            C, name = ctx_for(i, t)
            a = S.ps2.post(S.ps2.PS2[name](C))
        else:
            a = xp.zeros((270, 480, 3), xp.float32) + xp.array([5, 5, 8], xp.float32)       # só texto: fundo preto minimalista
        ia = S.A["intro_title"]
        if i == 0 and t < ia[1] + 0.4: a = a * (0.35 + 0.65 * ease((t - ia[1]) / 0.4))
        f = xp.repeat(xp.repeat(a, 4, 0), 4, 1) * S.SCAN                                     # 480x270 -> 1920x1080 (pixels grandes)
        ov = overlay_ps2(t, i)
        if ov is not None:
            (x0, y0, x1, y1), ly = ov
            al = ly[..., 3:4] / 255.0; f[y0:y1, x0:x1] = f[y0:y1, x0:x1] * (1 - al) + ly[..., :3] * al
        if lt < 0.12 and i > 0: f = f * (lt / 0.12)                                          # corte seco, com um piscar
    for k_ in S.A["knocks"]:
        if 0 <= t - k_ < 0.2: f = xp.roll(f, int(10 * (1 - (t - k_) / 0.2) * (1 if int(t * 90) % 2 else -1)), axis=1)
    if t < 0.6: f = f * (t / 0.6)
    if t > S.TOTAL - 1.5: f = f * max(0, (S.TOTAL - t) / 1.5)
    return to_cpu(xp.clip(f, 0, 255).astype(xp.uint8))

def grade(a, look, k=1.0):
    lum = (a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114)[..., None]
    if look == "sepia": out = 0.55 * a + 0.45 * lum * xp.array([1.08, 0.93, 0.72], xp.float32)
    elif look == "teal": out = 0.62 * a + 0.38 * lum * xp.array([0.70, 1.06, 0.94], xp.float32)
    else: out = lum * xp.array([0.97, 1.0, 1.04], xp.float32)
    return a * (1 - k) + out * k

def up(a): return resize_img(xp.clip(a, 0, 255), H, W)

# ---------------- fundo: névoa, poeira de luz e vazamento de luz quente ----------------
def dust_layer(t):
    im = Image.new("RGB", (640, 360), (0, 0, 0)); d = ImageDraw.Draw(im)
    for x, y, s, ph in S.dust:
        yy = (y * 360 - t * (4 + 14 * s)) % 360; xx = (x * 640 + 18 * math.sin(t * 0.4 + ph * 9)) % 640
        r = 1.5 + 5 * s; al = int(55 + 90 * s * (0.5 + 0.5 * math.sin(t * 0.8 + ph * 7)))
        d.ellipse([xx - r, yy - r, xx + r, yy + r], fill=(al, int(al * 0.9), int(al * 0.75)))
    return pil_arr(im.filter(ImageFilter.GaussianBlur(1.6)).resize((1280, 720), Image.BILINEAR))

def base_color(i, t):
    sh = S.shots[i]; cur = np.array(BASE.get(sh["s"]["phrases"][0]["look"], (22, 22, 22)), np.float32)
    if i == 0: return cur
    prev = np.array(BASE.get(S.shots[i - 1]["s"]["phrases"][0]["look"], (22, 22, 22)), np.float32)
    return prev + (cur - prev) * ease((t - sh["start"]) / 1.6)

def text_bg(t, i):
    base = base_color(i, t); bt = [float(x) for x in base]
    a = core.gradient(tuple(x * 1.25 for x in bt), tuple(x * 0.3 for x in bt))
    a += (core.fog(t, i % 9, 8)[..., None] * 0.8 + core.fog(t * 1.4, (i + 3) % 9, 12, 1)[..., None] * 0.35) * xp.asarray(base) * 1.3
    a += dust_layer(t) * 0.55
    return a

def light_leak(t):
    cx = 320 * (0.5 + 0.45 * math.sin(t * 0.11)); cy = 180 * (0.25 + 0.1 * math.sin(t * 0.17))
    g = xp.exp(-(((S.lx_ - cx) / 130.0) ** 2 + ((S.ly_ - cy) / 75.0) ** 2)).astype(xp.float32)
    return resize_img(g, 720, 1280)[..., None] * xp.array([34, 16, 6], xp.float32)

# ---------------- tipografia ----------------
def wrap(words, f, maxw):
    lines, cur = [], []
    for w in words:
        if cur and f.getlength(" ".join(cur + [w])) > maxw: lines.append(cur); cur = [w]
        else: cur.append(w)
    if cur: lines.append(cur)
    return lines

def draw_words(layer, glow, phrase, t, mode):
    d = ImageDraw.Draw(layer); g = ImageDraw.Draw(glow)
    words = phrase["text"].split(" "); ts = phrase["words"]
    if len(ts) != len(words):
        ts = [phrase["start"] + (phrase["end"] - phrase["start"]) * i / max(1, len(words)) for i in range(len(words))]
    if mode == "cap": sizes, maxw, fp, yc, lh, stroke = [68, 62, 56], 1560, "FreeSerifBoldItalic.ttf", H * 0.82, 84, 6
    else: sizes, maxw, fp, yc, lh, stroke = [100, 92, 84, 76, 68], 1440, "FreeSerifBold.ttf", H * 0.5, None, 0
    for sz in sizes:
        f = font(fp, sz); lines = wrap(words, f, maxw)
        if (mode == "cap" and len(lines) <= 2) or (mode == "big" and len(lines) <= 5): break
    lh = lh or int(sz * 1.34)
    y0 = yc - len(lines) * lh / 2; gi = 0
    for ln in lines:
        x = (W - f.getlength(" ".join(ln))) / 2; y = y0
        for w in ln:
            tw = ts[gi]; a = ease((t - tw) / 0.32)
            if a > 0:
                nxt = ts[gi + 1] if gi + 1 < len(ts) else phrase["end"]
                cur = tw <= t < nxt; em = is_emph(w); dy = 16 * (1 - a)
                col = ACCENT if em else ((255, 246, 226) if cur else IVORY)
                if mode == "cap": d.text((x, y + dy), w, font=f, fill=col + (int(255 * a),), stroke_width=stroke, stroke_fill=(0, 0, 0, int(230 * a)))
                else: d.text((x, y + dy), w, font=f, fill=col + (int(255 * a),))
                if cur or em: g.text((x, y + dy), w, font=f, fill=(ACCENT if em else GOLD) + (int(200 * a * (1 if cur else 0.55)),))
            x += f.getlength(w + " "); gi += 1
        y0 += lh
    return y0 - len(lines) * lh

def rule(layer, cx, y, half, a, col=GOLD):
    d = ImageDraw.Draw(layer)
    d.line([cx - half, y, cx + half, y], fill=col + (int(200 * a),), width=2)
    d.ellipse([cx - 4, y - 4, cx + 4, y + 4], fill=col + (int(220 * a),))

def intro_title(layer, glow, t, a):
    d = ImageDraw.Draw(layer)
    kick = S.cfg["kicker"]
    if kick: d.text((W / 2, H * 0.26), "   ".join(" ".join(w) for w in kick.split()), font=font("FreeMonoBold.ttf", 34), fill=GOLD + (int(220 * a),), anchor="mm")
    rule(layer, W / 2, H * 0.30, 160 * ease(a), a)
    for n, line in enumerate(S.cfg["title"]):
        f = font("FreeSerifBoldItalic.ttf", 104 if n == 0 else 88); x = (W - f.getlength(line)) / 2
        for w in line.split(" "):
            c = ACCENT if is_emph(w) else IVORY
            d.text((x, H * 0.38 + n * 128), w, font=f, fill=c + (int(255 * a),))
            if is_emph(w): ImageDraw.Draw(glow).text((x, H * 0.38 + n * 128), w, font=f, fill=ACCENT + (int(220 * a),))
            x += f.getlength(w + " ")

def part_card(layer, glow, text, t, a):
    d = ImageDraw.Draw(layer); f = font("FreeSerifBoldItalic.ttf", 170)
    d.text((W / 2, H * 0.44), text, font=f, fill=IVORY + (int(255 * a),), anchor="mm")
    ImageDraw.Draw(glow).text((W / 2, H * 0.44), text, font=f, fill=GOLD + (int(150 * a),), anchor="mm")
    rule(layer, W / 2, H * 0.58, 220 * ease(a), a)

def overlay(t, i):
    sh = S.shots[i]; phrases = sh["s"]["phrases"]; cutscene = sh["s"]["id"] in S.cut
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ia = S.A["intro_title"]
    if i == 0 and S.cfg["title"] and ia[0] <= t <= ia[1]:
        intro_title(layer, glow, t, min(1.0, (t - ia[0]) / 0.6, (ia[1] - t) / 0.6))
    else:
        for k, p in enumerate(phrases):
            nxt = phrases[k + 1]["start"] if k + 1 < len(phrases) else (S.shots[i + 1]["s"]["phrases"][0]["start"] if i + 1 < len(S.shots) else 1e9)
            t0, t1 = p["start"] - 0.05, min(p["end"] + 0.7, nxt - 0.1)
            if not (t0 <= t <= t1) or not p["text"]: continue
            a = min(1.0, (t - t0) / 0.12, (t1 - t) / 0.4)
            if p["title"]: part_card(layer, glow, p["text"].capitalize() if p["text"].isupper() else p["text"], t, a)
            else:
                top = draw_words(layer, glow, p, t, "cap" if cutscene else "big")
                if not cutscene: rule(layer, W / 2, top - 34, 90 * ease((t - p["start"]) / 0.6), 1.0)
            if a < 1:
                layer.putalpha(layer.getchannel("A").point(lambda v: int(v * max(0, a)))); glow.putalpha(glow.getchannel("A").point(lambda v: int(v * max(0, a))))
            break
    bb = layer.getchannel("A").getbbox()
    if bb is None: return None
    box = (max(0, bb[0] - 90), max(0, bb[1] - 90), min(W, bb[2] + 90), min(H, bb[3] + 90))
    g = glow.crop(box); gw, gh = g.size
    g = g.resize((max(1, gw // 4), max(1, gh // 4)), Image.BILINEAR).filter(ImageFilter.GaussianBlur(3.5)).resize((gw, gh), Image.BILINEAR)
    return box, pil_arr(layer.crop(box)), pil_arr(g)

def end_card(t, sh):
    p = sh["s"]["phrases"][0]; cfg = S.cfg
    img = Image.new("RGB", (W, H), (6, 6, 6)); d = ImageDraw.Draw(img, "RGBA")
    k = int(t * 4.2); r = (k * 2654435761) % 1000 / 1000
    on = (0.55 if r < 0.12 else 1.0) if t > p["start"] - 0.1 else 0
    if on > 0:
        col = (int(230 * on), int(25 * on), int(25 * on))
        glow = Image.new("RGB", (W, H)); ImageDraw.Draw(glow).text((W / 2, 400), "TEMOS VAGAS", font=font("DejaVuSerif-Bold.ttf", 190), fill=col, anchor="mm")
        gl = np.asarray(glow.filter(ImageFilter.GaussianBlur(24))).astype(np.float32)
        img = Image.fromarray(np.clip(np.asarray(img).astype(np.float32) + gl * 1.3 + np.asarray(glow).astype(np.float32) * 0.9, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(img, "RGBA")
    if t > p["end"] + 0.4:
        a = min(1, (t - p["end"] - 0.4) / 0.6)
        d.text((W / 2, 640), cfg["end_question"], font=font("FreeSerifItalic.ttf", 64), fill=(230, 225, 215, int(255 * a)), anchor="mm")
        d.text((W / 2, 740), cfg["end_note"], font=font("FreeSans.ttf", 42), fill=(200, 190, 170, int(255 * a)), anchor="mm")
        d.text((W / 2, 830), cfg["channel"], font=font("FreeMonoBold.ttf", 52), fill=(200, 30, 30, int(255 * a)), anchor="mm")
    return pil_arr(img)

# ---------------- quadro ----------------
def frame(t):
    if S.style == "ps2": return frame_ps2(t)
    i = max(0, bisect.bisect_right(S.starts, t) - 1)
    sh = S.shots[i]; sid = sh["s"]["id"]; lt = t - sh["start"]; look = sh["s"]["phrases"][0]["look"]
    if sid == S.cfg["end_scene"]:
        f = end_card(t, sh)
    else:
        if sid in S.cut:                                                  # tudo em 720p…
            C, name = ctx_for(i, t)
            f = grade(CUTSCENES[name](C), look, 0.35) * S.VIGBAND
            k = min(1.0, lt / 0.6)
            if k < 1: f = f * k + text_bg(t, i) * 0.6 * (1 - k)
        else:
            f = text_bg(t, i) * S.VIG
        ia = S.A["intro_title"]
        if i == 0 and t < ia[1] + 0.6: f = f * (0.45 + 0.55 * ease((t - ia[1]) / 0.6))
        f += light_leak(t)
        f *= 1 + 0.03 * math.sin(t * 47) + 0.02 * math.sin(t * 13.1)
        f = up(f)                                                          # …e sobe para 1080p uma vez
        ov = overlay(t, i)
        if ov is not None:
            (x0, y0, x1, y1), ly, gl = ov
            reg = f[y0:y1, x0:x1]; reg += gl[..., :3] * (gl[..., 3:4] / 255.0) * 0.9
            a = ly[..., 3:4] / 255.0
            f[y0:y1, x0:x1] = reg * (1 - a) + ly[..., :3] * a
    for k_ in S.A["knocks"]:
        if 0 <= t - k_ < 0.2: f = xp.roll(f, int(14 * (1 - (t - k_) / 0.2) * (1 if int(t * 90) % 2 else -1)), axis=1)
    f *= S.FRAME; f += S.FRAME_I; f += S.GRAIN[int(t * FPS) % 6]
    bar = int(BAR * ease(t / 1.2))
    if bar: f[:bar] = 0; f[H - bar:] = 0
    if t < 0.8: f *= t / 0.8
    if t > S.TOTAL - 1.5: f *= max(0, (S.TOTAL - t) / 1.5)
    return to_cpu(xp.clip(f, 0, 255).astype(xp.uint8))

def encoder_args(enc):
    if enc == "nvenc":
        return ["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "27", "-b:v", "0", "-maxrate", "4M", "-bufsize", "8M", "-pix_fmt", "yuv420p"]
    return ["-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-maxrate", "4M", "-bufsize", "8M", "-pix_fmt", "yuv420p"]

def _init(ep_path): setup(ep_path)

def render_chunk(args):
    c, enc = args
    n = math.ceil(S.TOTAL * FPS / NCH)
    f0, f1 = c * n, min(round(S.TOTAL * FPS), (c + 1) * n)
    tmp = S.OUT / f"chunk_{c:02d}.tmp.mp4"
    pr = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
                           "-i", "-", *encoder_args(enc), "-g", "60", str(tmp)], stdin=subprocess.PIPE)
    for fi in range(f0, f1): pr.stdin.write(frame(fi / FPS).tobytes())
    pr.stdin.close(); ok = pr.wait() == 0
    if ok: os.replace(tmp, S.OUT / f"chunk_{c:02d}.mp4")
    return c, f1 - f0, ok

def render_all(ep_path, enc="x264", jobs=None):
    setup(ep_path)
    for f in S.OUT.glob("chunk_*.mp4"): f.unlink()
    t0 = time.time()
    with Pool(jobs or (4 if GPU else os.cpu_count() or 4), initializer=_init, initargs=(str(ep_path),)) as pool:
        for c, n, ok in pool.imap_unordered(render_chunk, [(c, enc) for c in range(NCH)]):
            print("ok" if ok else "FALHOU", f"bloco {c + 1}/{NCH}", f"{time.time() - t0:.0f}s", flush=True)
            if not ok: raise SystemExit("falha ao codificar um bloco")

def tstart(spec):
    """'12.5' = segundos; 's05:8' = 8 s depois do início da cena s05."""
    if ":" in spec or not spec.replace(".", "").isdigit():
        sid, _, off = spec.partition(":")
        for sh in S.shots:
            if sh["s"]["id"] == sid: return sh["start"] + float(off or 1.0)
        raise SystemExit(f"cena {sid} não existe")
    return float(spec)

def preview(ep_path, specs):
    setup(ep_path); d = S.ep.build / "prev"; d.mkdir(exist_ok=True); names = []
    for sp in specs:
        n = sp.replace(":", "_"); Image.fromarray(frame(tstart(sp))).save(d / f"prev_{n}.png"); names.append(n)
    # folha de contato (2 colunas) para ver vários quadros de uma vez
    cols = 2; rows = (len(names) + 1) // 2; sheet = Image.new("RGB", (cols * 800, rows * 450))
    for i, n in enumerate(names): sheet.paste(Image.open(d / f"prev_{n}.png").resize((800, 450)), ((i % cols) * 800, (i // cols) * 450))
    sheet.save(d / "sheet.png"); print("prévias em", d)

if __name__ == "__main__":
    ep_path, cmd, *rest = sys.argv[1:]
    if cmd == "preview": preview(ep_path, rest)
    else: render_all(ep_path, os.environ.get("ENC", "x264"))
