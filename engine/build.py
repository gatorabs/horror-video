"""Monta um episódio de ponta a ponta.   python -m engine.build episodios/NN-nome [opções]

Etapas (--steps, padrão tts,mix,render,mux):
  tts     narração no ElevenLabs (cache; chave em ~/.elevenlabs_key)         -> roda no WSL se não houver sox
  mix     voz + trilha + efeitos -> build/mix.wav e build/timeline.json     -> idem (precisa de sox)
  render  quadros na GPU (CuPy) ou CPU, codificados em 14 blocos            -> build/chunks/
  mux     junta os blocos e a narração normalizada                          -> episodios/NN-nome/NN-nome.mp4
Opções: --cpu (não usar a GPU), --enc x264|nvenc|auto, --jobs N, --steps a,b"""
import argparse, glob, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def wsl_path(p):
    p = Path(p).resolve(); drive = p.drive[0].lower()
    return f"/mnt/{drive}/" + str(p)[3:].replace("\\", "/")

def run_audio(module, ep_dir):
    """tts/mix precisam de sox: roda aqui se existir, senão dentro do WSL."""
    if shutil.which("sox") or os.name != "nt":
        cmd = [sys.executable, "-m", f"engine.{module}", str(ep_dir)]
    else:
        cmd = ["wsl", "bash", "-lc", f"cd {wsl_path(ROOT)} && python3 -m engine.{module} {wsl_path(ep_dir)}"]
    subprocess.run(cmd, cwd=ROOT, check=True)

def pick_encoder(choice, cpu):
    if choice != "auto": return choice
    if cpu: return "x264"
    out = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
    return "nvenc" if "h264_nvenc" in out else "x264"

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episodio"); ap.add_argument("--steps", default="tts,mix,render,mux")
    ap.add_argument("--cpu", action="store_true"); ap.add_argument("--enc", default="auto", choices=["auto", "x264", "nvenc"])
    ap.add_argument("--jobs", type=int)
    a = ap.parse_args()
    ep = Path(a.episodio).resolve(); steps = a.steps.split(","); t0 = time.time()
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    if a.cpu: env["GPU"] = "0"
    if a.jobs: env["JOBS"] = str(a.jobs)
    if "tts" in steps: run_audio("tts", ep)
    if "mix" in steps: run_audio("mix", ep)
    build = ep / "build"
    if "render" in steps:
        enc = pick_encoder(a.enc, a.cpu); print("render:", "GPU" if env.get("GPU") != "0" else "CPU", "| encoder", enc)
        subprocess.run([sys.executable, "-m", "engine.render", str(ep), "all"], cwd=ROOT, check=True, env=dict(env, ENC=enc))
    if "mux" in steps:
        chunks = sorted(glob.glob(str(build / "chunks" / "chunk_??.mp4")))
        if not chunks: raise SystemExit("nenhum bloco encontrado: rode a etapa render")
        lst = build / "chunks" / "list.txt"; lst.write_text("".join(f"file '{os.path.basename(c)}'\n" for c in chunks))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(build / "video.mp4")], check=True)
        out = ep / f"{ep.name}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(build / "video.mp4"), "-i", str(build / "mix.wav"), "-map", "0:v", "-map", "1:a",
                        "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", "-movflags", "+faststart", str(out)], check=True)
        print(f"OK -> {out}  ({out.stat().st_size / 1e6:.0f} MB, {time.time() - t0:.0f}s no total)")

if __name__ == "__main__":
    main()
