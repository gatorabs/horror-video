"""Interface do gerador de vídeos do YouTube: cole o link do 4chan, clique em PROCESSAR, veja onde o arquivo ficou.

    python youtube/interface.py      (ou dê dois cliques em youtube/abrir.bat)
"""
import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk

AQUI = os.path.dirname(os.path.abspath(__file__))
GERAR = os.path.join(AQUI, "motor", "gerar.py")

BG, FG, DIM, ACC, OK = "#0a0908", "#c9c2b8", "#6a645b", "#c8282a", "#9ab87a"
MONO = ("Consolas", 11)

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
        raiz.geometry("820x760")
        raiz.minsize(760, 700)
        self.fila = queue.Queue()
        self.proc = None
        self.caminho = None
        self.rodando = False
        self.giro = 0

        self.txt(banner(), ACC, ("Consolas", 12, "bold"), pady=(18, 0))
        self.txt("n a r r a ç ã o   d e   r e l a t o s   d e   t e r r o", DIM, MONO, pady=(2, 4))
        self.txt("═" * 78, DIM, ("Consolas", 10))

        self.txt("─ LINK DA THREAD (4chan) " + "─" * 74, FG, ("Consolas", 10), anchor="w", padx=22, pady=(10, 2))
        caixa = tk.Frame(raiz, bg=BG, highlightbackground=DIM, highlightcolor=ACC, highlightthickness=1)
        caixa.pack(fill="x", padx=24)
        self.link = tk.Entry(caixa, bg="#12100e", fg=FG, insertbackground=ACC, relief="flat", font=("Consolas", 12))
        self.link.pack(fill="x", padx=2, pady=2, ipady=7)
        self.link.bind("<Return>", lambda e: self.processar())
        self.link.focus_set()

        opcoes = tk.Frame(raiz, bg=BG)
        opcoes.pack(fill="x", padx=24, pady=(10, 0))
        self.so_autor = tk.BooleanVar(value=True)
        self.so_roteiro = tk.BooleanVar(value=False)
        for var, rotulo in ((self.so_autor, "só os posts do autor"), (self.so_roteiro, "só gerar o roteiro (sem voz nem vídeo)")):
            tk.Checkbutton(opcoes, text=rotulo, variable=var, bg=BG, fg=FG, selectcolor="#12100e", activebackground=BG,
                           activeforeground=ACC, font=("Consolas", 10), highlightthickness=0, bd=0).pack(side="left", padx=(0, 22))

        botoes = tk.Frame(raiz, bg=BG)
        botoes.pack(pady=(16, 6))
        self.b_proc = self.botao(botoes, "[  PROCESSAR  ]", self.processar, ACC)
        self.b_proc.pack(side="left", padx=8)
        self.b_cancel = self.botao(botoes, "[  CANCELAR  ]", self.cancelar, DIM)
        self.b_cancel.pack(side="left", padx=8)
        self.b_cancel.config(state="disabled")

        self.status = self.txt("[ ] aguardando um link", DIM, MONO, pady=(6, 2))

        self.txt("─ ANDAMENTO " + "─" * 78, FG, ("Consolas", 10), anchor="w", padx=22, pady=(8, 2))
        moldura = tk.Frame(raiz, bg=BG, highlightbackground=DIM, highlightthickness=1)
        moldura.pack(fill="both", expand=True, padx=24)
        self.log = tk.Text(moldura, bg="#0d0b0a", fg=DIM, relief="flat", font=("Consolas", 10), height=8, wrap="word",
                           state="disabled", padx=10, pady=8)
        self.log.pack(fill="both", expand=True)

        self.txt("─ ARQUIVO " + "─" * 78, FG, ("Consolas", 10), anchor="w", padx=22, pady=(10, 2))
        self.res = tk.Label(raiz, text="┤ ainda não há arquivo ├", bg=BG, fg=DIM, font=("Consolas", 11), anchor="w",
                            justify="left", wraplength=760)
        self.res.pack(fill="x", padx=26)
        acoes = tk.Frame(raiz, bg=BG)
        acoes.pack(pady=(8, 14))
        self.b_abrir = self.botao(acoes, "[ ABRIR PASTA ]", self.abrir_pasta, FG)
        self.b_abrir.pack(side="left", padx=8)
        self.b_copiar = self.botao(acoes, "[ COPIAR CAMINHO ]", self.copiar, FG)
        self.b_copiar.pack(side="left", padx=8)
        self.b_abrir.config(state="disabled")
        self.b_copiar.config(state="disabled")

        raiz.protocol("WM_DELETE_WINDOW", self.fechar)
        self.raiz.after(120, self.tic)

    # ---- widgets ----
    def txt(self, texto, cor, fonte, pady=0, anchor="center", padx=0):
        l = tk.Label(self.raiz, text=texto, bg=BG, fg=cor, font=fonte, anchor=anchor, justify="left" if anchor == "w" else "center")
        l.pack(fill="x" if anchor == "w" else None, pady=pady, padx=padx)
        return l

    def botao(self, pai, texto, cmd, cor):
        return tk.Button(pai, text=texto, command=cmd, bg=BG, fg=cor, activebackground="#1a1614", activeforeground=ACC,
                         disabledforeground="#332f2a", relief="flat", bd=0, font=("Consolas", 12, "bold"), cursor="hand2",
                         highlightthickness=1, highlightbackground=cor, padx=10, pady=5)

    def escrever(self, linha):
        self.log.config(state="normal")
        self.log.insert("end", linha + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    # ---- ações ----
    def processar(self):
        if self.rodando:
            return
        url = self.link.get().strip()
        if not re.search(r"4chan(?:nel)?\.org/\w+/thread/\d+", url):
            self.definir_status("[!] cole o link de uma thread do 4chan (boards.4chan.org/x/thread/123...)", ACC)
            return
        cmd = [sys.executable, "-u", GERAR, url]
        if self.so_autor.get():
            cmd.append("--so-autor")
        if self.so_roteiro.get():
            cmd.append("--sem-render")
        self.caminho = None
        self.log.config(state="normal")
        self.log.delete("1.0", "end")
        self.log.config(state="disabled")
        self.res.config(text="┤ processando… ├", fg=DIM)
        self.b_abrir.config(state="disabled")
        self.b_copiar.config(state="disabled")
        self.rodando = True
        self.b_proc.config(state="disabled")
        self.b_cancel.config(state="normal")
        env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env,
                                     cwd=os.path.dirname(AQUI), creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        threading.Thread(target=self.ler, args=(self.proc,), daemon=True).start()

    def ler(self, proc):
        for bruto in proc.stdout:
            self.fila.put(("linha", bruto.decode("utf-8", errors="replace").rstrip()))
        proc.wait()
        self.fila.put(("fim", proc.returncode))

    def cancelar(self):
        if self.proc and self.proc.poll() is None:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.proc.pid)], capture_output=True)
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
                else:
                    self.terminou(valor)
        except queue.Empty:
            pass
        if self.rodando:
            self.giro += 1
            self.definir_status(f"[{'|/-\\'[self.giro % 4]}] {getattr(self, 'ultima', 'iniciando…')[:84]}", FG)
        self.raiz.after(120, self.tic)

    def terminou(self, codigo):
        self.rodando = False
        self.b_proc.config(state="normal")
        self.b_cancel.config(state="disabled")
        if codigo == 0 and self.caminho:
            self.definir_status("[✓] pronto", OK)
            self.res.config(text="┤ " + self.caminho + " ├", fg=OK)
            self.b_abrir.config(state="normal")
            self.b_copiar.config(state="normal")
        else:
            self.definir_status("[x] não terminou; veja o andamento acima", ACC)
            self.res.config(text="┤ nenhum arquivo gerado ├", fg=DIM)

    def definir_status(self, texto, cor):
        self.status.config(text=texto, fg=cor)

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
    if len(sys.argv) > 1 and sys.argv[1] == "--teste":  # abre, tira um print e fecha (para conferir o visual)
        def print_tela():
            from PIL import ImageGrab
            raiz.update()
            x, y, w, h = raiz.winfo_rootx(), raiz.winfo_rooty(), raiz.winfo_width(), raiz.winfo_height()
            ImageGrab.grab((x, y, x + w, y + h)).save(sys.argv[2])
            raiz.destroy()
        raiz.after(900, print_tela)
    raiz.mainloop()
