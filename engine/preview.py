"""Prévia rápida de quadros (sem renderizar o vídeo):  python -m engine.preview episodios/NN-nome 12.5 s05:8 s15:9
'12.5' = segundos; 's05:8' = 8 s depois do início da cena s05. Salva em episodios/NN-nome/build/prev/ (inclui sheet.png)."""
import sys
from .render import preview
if __name__ == "__main__":
    preview(sys.argv[1], sys.argv[2:])
