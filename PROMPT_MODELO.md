# Prompt modelo: novo episódio do Temos Vagas

Copie o bloco abaixo para o Claude, preencha os campos entre `{chaves}` e envie. O resto deste arquivo é a "bíblia" do formato, que o Claude deve seguir. Ela foi tirada do episódio 01 (Posto Estrela), que teve ótimo resultado.

---

## 1. O prompt (preencha e envie)

```
Crie o episódio {NÚMERO} do canal Temos Vagas (@temosvagas.terror), um Reel de terror
no formato "Você foi contratado". Use o repositório github.com/gatorabs/horror-video:
siga o PROMPT_MODELO.md à risca e use ferramentas/imagens-ia como base técnica
(mesmo pipeline: tts.py → mix.py → render.py → build.sh).

Emprego: {cargo — ex.: vigia noturno, recepcionista, zelador}
Local: {lugar brasileiro bem específico — ex.: "Shopping Vale Verde, Contagem-MG, piso G2"}
Turno: {horário — ex.: 22h às 6h}
Diária: {valor ALTO — ex.: R$ 2.500, paga em dinheiro no fim do turno}
Ideia para a virada da regra 5 (opcional): {ou deixe "você decide"}
Publicação: {data e hora, ou "melhor horário da semana"}

Entregue:
1. O roteiro (5 regras + virada) para eu aprovar antes de renderizar.
2. O vídeo final 1080x1920 e a capa.
3. A legenda do post.
4. O agendamento no Metricool (marca 7988382, Reel, marcado como conteúdo de IA).
```

---

## 2. Bíblia do formato

### Estrutura (55 a 65 segundos)
| Cena | Duração | Conteúdo |
|---|---|---|
| Intro | ~12 s | "Você foi contratado como {cargo}…" + local com nome, número, rodovia ou bairro + **a diária do contrato, sempre ALTA** (de R$ 1.500 a R$ 5.000, coerente com um trabalho paranormal; cartão grande "DIÁRIA R$ x") + **"Siga as regras."** (lento) |
| Regras 1–4 | 7–10 s cada | Cada regra tem um **gatilho concreto** (um horário exato, um objeto, um som) e uma **proibição curta** ("Não abra.", "Não olhe."). |
| Regra 5 | ~9 s | **A virada**: liga o protagonista ao horror e de preferência fecha um ciclo. Exemplo do ep. 01: "Se ninguém vier te render, não saia. **Agora é você quem bate no vidro.**" |
| Fecho | ~5 s | Silêncio, boom grave e a voz bem lenta: **"Temos vagas."** Depois aparecem o neon TEMOS VAGAS, a pergunta "Você aguentaria até as {fim do turno}?" e o @. |

### Regras do roteiro
- **Uma ideia por frase.** As frases ficam curtas, porque cada uma aparece e some sozinha na tela.
- Pelo menos **uma regra deve ecoar outra**. No ep. 01, o colega que bate no vidro (regra 4) volta na virada (regra 5).
- Use detalhes brasileiros e específicos: km de rodovia, nome de posto ou loja, ônibus, orelhão, BR, "plantão".
- **Narração × tela:** na narração, números vão por extenso ("duas e dezessete", "bomba quatro"). Na tela, vão em algarismos ("2h17", "bomba 4"). No `script.py`, cada frase é `(narrado, tela, velocidade, tom, pausa_depois)`.
- Frases de ameaça são mais **lentas e graves**: velocidade 108–120 e tom 28–32. Frases normais: velocidade 132–146 e tom 35–38.
- Pausas: 0,35–0,6 s entre frases e 0,8–1,1 s antes de uma virada ou de um som importante.
- Use reticências na tela para suspense em frase quebrada: "Se você contar dois…" / "…um deles não é cliente."
- Evite "às d…" no começo de frase, porque a voz mbrola falha no som z‑d. Reescreva ("Duas e dezessete da madrugada.").

### Voz (o que deixou a narração orgânica)
- Voz `mb-br3` (espeak-ng + MBROLA, masculina brasileira). A velocidade é a da tabela × 0,84, e a variação de entonação (range) é 45.
- Sintetize **frase por frase**, nunca o texto todo de uma vez.
- Tratamento (em `mix.py`): corta o silêncio, `pitch -120` cents, graves +4 dB, compressão leve. No fecho, `pitch -260` com tempo 0,72.
- Coloque **respirações** curtas antes da primeira frase de cada cena e antes das viradas.
- Ambiente: `reverb 28` + eco leve de 70 ms. Mantém a sensação de "gravação", mas sem soar robótico.
- Para uma voz humana, gere no ElevenLabs uma frase por arquivo e substitua os `vo_*.wav`. O resto do pipeline continua igual.

### Visual
- **Câmera de segurança VHS**: ● REC piscando, um relógio que **avança ao longo do turno** (cada cena num horário), "CAM 0X {ÁREA}", grão, scanlines, vinheta, glitch de 0,2 s nas trocas de cena e tremor de tela nos impactos.
- **Um único cenário** desenhado em camadas: base, luz fluorescente com flicker, janelas e placas. Objetos que passam por trás de outros usam máscara de profundidade (no ep. 01, o caminhão passa atrás das bombas e dos pilares).
- **Cada regra muda algo no cenário**, no momento exato em que a palavra é dita:
  - ep. 01: o caminhão chega e para em "parar"; olhos vermelhos na cabine em "Não olhe para a cabine"; a janela pisca com o telefone; uma 2ª silhueta aparece em "dois"; um vulto no vidro em "vidro".
- Na regra 5, a luz principal **morre aos poucos** e o céu começa a amanhecer.
- Paleta: preto azulado, luz fluorescente esverdeada, vermelho só para alertas, títulos e o neon.

### Texto na tela
- Rótulo fixo por cena: **"REGRA N"** em vermelho, FreeMono Bold 64, sublinhado. Na intro: "VOCÊ FOI / CONTRATADO".
- Corpo: DejaVu Sans Bold 62, alinhado à esquerda em x=100, largura máxima de 880 px.
- **Só a frase atual aparece.** As palavras surgem conforme são narradas, e a frase **some** (fade de 0,32 s, subindo um pouco) logo depois de narrada.
- Área segura do Reel: o texto fica entre y≈1050 e y≈1650. Nada importante perto da borda direita (botões do Instagram).

### Som
- Base: drone grave (49 Hz com batimento), zumbido fluorescente, chiado de fita e tensão crescendo até o fim.
- **Um efeito por regra, preso a uma palavra** (âncoras em `mix.py`, que o `render.py` também usa): motor e freio a ar, telefone de 425 Hz, campainha de loja, batidas no vidro.
- Coração acelerando nas regras 4–5. Ruído de estática a cada troca de cena.
- No fecho, o drone cai para 25%, entra um boom subgrave com um agudo dissonante, e vem a voz.
- Volume final: −14 LUFS (`loudnorm`). A voz fica cerca de 10 dB acima da trilha.

### Exportação e publicação
- 1080x1920, 30 fps, H.264 com crf 25 e maxrate 9M, AAC 192k e `+faststart`.
- **Capa:** o quadro mais assustador **com a frase inteira na tela** (ep. 01: os olhos na cabine + "Não olhe para a cabine.").
- **Legenda:** `VAGA: {Cargo}, {turno} + {local}. {benefício irônico}. Início imediato.` → pergunta para comentários → hashtags (#terror #historiasdeterror #creepypasta #terrorbrasileiro #regras #suspense #medo).
- **Metricool:** marca 7988382, Instagram tipo REEL, `isAiGenerated: true`, capa via `videoCoverMilliseconds`. O vídeo precisa de um link público (Google Drive compartilhado ou arquivo no repositório).

### Checklist antes de entregar
- [ ] **Âncoras de palavra conferidas**: índice da palavra certa e frase certa. No ep. 01, três efeitos ficaram adiantados por erro de índice.
- [ ] Prévia de 6 a 8 quadros nos momentos mais cheios (`python3 render.py preview …`).
- [ ] Nenhuma frase cortada na capa; texto dentro da área segura.
- [ ] Duração entre 55 e 65 s; loudness em −14 LUFS.

---

## 3. Ideias para os próximos episódios
1. **Vigia noturno** de shopping fechado: as vitrines dos manequins.
2. **Recepcionista** de motel na beira da Fernão Dias: o quarto 7 que não existe no mapa.
3. **Cobrador** do último ônibus da linha 023: o passageiro que desce no ponto desativado.
4. **Zelador** de escola estadual nas férias: a chamada que alguém faz na sala 12.
5. **Operador de pedágio** na madrugada: o carro que passa toda noite sem motorista.
6. **Plantonista** de hospital antigo: o elevador que para no 4º andar interditado.
7. **Caseiro** de sítio em Minas: quem chama o seu nome do lado de fora da cerca.
8. **Faxineiro** de estação de metrô: o trem que chega depois do último.
9. **Operador de rádio** de estrada: o caminhoneiro que pede socorro de um km que não existe.
10. **Guarda** de cemitério municipal: as visitas fora do horário.

---

## 4. Padrão "imagens de IA" (a partir do ep. 01 refeito)
Em vez do cenário desenhado em código, cada frase tem uma imagem gerada por IA (16 por episódio, vertical 9:16, em `episodios/<ep>/imagens/NN.jpg`). O render aplica zoom lento, glitch nos cortes, legenda dourada em itálico, cartões de título ("REGRA N°x", "DIÁRIA R$ x") e moldura de TV antiga. O Claude escreve o roteiro e o `prompts.md`; você gera as imagens; o Claude renderiza com a voz do ElevenLabs. Trechos `[[entre colchetes]]` saem em voz demoníaca e em vermelho.

### Variantes (para intercalar e não ficar repetitivo)
Nem todo episódio precisa ser uma vaga de emprego. Mantendo o padrão de imagens, as 5 regras e a virada, alterne o *contexto*: **vaga de emprego** (diária ALTA) · **aluguel barato demais** ("Aluga-se… R$ 300 por mês", aviso do síndico) · outros: hospedagem, carona, pesquisa remunerada, herança de casa. O gancho é sempre um valor/benefício estranho no começo, e o fecho "Temos vagas" continua valendo (o prédio, a pousada, a casa também têm vagas).
