"""Base do motor de vídeo: backend de pixels (GPU/CPU), helpers de imagem e fontes.

O desenho de formas e texto usa o PIL (CPU). Toda conta de pixel (fundo, névoa, brilho, zoom, composição) usa `xp`:
CuPy na placa de vídeo quando disponível (GPU=1 força, GPU=0 desliga, sem variável detecta sozinho) ou numpy na CPU.
As cutscenes são compostas em 1280x720 e o render sobe para 1920x1080 uma única vez."""
import math, os
from pathlib import Path
import numpy as onp
from PIL import Image, ImageDraw, ImageFilter, ImageFont

def _detect_gpu():
    want = os.environ.get("GPU")
    if want == "0": return False
    try:
        import cupy
        return cupy.cuda.runtime.getDeviceCount() > 0
    except Exception:
        if want == "1": raise
        return False

GPU = _detect_gpu()
if GPU:
    import cupy as xp
    import cupyx.scipy.ndimage as _ndi
else:
    xp = onp
    _ndi = None

def to_cpu(a): return a.get() if GPU else a

# ------------------------------------------------------------------ fontes
FONT_DIR = Path(__file__).parent / "fonts"            # copiadas de /usr/share/fonts (não vão para o git)
_SYS = ["/usr/share/fonts/truetype/freefont/", "/usr/share/fonts/truetype/dejavu/"]
_FC = {}
def font(name, size):
    """Carrega uma fonte por nome de arquivo (ex.: 'FreeSerifBold.ttf'), de engine/fonts ou do sistema."""
    if (name, size) not in _FC:
        for base in [str(FONT_DIR) + os.sep] + _SYS:
            if os.path.exists(base + name): _FC[(name, size)] = ImageFont.truetype(base + name, size); break
        else: raise FileNotFoundError(f"fonte {name} não encontrada (copie para engine/fonts)")
    return _FC[(name, size)]
def F(size, mono=False): return font("FreeMonoBold.ttf" if mono else "FreeSansBold.ttf", size)

# ------------------------------------------------------------------ matemática
def ease(x): x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)
def lerp(a, b, x): return a + (b - a) * x
def pingpong(x, m): return m - abs((x % (2 * m)) - m)

# ------------------------------------------------------------------ imagem (xp)
W0, H0 = 1280, 720

def resize_img(a, h, w, box=None):
    """Redimensiona (bilinear) um array (h,w[,c]) float; box=(l,t,r,b) recorta na origem."""
    ih, iw = a.shape[:2]
    l, t, r, b = box if box else (0, 0, iw, ih)
    ys = xp.clip((xp.arange(h, dtype=xp.float32) + 0.5) * ((b - t) / h) + t - 0.5, 0, ih - 1)
    xs = xp.clip((xp.arange(w, dtype=xp.float32) + 0.5) * ((r - l) / w) + l - 0.5, 0, iw - 1)
    y0 = xp.floor(ys).astype(xp.int32); x0 = xp.floor(xs).astype(xp.int32)
    y1 = xp.minimum(y0 + 1, ih - 1); x1 = xp.minimum(x0 + 1, iw - 1)
    wy = (ys - y0).astype(xp.float32); wx = (xs - x0).astype(xp.float32)
    if a.ndim == 3: wy = wy[:, None, None]; wx = wx[None, :, None]
    else: wy = wy[:, None]; wx = wx[None, :]
    ra, rb = a[y0], a[y1]
    top = ra[:, x0] * (1 - wx) + ra[:, x1] * wx
    bot = rb[:, x0] * (1 - wx) + rb[:, x1] * wx
    return top * (1 - wy) + bot * wy

def blur_img(a, sigma):
    """Desfoque gaussiano espacial de um array (h,w[,c])."""
    if GPU:
        return _ndi.gaussian_filter(a, sigma=(sigma, sigma, 0) if a.ndim == 3 else sigma, mode="nearest")
    r = max(1, int(3 * sigma)); k = onp.exp(-(onp.arange(-r, r + 1) ** 2) / (2 * sigma * sigma)); k = (k / k.sum()).astype(onp.float32)
    out = a
    for ax in (0, 1):
        pad = [(0, 0)] * a.ndim; pad[ax] = (r, r); p = onp.pad(out, pad, mode="edge")
        acc = 0
        for i, kv in enumerate(k):
            sl = [slice(None)] * a.ndim; sl[ax] = slice(i, i + a.shape[ax]); acc = acc + kv * p[tuple(sl)]
        out = acc
    return out

def _noise(h, w, sg, seed):
    r = onp.random.default_rng(seed).random((h, w)).astype(onp.float32)
    a = onp.asarray(Image.fromarray((r * 255).astype(onp.uint8)).filter(ImageFilter.GaussianBlur(sg))).astype(onp.float32)
    return xp.asarray((a - a.min()) / (a.max() - a.min() + 1e-6))

NZ = [_noise(540, 960, 20, 1), _noise(540, 960, 7, 2)]
YY, XX = xp.mgrid[0:H0, 0:W0]
VIG = (1 - 0.65 * xp.clip((((XX - W0 / 2) / (W0 * 0.7)) ** 2 + ((YY - H0 / 2) / (H0 * 0.75)) ** 2), 0, 1)).astype(xp.float32)[..., None]

def fog(t, seed=0, speed=14, layer=0):
    """Névoa em movimento (0..1), 720p."""
    n = NZ[layer]
    ox = int(pingpong(t * speed + seed * 91, 320)); oy = int(pingpong(t * speed * 0.4 + seed * 47, 180))
    return resize_img(n[oy:oy + 360, ox:ox + 640], H0, W0)

def gradient(top, bot):
    y = xp.linspace(0, 1, H0, dtype=xp.float32)[:, None, None]
    return xp.array(top, xp.float32) * (1 - y) + xp.array(bot, xp.float32) * y + xp.zeros((H0, W0, 3), xp.float32)

def canvas(c=(0, 0, 0)):
    im = Image.new("RGB", (W0, H0), c); return im, ImageDraw.Draw(im)

def arr(im): return xp.asarray(onp.asarray(im)).astype(xp.float32)

def bloom(a, thr=140, k=0.9, r=14):
    b = xp.clip(a - thr, 0, 255)
    small = b.reshape(H0 // 4, 4, W0 // 4, 4, 3).mean(axis=(1, 3))
    return a + resize_img(blur_img(small, r / 4), H0, W0) * k

def zoom(a, k, cx=0.5, cy=0.5):
    vw, vh = W0 / k, H0 / k
    l = min(max(cx * W0 - vw / 2, 0), W0 - vw); t = min(max(cy * H0 - vh / 2, 0), H0 - vh)
    return resize_img(a, H0, W0, box=(l, t, l + vw, t + vh))

def finish(a, vig=1.0):
    return xp.clip(a * (1 - vig + vig * VIG), 0, 255)

# ------------------------------------------------------------------ contexto de uma cutscene
class Ctx:
    """t = tempo desde o início da cena; d = duração; ph = frases [{start,end,words}] (tempos relativos à cena);
    params = parâmetros da cutscene dados no script do episódio."""
    def __init__(s, t, d, ph, params=None): s.t, s.d, s.ph, s.params = t, d, ph, params or {}
    def w(s, k, i):
        ws = s.ph[min(k, len(s.ph) - 1)]["words"]; return ws[min(i, len(ws) - 1)]
    def p(s, k): return s.ph[min(k, len(s.ph) - 1)]["start"]
    def prm(s, name, default): return s.params.get(name, default)
    def when(s, v):
        """Âncora de tempo: (k, i) = palavra i da frase k; (k,) = início da frase k; número = segundos na cena."""
        if isinstance(v, (int, float)): return float(v)
        return s.p(v[0]) if len(v) == 1 else s.w(v[0], v[1])
    def at(s, name, default): return s.when(s.params.get(name, default))
