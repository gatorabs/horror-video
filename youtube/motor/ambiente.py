"""Verificações do ambiente (Claude Code, chave do ElevenLabs, ffmpeg, bibliotecas). Usado pela interface e pelo gerar.py."""
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

ARQ_CHAVE = os.path.expanduser("~/.elevenlabs_key")
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ---------- Claude Code ----------
def achar_claude():
    """Caminho do executável do Claude Code, ou None."""
    exe = shutil.which("claude")
    if exe:
        return exe
    home = os.path.expanduser("~")
    candidatos = [os.path.join(home, ".local", "bin", "claude.exe"), os.path.join(home, ".local", "bin", "claude"),
                  os.path.join(os.environ.get("APPDATA", ""), "npm", "claude.cmd"), "/usr/local/bin/claude", "/opt/homebrew/bin/claude"]
    return next((c for c in candidatos if c and os.path.exists(c)), None)


def claude_estado():
    """(instalado, logado, texto) — texto é a versão ou o motivo."""
    exe = achar_claude()
    if not exe:
        return False, False, "não instalado"
    try:
        v = subprocess.run([exe, "--version"], capture_output=True, timeout=60, creationflags=NO_WINDOW)
        versao = v.stdout.decode(errors="ignore").strip().split(" ")[0] or "?"
    except Exception:
        versao = "?"
    try:
        r = subprocess.run([exe, "auth", "status"], capture_output=True, timeout=90, creationflags=NO_WINDOW)
        dados = json.loads(r.stdout.decode(errors="ignore") or "{}")
        if dados.get("loggedIn"):
            return True, True, f"{versao} · logado ({dados.get('authMethod', 'conta')})"
        return True, False, f"{versao} · falta entrar na conta"
    except Exception:
        return True, False, f"{versao} · não consegui ver o login"


# ---------- ElevenLabs ----------
def chave_eleven():
    k = os.environ.get("ELEVENLABS_API_KEY", "").strip()
    if k:
        return k
    if os.path.exists(ARQ_CHAVE):
        k = open(ARQ_CHAVE, encoding="utf-8", errors="ignore").read().strip()
        if k:
            return k
    if os.name == "nt":  # quem usa WSL costuma ter a chave lá
        try:
            r = subprocess.run(["wsl", "-d", "Ubuntu", "-e", "bash", "-c", "cat ~/.elevenlabs_key 2>/dev/null"],
                               capture_output=True, timeout=30, creationflags=NO_WINDOW)
            k = r.stdout.decode(errors="ignore").strip()
            if k and " " not in k:
                return k
        except Exception:
            pass
    return None


def mascarar(k):
    return "••••" + k[-4:] if k and len(k) > 4 else "••••"


def validar_eleven(k):
    """(ok, texto). ok=None quando a chave existe mas não deu para conferir (sem rede, permissões restritas...)."""
    req = urllib.request.Request("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": k})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
        usado, limite = d.get("character_count"), d.get("character_limit")
        if usado is not None and limite:
            return True, f"{mascarar(k)} · {max(0, limite - usado):,} de {limite:,} caracteres restantes".replace(",", ".")
        return True, f"{mascarar(k)} · válida"
    except urllib.error.HTTPError as e:
        corpo = e.read().decode(errors="ignore")
        if e.code == 401 and "missing_permissions" in corpo:
            return None, f"{mascarar(k)} · salva (a chave não permite ver o saldo)"
        if e.code == 401:
            return False, f"{mascarar(k)} · a ElevenLabs recusou esta chave"
        return None, f"{mascarar(k)} · salva (erro {e.code} ao conferir)"
    except Exception:
        return None, f"{mascarar(k)} · salva (sem conexão para conferir)"


def salvar_chave_eleven(k):
    k = k.strip()
    with open(ARQ_CHAVE, "w", encoding="utf-8") as f:
        f.write(k)
    try:
        os.chmod(ARQ_CHAVE, 0o600)
    except OSError:
        pass
    return ARQ_CHAVE


# ---------- ffmpeg e bibliotecas ----------
def tem_ffmpeg():
    return shutil.which("ffmpeg") is not None


def libs_faltando():
    falta = []
    for modulo, pacote in (("numpy", "numpy"), ("PIL", "pillow")):
        r = subprocess.run([sys.executable, "-c", f"import {modulo}"], capture_output=True, creationflags=NO_WINDOW)
        if r.returncode:
            falta.append(pacote)
    return falta
