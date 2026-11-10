# horror-video: vídeos de terror narrados 🩸

```
youtube/   vídeos longos: o texto do relato na tela, lido por voz (ElevenLabs). Você passa o link do 4chan e sai o vídeo.
reels/     Reels verticais (imagens de IA, Metricool). Em espera até haver integração com geração de imagem.
```

## Como usar (YouTube)
Abra a interface (`youtube/abrir.bat` no Windows, ou `python youtube/interface.py`), cole o link da thread do 4chan e clique em **PROCESSAR**.
Ao terminar, ela mostra onde o vídeo ficou (`youtube/episodios/NN-titulo/NN-titulo.mp4`), junto com `capa.jpg`, `descricao.txt` e o roteiro.

Pela linha de comando: `python youtube/motor/gerar.py "<link>" --so-autor`.
Detalhes, opções e o fluxo manual: [`youtube/README.md`](youtube/README.md).

## O que ele precisa
Python 3.12+ (`numpy`, `pillow`), ffmpeg no PATH (usa a placa NVIDIA se houver, senão a CPU), o Claude Code instalado e logado
(ele adapta o relato para roteiro; alternativa: `ANTHROPIC_API_KEY` com `--provedor api`) e a chave do ElevenLabs em `~/.elevenlabs_key`.

## Reels
`reels/` guarda os 3 Reels já agendados (prompts) e o fluxo antigo com imagens de IA. Veja `reels/README.md`.
