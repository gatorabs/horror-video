# horror-video: vídeos de terror do canal Temos Vagas 🩸

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
- `engine/` (motor), `ferramentas/imagens-ia/` (render/mix/tts do formato antigo de Reels com imagens de IA), `PROMPT_MODELO.md`.
- `episodios/01..03-*-ia/prompts.md`: só os prompts dos 3 episódios já publicados/agendados no Metricool.
Fora do git: saídas (`build/`, `*.mp4`, `*.wav`), fontes copiadas e `ref/`. Os MP4 finais ficam só locais, dentro de cada pasta de episódio.
Episódio novo do motor: o `script.py` fica local; para versionar, `git add -f episodios/NN-nome/script.py`.
