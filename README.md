# horror-video (branch youtube): vídeos longos de terror 🩸

Motor para produzir vídeos narrados de terror (relatos do Reddit, "Você foi contratado" etc.): **texto lido palavra por palavra,
cutscenes 2D animadas** (só cenários e objetos, sem rostos), **voz ElevenLabs** e render na **placa de vídeo**.

Um episódio novo = uma pasta com **um único arquivo de conteúdo** (`script.py`). Todo o resto é o motor, em `engine/`.

## Fluxo de um vídeo novo
```bash
python -m engine.new episodios/05-nome-do-video      # cria o script.py a partir do modelo
# edite o roteiro (texto, cenas, cutscenes) em episodios/05-nome-do-video/script.py
python -m engine.preview episodios/05-nome-do-video s01:1.5 s03:6   # prévia de quadros (segundos ou cena:segundos)
python -m engine.build episodios/05-nome-do-video    # voz + mix + render + mp4 final
```
O MP4 sai em `episodios/05-nome-do-video/05-nome-do-video.mp4`. Etapas isoladas: `--steps tts,mix,render,mux`.
Mudou só o visual? `--steps render,mux`. A narração fica em cache (só gasta crédito do que mudou).

## Estrutura
```
engine/
  episode.py      formato do script.py (CONFIG, SCENES, HITS)
  cutscenes.py    biblioteca de cutscenes 2D (catálogo no topo do arquivo)
  tts.py          narração ElevenLabs frase a frase (cache)           [precisa de sox: roda no WSL]
  mix.py          voz + trilha + efeitos -> mix.wav + timeline.json   [idem]
  render.py       quadros 1080p (GPU via CuPy, ou CPU), em 14 blocos
  build.py        orquestra tudo e gera o mp4
  core.py         backend GPU/CPU, helpers de imagem, fontes
  template_script.py  modelo de episódio novo
episodios/NN-nome/script.py   o conteúdo de um episódio novo
```

## Requisitos
- **WSL (Ubuntu):** `./setup.sh` (ffmpeg, sox, fontes, numpy/pillow/soundfile). Chave do ElevenLabs em `~/.elevenlabs_key`.
- **Windows (render na GPU):** Python 3.12+, ffmpeg com `h264_nvenc`, `pip install numpy pillow` e, para a GPU NVIDIA,
  `pip install "cupy-cuda13x[ctk]"`. Uma vez: `python -m engine.fonts`. Sem GPU/CuPy o motor usa a CPU sozinho (`--cpu` força).
- O `build` roda tts/mix dentro do WSL automaticamente quando está no Windows.

## O que fica no git
Branch `youtube`: só o motor (`engine/`) e o `setup.sh`. Os Reels (imagens de IA + Metricool) vivem na branch `main`, totalmente separados.
Fora do git: saídas (`build/`, `*.mp4`, `*.wav`), fontes copiadas e `ref/`. O `script.py` de cada episódio fica local;
para versionar um de propósito: `git add -f episodios/NN-nome/script.py`.
