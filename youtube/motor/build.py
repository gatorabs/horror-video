"""Gera o vídeo de um episódio.

    python youtube/motor/build.py youtube/episodios/01-lorde-palido            # tudo
    python youtube/motor/build.py youtube/episodios/01-lorde-palido --quadros  # só amostra de quadros, sem voz (grátis)
    python youtube/motor/build.py youtube/episodios/01-lorde-palido --ate 4    # só os 4 primeiros parágrafos (teste barato)
Opções: --cpu (sem NVENC)
"""
import argparse
import os
import subprocess
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fundos
import render
import roteiro
import tts

FPS = 30
ABERTURA_S = 2.2  # silêncio com o primeiro painel surgindo em fade, antes da voz
PAUSA_PRE = 0.25
PAUSA = 0.85
PAUSA_CENA = 1.9
CAUDA_S = 3.5


def ffmpeg(*args, cwd=None):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], cwd=cwd)
    if r.returncode:
        raise SystemExit("ffmpeg falhou")


def tem_nvenc():
    """True se este computador consegue codificar com NVENC (placa NVIDIA); senão o build usa a CPU."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.2", "-c:v", "h264_nvenc",
                        "-f", "null", "-"], capture_output=True)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pasta")
    ap.add_argument("--quadros", action="store_true")
    ap.add_argument("--ate", type=int, default=0)
    ap.add_argument("--cpu", action="store_true")
    a = ap.parse_args()

    pasta = os.path.abspath(a.pasta)
    slug = os.path.basename(pasta)
    build = os.path.join(pasta, "build")
    os.makedirs(build, exist_ok=True)
    meta, unidades = roteiro.carregar(pasta)
    if a.ate:
        unidades = unidades[:a.ate]
    print(f"{meta['titulo']}: {len(unidades)} parágrafos, {sum(len(u['texto']) for u in unidades)} caracteres")

    # fundos (um png por fundo distinto)
    pasta_fundos = os.path.join(pasta, "fundos")
    imgs = {}
    for u in unidades:
        if u["fundo"] not in imgs:
            imgs[u["fundo"]] = fundos.preparar(u["fundo"], pasta_fundos, os.path.join(build, f"fundo_{u['fundo'][0]}.png"))

    paginas, por_unidade, quebras = render.paginar(unidades)

    if a.quadros:
        qd = os.path.join(build, "quadros")
        os.makedirs(qd, exist_ok=True)
        passo = max(1, len(unidades) // 6)
        for i in range(0, len(unidades), passo):
            bg = os.path.join(build, f"fundo_{unidades[i]['fundo'][0]}.png")
            from PIL import Image
            comp = Image.open(bg).convert("RGBA")
            comp.alpha_composite(render.quadro_pagina(paginas[por_unidade[i]], i, quebras))
            comp.convert("RGB").save(os.path.join(qd, f"p{i:03d}.jpg"), quality=90)
        print("amostras em", qd, f"({len(paginas)} páginas no total)")
        return

    # 1) voz
    print("narração...")
    wavs = tts.gerar_todos(unidades, os.path.join(build, "voz"), meta.get("voz", tts.VOZ_PADRAO))
    durs = [tts.duracao(w) for w in wavs]

    # 2) linha do tempo + trilha de narração
    t = ABERTURA_S
    linha = []  # (inicio, duracao, indice)
    quadros = []
    sil = lambda s: b"\x00\x00" * round(24000 * s)
    audio = bytearray(sil(ABERTURA_S))
    for i, d in enumerate(durs):
        fim_cena = i + 1 == len(unidades) or unidades[i + 1]["novo_fundo"]
        total = PAUSA_PRE + d + (PAUSA_CENA if fim_cena else PAUSA)
        if i + 1 == len(unidades):
            total += CAUDA_S
        with wave.open(wavs[i]) as w:
            audio += sil(PAUSA_PRE) + w.readframes(w.getnframes()) + sil(total - PAUSA_PRE - d)
        quadros.append((i, 0.0 if i == 0 else t, total + (ABERTURA_S if i == 0 else 0)))
        linha.append((t, total, i))
        t += total
    dur_total = t
    with wave.open(os.path.join(build, "narracao.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(bytes(audio))
    print(f"duração: {int(dur_total // 60)}min{int(dur_total % 60):02d}s")

    # 3) quadros do painel
    pq = os.path.join(build, "painel")
    os.makedirs(pq, exist_ok=True)
    lista = []
    for ident, ini, dur in quadros:
        fn = f"u{ident:03d}.png"
        render.quadro_pagina(paginas[por_unidade[ident]], ident, quebras).save(os.path.join(pq, fn))
        lista.append((fn, dur))
    with open(os.path.join(pq, "lista.txt"), "w") as f:
        for fn, dur in lista:
            f.write(f"file '{fn}'\nduration {dur:.3f}\n")
        f.write(f"file '{lista[-1][0]}'\n")

    # 4) fundo em movimento (zoom lento + fade), um trecho por fundo
    segmentos = []  # (fundo, duracao)
    ini_seg, atual = 0.0, unidades[0]["fundo"]
    for ti, td, i in linha:
        if i and unidades[i]["novo_fundo"]:
            segmentos.append((atual, ti - ini_seg))
            ini_seg, atual = ti, unidades[i]["fundo"]
    segmentos.append((atual, dur_total - ini_seg))
    vcodec = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18"]
    arqs = []
    for n, (f, d) in enumerate(segmentos):
        out = f"seg{n:02d}.mp4"
        frames = max(1, round(d * FPS))
        z = f"1+0.06*on/{frames}" if n % 2 == 0 else f"1.06-0.06*on/{frames}"
        filtro = (f"scale=2880:1620,zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1920x1080:fps={FPS},"
                  f"fade=t=in:st=0:d=1.4,fade=t=out:st={max(0, d - 1.4):.2f}:d=1.4,format=yuv420p")
        print(f"fundo {n + 1}/{len(segmentos)} ({d:.0f}s)")
        ffmpeg("-loop", 1, "-framerate", FPS, "-t", f"{d:.3f}", "-i", imgs[f], "-vf", filtro, *vcodec, out, cwd=build)
        arqs.append(out)
    with open(os.path.join(build, "fundos.txt"), "w") as f:
        for x in arqs:
            f.write(f"file '{x}'\n")
    ffmpeg("-f", "concat", "-safe", 0, "-i", "fundos.txt", "-c", "copy", "fundo.mp4", cwd=build)

    # 5) montagem final: fundo + granulação leve + painel + narração + drone de ambiente
    saida = os.path.join(pasta, f"{slug}.mp4")
    usar_gpu = not a.cpu and tem_nvenc()
    print("encoder:", "GPU (NVENC)" if usar_gpu else "CPU (libx264)")
    venc = (["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "27", "-b:v", "5M", "-maxrate", "8M", "-bufsize", "16M"]
            if usar_gpu else ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-maxrate", "8M", "-bufsize", "16M"])
    fim_fade = max(0, dur_total - 3)
    fc = (f"[0:v]noise=alls=4:allf=t[b];[1:v]fps={FPS},format=rgba,fade=t=in:st=0.4:d=1.6:alpha=1[p];[b][p]overlay=format=auto:shortest=1,format=yuv420p[v];"
          f"[2:a]loudnorm=I=-16:TP=-1.5:LRA=11[voz];"
          f"[3:a]lowpass=f=160,highpass=f=30,tremolo=f=0.1:d=0.6,volume=0.07[amb];"
          f"[voz][amb]amix=inputs=2:duration=first:normalize=0,afade=t=in:d=2,afade=t=out:st={fim_fade:.2f}:d=3[a]")
    ffmpeg("-i", "fundo.mp4", "-f", "concat", "-safe", 0, "-i", "painel/lista.txt", "-i", "narracao.wav",
           "-f", "lavfi", "-t", f"{dur_total:.2f}", "-i", "anoisesrc=color=brown:amplitude=0.5:sample_rate=48000",
           "-filter_complex", fc, "-map", "[v]", "-map", "[a]", *venc, "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
           "-t", f"{dur_total:.2f}", "-movflags", "+faststart", saida, cwd=build)

    fundos_capa = imgs[unidades[min(len(unidades) - 1, 3)]["fundo"]]
    render.capa(fundos_capa, meta["titulo"], meta["subtitulo"], os.path.join(pasta, "capa.jpg"))
    print("OK ->", saida)


if __name__ == "__main__":
    main()
