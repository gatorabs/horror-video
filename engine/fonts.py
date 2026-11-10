"""Copia as fontes do WSL/Linux para engine/fonts (necessário uma vez para renderizar no Windows):  python -m engine.fonts"""
import os, shutil, subprocess
from pathlib import Path

NAMES = ["FreeSerifBold.ttf", "FreeSerifBoldItalic.ttf", "FreeSerifItalic.ttf", "FreeSans.ttf", "FreeSansBold.ttf",
         "FreeSansBoldOblique.ttf", "FreeMonoBold.ttf", "DejaVuSerif-Bold.ttf"]
SRC = {"DejaVuSerif-Bold.ttf": "/usr/share/fonts/truetype/dejavu/"}
DEFAULT = "/usr/share/fonts/truetype/freefont/"
DST = Path(__file__).parent / "fonts"

def main():
    DST.mkdir(exist_ok=True)
    for n in NAMES:
        src = SRC.get(n, DEFAULT) + n
        if os.name == "nt":
            subprocess.run(["wsl", "bash", "-lc", f"cp {src} /mnt/{DST.drive[0].lower()}/{str(DST)[3:].replace(chr(92), '/')}/"], check=True)
        else:
            shutil.copy(src, DST / n)
    print("fontes em", DST)

if __name__ == "__main__":
    main()
