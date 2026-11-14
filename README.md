# Classificador de avaliações de clientes

**No ar:** [classificador-avaliacoes.onrender.com](https://classificador-avaliacoes.onrender.com) (plano grátis: o primeiro acesso depois de um tempo parado leva cerca de 1 minuto).

[![CI](https://github.com/SudoMary/classificador-avaliacoes/actions/workflows/ci.yml/badge.svg)](https://github.com/SudoMary/classificador-avaliacoes/actions/workflows/ci.yml)

> Lê avaliações de clientes em português e diz o motivo de cada uma (atraso, defeito, produto errado...) e se a loja precisa responder. Tem conjunto de referência rotulado, medição com métricas por categoria, uma linha de base por regras (78,7% de acerto no teste) e um LLM grátis, via OpenRouter, que acerta 96,0%.

**Estado:** projeto concluído nesta versão (`v1.2.0`). A `v1.0.0` fechou com as regras, a `v1.1.0` acrescentou o classificador com LLM e a `v1.2.0` acrescenta o site, em que dá para testar os dois lado a lado. O que ficou de fora está em [Limitações e próximos passos](#limitações-e-próximos-passos).

## O problema

Uma loja grande recebe milhares de avaliações por mês, e ninguém lê todas. A nota em estrelas não ajuda a triar: uma nota 1 pode ser um pedido que nunca chegou, uma peça quebrada ou a cor errada, e cada caso vai para uma equipe diferente. Alguns pedem resposta hoje; outros são só desabafo.

O classificador responde, para cada avaliação, duas perguntas: **qual o motivo principal**, entre 9 categorias, e **a loja precisa responder?**

## Como funciona

```
olist_order_reviews_dataset.csv        99.224 avaliações reais (Kaggle)
  │
  ├─ src/amostra.py      tira as sem texto e as repetidas (sobram 40.950) e sorteia 40 de cada nota
  │    └─ dados/amostra.csv          200 avaliações: 50 de desenvolvimento + 150 de teste
  │
  ├─ src/rotular.py      rotulagem e revisão na linha de comando, seguindo o guia
  │    └─ dados/rotulos.csv          motivo, "precisa responder" e quem rotulou
  │
  └─ src/medir.py        roda um classificador num conjunto, mede e grava o relatório
       ├─ src/regras.py              classificador por palavras-chave
       ├─ src/llm.py                 classificador com LLM grátis (OpenRouter), em lotes e com cache
       ├─ src/medicao.py             acerto, precisão, revocação, F1 e matriz de confusão
       └─ resultados/                relatório em Markdown e cada previsão ao lado da referência

src/web.py              site: cola uma avaliação e vê regras e LLM lado a lado
  └─ src/pagina.py      exemplos, cartões e a tabela de resultados calculada de resultados/
```

| Módulo | O que faz |
|---|---|
| `src/categorias.py` | As 9 categorias, em ordem de gravidade, e a regra de "precisa responder". Fonte única para a rotulagem, as regras e a medição. |
| `src/amostra.py` | Lê o CSV da Olist, descarta texto vazio e `review_id` repetido, sorteia por nota com semente fixa e separa desenvolvimento de teste mantendo a proporção de notas. |
| `src/rotular.py` | Ferramenta de rotulagem: um rótulo por tecla, gravação a cada resposta (por arquivo temporário, para um Ctrl+C não corromper nada), retomada de onde parou, desfazer e modo de revisão. |
| `src/regras.py` | Normaliza o texto (minúsculas, sem acento, "n" e "ñ" por "não") e procura expressões regulares por motivo, na ordem de gravidade do guia. |
| `src/llm.py` | Manda o guia de rotulagem e 15 avaliações por requisição a um modelo grátis do OpenRouter, pede a resposta em JSON com esquema fixo e confere item por item. Guarda as respostas em cache (medir de novo não gasta cota) e tenta de novo quando o modelo grátis está sobrecarregado no fornecedor. |
| `src/medicao.py` | Métricas calculadas à mão, sem bibliotecas: precisão, revocação e F1 por categoria, F1 macro e matriz de confusão. |
| `src/medir.py` | Linha de comando que junta tudo; o classificador "maioria" aprende só com o desenvolvimento. |
| `src/web.py`, `src/pagina.py` | Site em FastAPI: regras e LLM lado a lado para a avaliação digitada, com limite diário próprio para o LLM e cache por texto; a tabela de resultados e os números de discordância são calculados dos arquivos de `resultados/`, para o site sempre bater com o repositório. |

**Stack:** Python 3.12; o classificador e a medição só com a biblioteca padrão (`csv`, `re`, `unicodedata`, `dataclasses`, `argparse`, `urllib`) e o site em FastAPI com Jinja2; API do OpenRouter com o modelo grátis Nemotron 3.5 Super, da NVIDIA, pytest (126 testes, nenhum chama a rede), ruff e GitHub Actions (CI em todo push e pull request).

## Resultados

Conjunto de teste: 150 avaliações, 30 de cada nota. Nenhuma delas foi usada para ajustar as regras.

| Classificador | Acerto do motivo | F1 macro do motivo | Acerto em "precisa responder" | F1 de "sim" |
|---|---|---|---|---|
| Sempre a classe mais comum | 41,3% | 0,06 | 65,3% | 0,00 |
| Regras por palavras-chave | 78,7% | 0,70 | 91,3% | 0,87 |
| LLM grátis (Nemotron 3.5 Super, via OpenRouter) | 96,0% | 0,95 | 95,3% | 0,94 |

O F1 macro dá o mesmo peso a cada categoria: é ele que mostra que "sempre elogio" acerta 41% sem entender nada. Relatórios completos, com a matriz de confusão e cada previsão ao lado da referência, em [`resultados/`](resultados/).

O que os números mostram:

- As regras vão bem onde o vocabulário é próprio: entrega incompleta (F1 0,88), elogio (0,91), atendimento (0,82), atraso e defeito (0,80).
- Erram onde é preciso interpretar: só 2 de 6 casos de produto errado e 4 de 9 de qualidade ruim foram reconhecidos; o resto virou "outro" ou "elogio".
- 4 das 23 entregas incompletas viraram "não recebido": o texto diz "não chegou" sobre uma parte do pedido.
- O LLM resolve justamente o que as regras não conseguem: acerta os 6 casos de produto errado e os 9 de qualidade ruim. Custo: US$ 0, com 14 requisições para as 200 avaliações e nenhuma resposta fora do esquema.

Cuidados ao ler:

- Categorias com menos de 10 avaliações mudam vários pontos com um único acerto ou erro.
- Os rótulos de referência são do Claude e ainda não foram revisados por uma pessoa.
- As regras também foram escritas pelo Claude, que leu as avaliações do teste ao rotular. Os ajustes vieram só dos erros do desenvolvimento, mas o número do teste pode estar um pouco otimista.
- O LLM medido (Nemotron, da NVIDIA) é de outra empresa que a do modelo que rotulou (Claude, da Anthropic), mas os dois são LLMs: parte da concordância pode vir de lerem o guia de forma parecida. A revisão humana é o que fecha essa dúvida.

## Decisões de projeto

- **Amostra com o mesmo número de cada nota.** Metade das avaliações com texto tem nota 5. Numa amostra proporcional, as reclamações, que são o que mais importa acertar, apareceriam pouco para medir. São 40 avaliações de cada nota, em ordem embaralhada, para a nota não puxar o julgamento de quem rotula.
- **Desenvolvimento separado do teste.** 50 avaliações servem para ajustar as regras olhando os erros; as outras 150 só medem o resultado final. Medir no mesmo conjunto usado para ajustar daria um número otimista: no desenvolvimento, as regras chegaram a 90%.
- **Um motivo principal, por ordem de gravidade.** Muitas avaliações trazem mais de um problema ("atrasou e veio quebrado"). Um rótulo só, decidido por uma ordem fixa, deixa a medição simples e os rótulos consistentes.
- **Guia de rotulagem com casos decididos.** O [guia](GUIA_DE_ROTULAGEM.md) define cada categoria com exemplos e registra os casos de fronteira decididos durante a rotulagem, para os próximos seguirem igual.
- **Linha de base antes de qualquer modelo.** Um classificador "sempre a classe mais comum" e um por regras dão o piso que qualquer modelo mais caro precisa superar para valer o custo.
- **LLM grátis, em lotes e com cache.** O plano grátis do OpenRouter dá 50 requisições por dia. Com 15 avaliações por requisição, as 200 cabem em 14; com o cache, medir de novo não gasta nada. O modelo recebe o mesmo guia que a referência seguiu, e a resposta é conferida item por item: o que vier fora do esquema conta como erro na medição, em vez de sumir.
- **Site com os dois lado a lado.** Quem visita testa a própria frase e vê onde as regras e o LLM concordam ou não. O LLM tem limite diário próprio (15 por dia), porque a cota grátis é dividida com outros usos da mesma chave; passado o limite, a página responde só com as regras.
- **Quem rotulou fica registrado.** Os 200 rótulos foram feitos pelo Claude, lendo cada avaliação e seguindo o guia, e a coluna `autor` diz isso. Medir um LLM contra rótulos do mesmo modelo o favoreceria; por isso existe `python -m src.rotular --revisar`, em que uma pessoa confere cada rótulo, e os relatórios dizem quantos foram conferidos.

## Limitações e próximos passos

- **Revisão humana dos rótulos:** pendente. A ferramenta de revisão está pronta (Enter confirma, um número corrige); depois dela, as medições são refeitas com `python -m src.medir`.
- **Conjunto pequeno:** 150 avaliações de teste dão números instáveis nas categorias pequenas. Uma amostra maior, ou uma segunda amostra só para teste, daria mais firmeza.
- **Regras não interpretam:** produto errado e qualidade ruim pedem entender o sentido, não só achar palavras.
- **Próximo passo:** um modelo pequeno em português (BERTimbau), treinado com os rótulos do LLM em milhares de avaliações e comparado com ele em acerto, custo e velocidade. As categorias, a medição e o conjunto de referência já servem para isso.

## Publicação

O site roda no Render como Web Service do plano grátis, com a configuração descrita no [`render.yaml`](render.yaml): build com `pip install -r requirements.txt`, início com `uvicorn src.web:app --host 0.0.0.0 --port $PORT`, health check em `/saude` e as variáveis `OPENROUTER_API_KEY` e `PYTHON_VERSION` (3.12.10). Sem a chave, o site funciona só com as regras. Cada merge na `main` é publicado sozinho.

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements-dev.txt

uvicorn src.web:app --reload      # site em http://127.0.0.1:8000
python -m src.medir regras        # mede as regras no teste (relatório em resultados/)
python -m src.medir maioria       # mede o "sempre a classe mais comum"
python -m src.medir llm           # mede o LLM grátis (copie .env.example para .env e ponha a chave)
python -m src.rotular --revisar   # confere os rótulos feitos pelo Claude
python -m src.rotular             # rotula o que faltar, uma por vez; pode parar e continuar
python -m src.amostra             # sorteia a amostra (já está em dados/amostra.csv)

pytest -q                                  # testes
ruff check . && ruff format --check .      # lint
```

Para sortear de novo, baixe o [dataset da Olist no Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) e coloque `olist_order_reviews_dataset.csv` em `dados/brutos/`.

## Dados e licença

O código está sob a licença MIT ([LICENSE](LICENSE)). As avaliações vêm do [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), publicado sob a licença [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). O arquivo original não está neste repositório; a amostra em `dados/` é derivada dele e segue a mesma licença. Os nomes de lojas nos textos já vêm anonimizados pela Olist.
