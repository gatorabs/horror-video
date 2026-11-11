# youtube/: narração assistida de creepypastas

Formato: **o texto do relato na tela, parágrafo por parágrafo, lido em voz alta**, sobre um fundo escuro estático (zoom lento).
O parágrafo que está sendo lido fica em destaque, com uma barra vermelha. O vídeo abre com o painel surgindo em fade (sem cartão de título). Sem animações além de fade entre fundos.
Voz: ElevenLabs (`oJebhZNaPllxk6W0LSBA`). Um drone de ambiente baixinho corre por baixo.

## Jeito rápido: só o link
Pela interface: `youtube/abrir.bat` (ou `python youtube/interface.py`). Ao abrir, ela confere o ambiente (ffmpeg, bibliotecas, Claude Code, chave do ElevenLabs) e ajuda a resolver o que faltar. Depois é só colar o link e clicar em PROCESSAR; ela mostra onde o vídeo ficou.
Pela linha de comando:
```bash
python youtube/motor/gerar.py "https://boards.4chan.org/x/thread/ID/nome"
```
Baixa a thread, o LLM adapta para roteiro narrado em PT-BR (com aviso de conteúdo, fundos e descrição) e o motor gera voz e vídeo.
Por padrão usa o Claude Code em modo headless (`claude -p`, sem chave). Com `--provedor api` usa a API (`ANTHROPIC_API_KEY`).
Opções úteis: `--sem-render` (só o roteiro, para revisar antes de gastar voz), `--so-autor` (ignora comentários de outros usuários), `--nome 02-titulo`.
O estilo do roteiro está em `motor/prompt_roteiro.md`. Revise sempre o roteiro gerado (fidelidade e conteúdo sensível) antes do render.

## Workflow manual de um vídeo novo
1. **Escolha o relato** (fórum, thread, reddit). Leia inteiro e confira conteúdo sensível antes de adaptar.
2. **Crie a pasta** `youtube/episodios/NN-nome/` com um `roteiro.txt`:
   ```
   titulo: O Lorde Pálido
   subtitulo: Creepypasta
   fonte: autor, onde foi publicado
   ---
   @fundo 01 verde
   Parágrafo um.

   Parágrafo dois.
   @fundo 02 vermelho
   Outro trecho, com outro fundo.
   ```
   Cada parágrafo (linha em branco entre eles) vira um trecho de voz e um destaque. `@fundo NN cor` troca o fundo
   (cores: verde, vermelho, sepia, rosa, azul, cinza). Abertura: contexto + aviso de conteúdo. Fecho: pergunta para os comentários.
3. **Fundos** (opcional): gere imagens 16:9 sem pessoas (`prompts_fundos.md` tem um modelo) e salve em `fundos/NN.jpg`.
   Sem a imagem, o motor usa uma névoa escura gerada.
4. **Confira o layout de graça:**
   ```bash
   python youtube/motor/build.py youtube/episodios/NN-nome --quadros
   ```
   Amostras em `build/quadros/`.
5. **Teste barato da voz** (só os 4 primeiros parágrafos): `--ate 4`.
6. **Render completo:**
   ```bash
   python youtube/motor/build.py youtube/episodios/NN-nome
   ```
   Saída: `NN-nome.mp4` e `capa.jpg` (miniatura 1280x720) na pasta do episódio. A voz fica em cache: mudou um parágrafo, só ele gasta crédito.
   `--cpu` força o encoder de CPU (sem NVENC).
7. **Publicar:** use o `descricao.txt` do episódio (título, descrição, crédito do autor original, avisos). Marque "conteúdo sintético" e restrição de idade quando houver tema pesado.

## Estrutura
```
motor/roteiro.py   lê o roteiro.txt
motor/tts.py       narração ElevenLabs por parágrafo (cache)
motor/fundos.py    fundo (sua imagem ou névoa procedural), escurecido e com vinheta
motor/render.py    painel de texto, quadro de título e miniatura
motor/ambiente.py  detecta Claude Code, chave do ElevenLabs, ffmpeg e bibliotecas
interface.py       janela: link -> PROCESSAR -> caminho do arquivo
abrir.bat          abre a interface com dois cliques (Windows)
motor/gerar.py     link do 4chan -> roteiro (LLM) -> build
motor/prompt_roteiro.md  instruções do LLM para adaptar o relato
motor/build.py     orquestra voz, linha do tempo, ffmpeg e o mp4 final
episodios/NN-nome/ roteiro.txt, prompts_fundos.md, descricao.txt, vídeo e capa (ficam só no seu computador, fora do git)
```

## Requisitos
Python 3.12+ com `numpy` e `pillow`, ffmpeg no PATH (NVENC opcional) e a chave do ElevenLabs em `~/.elevenlabs_key`
(no Windows o motor lê a do WSL) ou na variável `ELEVENLABS_API_KEY`.
