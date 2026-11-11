"""Link do 4chan -> vídeo pronto.

    python youtube/motor/gerar.py https://boards.4chan.org/x/thread/43186732/...            # tudo
    python youtube/motor/gerar.py <link> --sem-render                                        # só o roteiro (revise antes de gastar voz)
    python youtube/motor/gerar.py <link> --provedor api                                      # usa a API (ANTHROPIC_API_KEY) em vez do Claude Code
    python youtube/motor/gerar.py <link> --nome 02-meu-titulo --so-autor                     # nome da pasta; só os posts do autor

Etapas: baixa a thread (API pública do 4chan) -> o LLM adapta para roteiro narrado em PT-BR (roteiro.txt, prompts dos fundos, descrição)
-> build.py gera voz e vídeo. Para mudar o estilo do roteiro, edite PROMPT em youtube/motor/prompt_roteiro.md.
"""
import argparse
import html
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.request

import ambiente

AQUI = os.path.dirname(os.path.abspath(__file__))
EPISODIOS = os.path.join(os.path.dirname(AQUI), "episodios")
MODELO_API = "claude-sonnet-5-5"


# ---------- 1. baixar a thread ----------
def baixar_thread(url):
    m = re.search(r"boards\.4chan(?:nel)?\.org/(\w+)/thread/(\d+)", url)
    if not m:
        raise SystemExit("Link não reconhecido. Use um link de thread do 4chan (boards.4chan.org/<board>/thread/<id>).")
    board, tid = m.groups()
    req = urllib.request.Request(f"https://a.4cdn.org/{board}/thread/{tid}.json", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["posts"]


def _texto(com):
    com = re.sub(r"<br\s*/?>", "\n", com or "")
    com = re.sub(r"<a [^>]*class=\"quotelink\"[^>]*>.*?</a>", "", com)
    return html.unescape(re.sub(r"<[^>]+>", "", com)).strip()


def montar_fonte(posts, so_autor):
    op = posts[0]
    chave = lambda p: (p.get("name"), p.get("id"), p.get("trip"))
    saida, vistos = [], set()
    for p in posts:
        if so_autor and chave(p) != chave(op):
            continue
        t = _texto(p.get("com"))
        if t and t not in vistos:  # a thread às vezes repete posts
            vistos.add(t)
            saida.append(t)
    return op.get("sub", ""), "\n\n".join(saida)


# ---------- 2. LLM ----------
def chamar_llm(prompt, provedor):
    if provedor == "api":
        chave = os.environ.get("ANTHROPIC_API_KEY")
        if not chave:
            raise SystemExit("Defina ANTHROPIC_API_KEY para usar --provedor api.")
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps({"model": MODELO_API, "max_tokens": 16000,
                             "messages": [{"role": "user", "content": prompt}]}).encode(),
            headers={"x-api-key": chave, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=900) as r:
            return "".join(b.get("text", "") for b in json.load(r)["content"])
    # padrão: Claude Code em modo headless (usa o login que você já tem, sem chave)
    exe = ambiente.achar_claude()
    if not exe:
        raise SystemExit("Claude Code não encontrado. Abra a interface (youtube/abrir.bat) para instalar e entrar, "
                         "ou use --provedor api com ANTHROPIC_API_KEY.")
    r = subprocess.run([exe, "-p", "--output-format", "text"], input=prompt.encode("utf-8"), capture_output=True, timeout=1500)
    if r.returncode:
        raise SystemExit("claude -p falhou: " + r.stderr.decode(errors="ignore")[:500])
    return r.stdout.decode("utf-8", errors="ignore")


def separar(resposta):
    partes = {}
    for nome in ("ROTEIRO", "FUNDOS", "DESCRICAO"):
        m = re.search(rf"=====\s*{nome}\s*=====\s*\n(.*?)(?=\n=====\s*[A-Z]+\s*=====|\Z)", resposta, re.S)
        if m:
            partes[nome] = m.group(1).strip() + "\n"
    return partes


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "relato"


def proxima_pasta(titulo, nome):
    os.makedirs(EPISODIOS, exist_ok=True)
    if nome:
        return os.path.join(EPISODIOS, nome)
    nums = [int(d[:2]) for d in os.listdir(EPISODIOS) if d[:2].isdigit()]
    return os.path.join(EPISODIOS, f"{max(nums, default=0) + 1:02d}-{slug(titulo)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--provedor", choices=["claude", "api"], default="claude")
    ap.add_argument("--nome")
    ap.add_argument("--so-autor", action="store_true", help="usa só os posts do mesmo autor do primeiro (ignora comentários)")
    ap.add_argument("--sem-render", action="store_true")
    ap.add_argument("--cpu", action="store_true")
    a = ap.parse_args()

    print("baixando a thread...")
    posts = baixar_thread(a.url)
    assunto, fonte = montar_fonte(posts, a.so_autor)
    print(f"{len(posts)} posts, {len(fonte)} caracteres de texto")

    modelo = open(os.path.join(AQUI, "prompt_roteiro.md"), encoding="utf-8").read()
    prompt = modelo.replace("{{URL}}", a.url).replace("{{ASSUNTO}}", assunto).replace("{{FONTE}}", fonte)
    print(f"adaptando com o LLM ({a.provedor})... (pode levar alguns minutos)")
    resposta = chamar_llm(prompt, a.provedor)
    partes = separar(resposta)
    if "ROTEIRO" not in partes:
        raise SystemExit("O LLM não devolveu o roteiro no formato esperado. Resposta:\n" + resposta[:1500])

    cab = re.search(r"^titulo:\s*(.+)$", partes["ROTEIRO"], re.M)
    pasta = proxima_pasta(cab.group(1) if cab else assunto, a.nome)
    os.makedirs(pasta, exist_ok=True)
    for nome, arq in (("ROTEIRO", "roteiro.txt"), ("FUNDOS", "prompts_fundos.md"), ("DESCRICAO", "descricao.txt")):
        if nome in partes:
            open(os.path.join(pasta, arq), "w", encoding="utf-8", newline="\n").write(partes[nome])
    print("episódio:", pasta)

    if a.sem_render:
        print("Revise o roteiro.txt e rode: python youtube/motor/build.py", os.path.relpath(pasta))
        return
    cmd = [sys.executable, os.path.join(AQUI, "build.py"), pasta] + (["--cpu"] if a.cpu else [])
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
