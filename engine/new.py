"""Cria a pasta de um episódio novo a partir do modelo:  python -m engine.new episodios/05-nome-do-video"""
import shutil, sys
from pathlib import Path

def main():
    dest = Path(sys.argv[1]); dest.mkdir(parents=True, exist_ok=True)
    target = dest / "script.py"
    if target.exists(): raise SystemExit(f"{target} já existe")
    shutil.copy(Path(__file__).parent / "template_script.py", target)
    print(f"criado {target}. Edite o roteiro e rode: python -m engine.build {dest}")

if __name__ == "__main__":
    main()
