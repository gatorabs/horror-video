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
Python 3.12+ (`numpy`, `pillow`), ffmpeg (usa a placa NVIDIA se houver, senão a CPU), o Claude Code logado (adapta o relato em roteiro;
alternativa: `ANTHROPIC_API_KEY` com `--provedor api`) e a chave do ElevenLabs (`~/.elevenlabs_key` ou `ELEVENLABS_API_KEY`).

A interface confere tudo isso ao abrir, no painel **AMBIENTE**: mostra o que está ok e, onde faltar algo, tem botões para instalar o
ffmpeg, as bibliotecas e o Claude Code, para entrar na conta do Claude e para colar/trocar a chave do ElevenLabs (mostra o saldo de caracteres).

## Reels
`reels/` guarda os 3 Reels já agendados (prompts) e o fluxo antigo com imagens de IA. Veja `reels/README.md`.
