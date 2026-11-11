"""Interface do gerador de vídeos do YouTube.

Ao abrir, confere o ambiente (ffmpeg, bibliotecas, Claude Code, chave do ElevenLabs) e ajuda a resolver o que faltar.
Depois: cole o link do 4chan, clique em PROCESSAR e veja onde o arquivo ficou.

    python youtube/interface.py      (ou dois cliques em youtube/abrir.bat)
"""
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox

AQUI = os.path.dirname(os.path.abspath(__file__))
GERAR = os.path.join(AQUI, "motor", "gerar.py")
sys.path.insert(0, os.path.join(AQUI, "motor"))
import ambiente  # noqa: E402

BG, FG, DIM, ACC, OK, AVISO = "#0a0908", "#c9c2b8", "#6a645b", "#c8282a", "#9ab87a", "#d9a441"
MONO = ("Consolas", 11)
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

GLIFOS = {
    "H": ["██╗  ██╗", "██║  ██║", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    "O": [" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "R": ["██████╗ ", "██╔══██╗", "██████╔╝", "██╔══██╗", "██║  ██║", "╚═╝  ╚═╝"],
}


def banner(palavra="HORROR"):
    letras = [[l.ljust(9) for l in GLIFOS[c]] for c in palavra]
    return "\n".join("".join(l[i] for l in letras).rstrip() for i in range(6))


class App:
    def __init__(self, raiz):
        self.raiz = raiz
        raiz.title("HORROR · gerador de vídeos")
        raiz.configure(bg=BG)
        raiz.geometry("860x960")
        raiz.minsize(800, 860)
        self.fila = queue.Queue()
        self.proc = None
        self.caminho = None
        self.rodando = False
        self.ao_fim = None
        self.giro = 0
        self.ultima = "iniciando…"
        self.amb = {}
        self.tentativas_login = 0

        self.txt(banner(), ACC, ("Consolas", 11, "bold"), pady=(14, 0))
        self.txt("n a r r a ç ã o   d e   r e l a t o s   d e   t e r r o", DIM, MONO, pady=(2, 2))
        self.txt("═" * 82, DIM, ("Consolas", 10))

        # ---- ambiente ----
        self.txt("─ AMBIENTE " + "─" * 82, FG, ("Consolas", 10), anchor="w", padx=22, pady=(8, 2))
        grade = tk.Frame(raiz, bg=BG)
        grade.pack(fill="x", padx=26)
        grade.columnconfigure(1, weight=1)
        self.linhas = {}
        for r, (chave, nome) in enumerate((("ffmpeg", "ffmpeg"), ("libs", "numpy / pillow"), ("claude", "Claude Code"),
                                           ("eleven", "ElevenLabs"))):
            ic = tk.Label(grade, text="[…]", bg=BG, fg=DIM, font=MONO, width=4, anchor="w")
            nm = tk.Label(grade, text=nome, bg=BG, fg=FG, font=MONO, width=15, anchor="w")
            dt = tk.Label(grade, text="verificando…", bg=BG, fg=DIM, font=("Consolas", 10), anchor="w", justify="left")
            bt = self.botao(grade, "", None, FG, pequeno=True)
            ic.grid(row=r, column=0, sticky="w", pady=2)
            nm.grid(row=r, column=0, sticky="w", padx=(40, 0), pady=2)
            dt.grid(row=r, column=1, sticky="w", padx=(150, 0), pady=2)
            bt.grid(row=r, column=2, sticky="e", pady=2)
            bt.grid_remove()
            self.linhas[chave] = (ic, dt, bt)

        chave_box = tk.Frame(raiz, bg=BG)
        chave_box.pack(fill="x", padx=26, pady=(4, 0))
        tk.Label(chave_box, text="chave ElevenLabs:", bg=BG, fg=DIM, font=("Consolas", 10)).pack(side="left")
        moldura = tk.Frame(chave_box, bg=BG, highlightbackground=DIM, highlightcolor=ACC, highlightthickness=1)
        moldura.pack(side="left", fill="x", expand=True, padx=8)
        self.entrada_chave = tk.Entry(moldura, bg="#12100e", fg=FG, insertbackground=ACC, relief="flat", show="•",
                                      font=("Consolas", 11))
        self.entrada_chave.pack(fill="x", padx=2, pady=2, ipady=3)
        self.entrada_chave.bind("<Return>", lambda e: self.salvar_chave())
        self.b_salvar = self.botao(chave_box, "[ SALVAR ]", self.salvar_chave, FG, pequeno=True)
        self.b_salvar.pack(side="left")

        # ---- link ----
        self.txt("─ LINK DA THREAD (4chan) " + "─" * 82, FG, ("Consolas", 10), anchor="w", padx=22, pady=(12, 2))
        caixa = tk.Frame(raiz, bg=BG, highlightbackground=DIM, highlightcolor=ACC, highlightthickness=1)
        caixa.pack(fill="x", padx=24)
        self.link = tk.Entry(caixa, bg="#12100e", fg=FG, insertbackground=ACC, relief="flat", font=("Consolas", 12))
        self.link.pack(fill="x", padx=2, pady=2, ipady=7)
        self.link.bind("<Return>", lambda e: self.processar())
        self.link.focus_set()

        opcoes = tk.Frame(raiz, bg=BG)
        opcoes.pack(fill="x", padx=24, pady=(8, 0))
        self.so_autor = tk.BooleanVar(value=True)
        self.so_roteiro = tk.BooleanVar(value=False)
        for var, rotulo in ((self.so_autor, "só os posts do autor"), (self.so_roteiro, "só gerar o roteiro (sem voz nem vídeo)")):
            tk.Checkbutton(opcoes, text=rotulo, variable=var, bg=BG, fg=FG, selectcolor="#12100e", activebackground=BG,
                           activeforeground=ACC, font=("Consolas", 10), highlightthickness=0, bd=0).pack(side="left", padx=(0, 22))

        botoes = tk.Frame(raiz, bg=BG)
        botoes.pack(pady=(12, 4))
        self.b_proc = self.botao(botoes, "[  PROCESSAR  ]", self.processar, ACC)
        self.b_proc.pack(side="left", padx=8)
        self.b_cancel = self.botao(botoes, "[  CANCELAR  ]", self.cancelar, DIM)
        self.b_cancel.pack(side="left", padx=8)
        self.b_cancel.config(state="disabled")

        self.status = self.txt("[ ] aguardando um link", DIM, MONO, pady=(4, 2))

        self.txt("─ ANDAMENTO " + "─" * 82, FG, ("Consolas", 10), anchor="w", padx=22, pady=(6, 2))
        moldura_log = tk.Frame(raiz, bg=BG, highlightbackground=DIM, highlightthickness=1)
        moldura_log.pack(fill="both", expand=True, padx=24)
        self.log = tk.Text(moldura_log, bg="#0d0b0a", fg=DIM, relief="flat", font=("Consolas", 10), height=6, wrap="word",
                           state="disabled", padx=10, pady=8)
        self.log.pack(fill="both", expand=True)

        self.txt("─ ARQUIVO " + "─" * 82, FG, ("Consolas", 10), anchor="w", padx=22, pady=(8, 2))
        self.res = tk.Label(raiz, text="┤ ainda não há arquivo ├", bg=BG, fg=DIM, font=("Consolas", 11), anchor="w",
                            justify="left", wraplength=800)
        self.res.pack(fill="x", padx=26)
        acoes = tk.Frame(raiz, bg=BG)
        acoes.pack(pady=(6, 12))
        self.b_abrir = self.botao(acoes, "[ ABRIR PASTA ]", self.abrir_pasta, FG)
        self.b_abrir.pack(side="left", padx=8)
        self.b_copiar = self.botao(acoes, "[ COPIAR CAMINHO ]", self.copiar, FG)
        self.b_copiar.pack(side="left", padx=8)
        self.b_abrir.config(state="disabled")
        self.b_copiar.config(state="disabled")

        raiz.protocol("WM_DELETE_WINDOW", self.fechar)
        self.verificar()
        self.raiz.after(120, self.tic)

    # ---------- widgets ----------
    def txt(self, texto, cor, fonte, pady=0, anchor="center", padx=0):
        l = tk.Label(self.raiz, text=texto, bg=BG, fg=cor, font=fonte, anchor=anchor, justify="left" if anchor == "w" else "center")
        l.pack(fill="x" if anchor == "w" else None, pady=pady, padx=padx)
        return l

    def botao(self, pai, texto, cmd, cor, pequeno=False):
        return tk.Button(pai, text=texto, command=cmd, bg=BG, fg=cor, activebackground="#1a1614", activeforeground=ACC,
                         disabledforeground="#332f2a", relief="flat", bd=0, font=("Consolas", 10 if pequeno else 12, "bold"),
                         cursor="hand2", highlightthickness=1, highlightbackground=cor, padx=8, pady=3 if pequeno else 5)

    def escrever(self, linha):
        self.log.config(state="normal")
        self.log.insert("end", linha + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def definir_status(self, texto, cor):
        self.status.config(text=texto, fg=cor)

    # ---------- ambiente ----------
    def verificar(self):
        threading.Thread(target=self._verificar, daemon=True).start()

    def _verificar(self):
        amb = {"ffmpeg": ambiente.tem_ffmpeg(), "libs": ambiente.libs_faltando()}
        amb["claude"] = ambiente.claude_estado()
        k = ambiente.chave_eleven()
        amb["eleven"] = (k, *ambiente.validar_eleven(k)) if k else (None, False, "nenhuma chave encontrada")
        amb["anthropic_env"] = bool(os.environ.get("ANTHROPIC_API_KEY"))
        self.fila.put(("amb", amb))

    def aplicar_ambiente(self, amb):
        self.amb = amb
        def linha(chave, ok, texto, botao=None, cmd=None):
            ic, dt, bt = self.linhas[chave]
            ic.config(text="[✓]" if ok is True else ("[!]" if ok is None else "[x]"), fg=OK if ok is True else (AVISO if ok is None else ACC))
            dt.config(text=texto, fg=FG if ok is True else (AVISO if ok is None else ACC))
            if botao:
                bt.config(text=botao, command=cmd)
                bt.grid()
            else:
                bt.grid_remove()

        linha("ffmpeg", amb["ffmpeg"], "encontrado" if amb["ffmpeg"] else "não encontrado",
              None if amb["ffmpeg"] else "[ INSTALAR ]", self.instalar_ffmpeg)
        falta = amb["libs"]
        linha("libs", not falta, "ok" if not falta else "faltam: " + ", ".join(falta),
              None if not falta else "[ INSTALAR ]", self.instalar_libs)
        instalado, logado, texto = amb["claude"]
        if logado:
            linha("claude", True, texto)
        elif not instalado:
            linha("claude", False, "não instalado (ele adapta o relato em roteiro)", "[ INSTALAR ]", self.instalar_claude)
        else:
            linha("claude", False, texto, "[ ENTRAR ]", self.entrar_claude)
        k, ok, texto_k = amb["eleven"]
        linha("eleven", ok, texto_k if k else "sem chave: cole abaixo e clique em SALVAR")
        if k:
            self.b_salvar.config(text="[ TROCAR ]")
        else:
            self.b_salvar.config(text="[ SALVAR ]")

    def pronto_para(self, so_roteiro):
        """Retorna (ok, mensagem, usar_api)."""
        amb = self.amb
        if not amb:
            return False, "[…] ainda verificando o ambiente, aguarde um instante", False
        _, logado, _ = amb["claude"]
        usar_api = not logado and amb.get("anthropic_env")
        if not logado and not usar_api:
            return False, "[!] falta o Claude Code: use [ INSTALAR ] / [ ENTRAR ] no painel AMBIENTE", False
        if not so_roteiro:
            if amb["eleven"][1] is False:
                return False, "[!] falta uma chave válida do ElevenLabs: cole no painel AMBIENTE e clique em SALVAR", False
            if not amb["ffmpeg"]:
                return False, "[!] falta o ffmpeg: use [ INSTALAR ] no painel AMBIENTE", False
            if amb["libs"]:
                return False, "[!] faltam bibliotecas Python: use [ INSTALAR ] no painel AMBIENTE", False
        return True, "", usar_api

    def salvar_chave(self):
        k = self.entrada_chave.get().strip()
        if not k:
            self.definir_status("[!] cole a chave do ElevenLabs no campo e clique em SALVAR", AVISO)
            return
        if re.search(r"\s", k):
            self.definir_status("[!] a chave não pode ter espaços", ACC)
            return
        ambiente.salvar_chave_eleven(k)
        self.entrada_chave.delete(0, "end")
        self.definir_status("[✓] chave salva em " + ambiente.ARQ_CHAVE, OK)
        self.verificar()

    def instalar_ffmpeg(self):
        if os.name == "nt" and shutil.which("winget"):
            self.tarefa(["winget", "install", "-e", "--id", "Gyan.FFmpeg", "--accept-package-agreements", "--accept-source-agreements"],
                        "winget install -e --id Gyan.FFmpeg", reabrir=True)
        elif sys.platform == "darwin" and shutil.which("brew"):
            self.tarefa(["brew", "install", "ffmpeg"], "brew install ffmpeg", reabrir=True)
        elif shutil.which("apt-get"):
            messagebox.showinfo("Instalar ffmpeg", "Rode no terminal:\n\nsudo apt install ffmpeg\n\ne reabra esta janela.")
        else:
            messagebox.showinfo("Instalar ffmpeg", "Instale o ffmpeg (https://ffmpeg.org/download.html), deixe no PATH e reabra esta janela.")

    def instalar_libs(self):
        faltam = self.amb.get("libs") or ["numpy", "pillow"]
        self.tarefa([sys.executable, "-m", "pip", "install", *faltam], f"python -m pip install {' '.join(faltam)}")

    def instalar_claude(self):
        npm = shutil.which("npm")
        if npm:
            cmd, texto = [npm, "install", "-g", "@anthropic-ai/claude-code"], "npm install -g @anthropic-ai/claude-code"
        elif os.name == "nt":
            texto = "irm https://claude.ai/install.ps1 | iex"
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", texto]
        else:
            texto = "curl -fsSL https://claude.ai/install.sh | bash"
            cmd = ["bash", "-c", texto]
        self.tarefa(cmd, texto)

    def entrar_claude(self):
        exe = ambiente.achar_claude()
        if not exe:
            return
        self.escrever("-- login do Claude: conclua no navegador (uma janela de terminal pode abrir) --")
        self.definir_status("[i] conclua o login no navegador; esta tela confere sozinha", AVISO)
        if os.name == "nt":
            subprocess.Popen(["cmd.exe", "/c", "start", "Entrar no Claude", "cmd.exe", "/k", exe, "auth", "login"])
        else:
            subprocess.Popen([exe, "auth", "login"])
        self.tentativas_login = 0
        self.raiz.after(5000, self.conferir_login)

    def conferir_login(self):
        _, logado, _ = self.amb.get("claude", (0, False, ""))
        if logado:
            self.definir_status("[✓] Claude Code logado", OK)
            return
        self.tentativas_login += 1
        if self.tentativas_login > 60:
            return
        self.verificar()
        self.raiz.after(5000, self.conferir_login)

    # ---------- execução de comandos ----------
    def tarefa(self, cmd, texto, reabrir=False):
        if self.rodando:
            return
        if not messagebox.askyesno("Confirmar", f"Vai rodar este comando:\n\n{texto}\n\nContinuar?"):
            return
        self.escrever(f"$ {texto}")
        self.executar(cmd, depois=(lambda cod: self.depois_instalar(cod, reabrir)))

    def depois_instalar(self, codigo, reabrir):
        if codigo == 0:
            msg = "[✓] instalado" + (" (se ainda aparecer faltando, feche e abra a interface de novo)" if reabrir else "")
            self.definir_status(msg, OK)
        else:
            self.definir_status("[x] a instalação falhou; veja o andamento acima", ACC)
        self.verificar()

    def executar(self, cmd, depois=None, cwd=None):
        self.ao_fim = depois
        self.rodando = True
        self.b_proc.config(state="disabled")
        self.b_cancel.config(state="normal")
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        try:
            self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env, cwd=cwd,
                                         creationflags=NO_WINDOW)
        except OSError as e:
            self.rodando = False
            self.b_proc.config(state="normal")
            self.b_cancel.config(state="disabled")
            self.escrever(f"não consegui iniciar o comando: {e}")
            return
        threading.Thread(target=self.ler, args=(self.proc,), daemon=True).start()

    def processar(self):
        if self.rodando:
            return
        url = self.link.get().strip()
        if not re.search(r"4chan(?:nel)?\.org/\w+/thread/\d+", url):
            self.definir_status("[!] cole o link de uma thread do 4chan (boards.4chan.org/x/thread/123...)", ACC)
            return
        ok, msg, usar_api = self.pronto_para(self.so_roteiro.get())
        if not ok:
            self.definir_status(msg, ACC)
            return
        cmd = [sys.executable, "-u", GERAR, url]
        if self.so_autor.get():
            cmd.append("--so-autor")
        if self.so_roteiro.get():
            cmd.append("--sem-render")
        if usar_api:
            cmd += ["--provedor", "api"]
        self.caminho = None
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        self.res.config(text="┤ processando… ├", fg=DIM)
        self.b_abrir.config(state="disabled")
        self.b_copiar.config(state="disabled")
        self.ultima = "iniciando…"
        self.executar(cmd, depois=self.terminou, cwd=os.path.dirname(AQUI))

    def ler(self, proc):
        for bruto in proc.stdout:
            self.fila.put(("linha", bruto.decode("utf-8", errors="replace").rstrip()))
        proc.wait()
        self.fila.put(("fim", proc.returncode))

    def cancelar(self):
        if self.proc and self.proc.poll() is None:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.proc.pid)], capture_output=True, creationflags=NO_WINDOW)
            else:
                self.proc.kill()
            self.escrever("-- cancelado --")

    def tic(self):
        try:
            while True:
                tipo, valor = self.fila.get_nowait()
                if tipo == "linha":
                    if valor.strip():
                        self.escrever(valor)
                        self.ultima = valor.strip()
                        m = re.search(r"OK ->\s*(.+)$", valor) or re.match(r"^epis.{1,3}dio:\s*(.+)$", valor.strip())
                        if m:
                            self.caminho = os.path.normpath(m.group(1).strip())
                elif tipo == "amb":
                    self.aplicar_ambiente(valor)
                else:
                    self.rodando = False
                    self.b_proc.config(state="normal")
                    self.b_cancel.config(state="disabled")
                    if self.ao_fim:
                        self.ao_fim(valor)
        except queue.Empty:
            pass
        if self.rodando:
            self.giro += 1
            self.definir_status(f"[{'|/-\\'[self.giro % 4]}] {self.ultima[:90]}", FG)
        self.raiz.after(120, self.tic)

    def terminou(self, codigo):
        if codigo == 0 and self.caminho:
            self.definir_status("[✓] pronto", OK)
            self.res.config(text="┤ " + self.caminho + " ├", fg=OK)
            self.b_abrir.config(state="normal")
            self.b_copiar.config(state="normal")
        else:
            self.definir_status("[x] não terminou; veja o andamento acima", ACC)
            self.res.config(text="┤ nenhum arquivo gerado ├", fg=DIM)

    def abrir_pasta(self):
        if not self.caminho:
            return
        alvo = self.caminho if os.path.isdir(self.caminho) else os.path.dirname(self.caminho)
        if os.name == "nt":
            if os.path.isfile(self.caminho):
                subprocess.Popen(["explorer", "/select,", self.caminho])
            else:
                os.startfile(alvo)
        else:
            subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", alvo])

    def copiar(self):
        if self.caminho:
            self.raiz.clipboard_clear()
            self.raiz.clipboard_append(self.caminho)
            self.definir_status("[✓] caminho copiado", OK)

    def fechar(self):
        self.cancelar()
        self.raiz.destroy()


if __name__ == "__main__":
    raiz = tk.Tk()
    app = App(raiz)
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":  # abre, espera a verificação, tira um print e fecha
        def print_tela():
            from PIL import ImageGrab
            raiz.update()
            x, y, w, h = raiz.winfo_rootx(), raiz.winfo_rooty(), raiz.winfo_width(), raiz.winfo_height()
            ImageGrab.grab((x, y, x + w, y + h)).save(sys.argv[2])
            raiz.destroy()
        raiz.after(9000, print_tela)
    raiz.mainloop()
