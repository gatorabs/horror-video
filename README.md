# horror-video (branch main): Reels do canal Temos Vagas 🩸

Esta branch guarda só os **Reels** (vertical 9:16, imagens geradas por IA, voz ElevenLabs, agendados no Metricool).
Os vídeos do **YouTube** (motor `engine/`, cutscenes 2D, render na GPU) ficam na branch `youtube`, sem nenhum arquivo em comum.

## Estrutura
```
episodios/NN-nome/prompts.md   prompts das imagens de cada Reel já agendado (01 a 03)
ferramentas/imagens-ia/        render.py, mix.py e tts.py do formato com imagens de IA
PROMPT_MODELO.md               passo a passo para criar um Reel novo
```
Os MP4 finais ficam só locais (ignorados pelo git).
