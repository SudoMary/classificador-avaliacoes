# Classificador de avaliações de clientes

[![CI](https://github.com/SudoMary/classificador-avaliacoes/actions/workflows/ci.yml/badge.svg)](https://github.com/SudoMary/classificador-avaliacoes/actions/workflows/ci.yml)

> Lê avaliações de clientes em português e diz o motivo de cada uma (atraso, defeito, produto errado...) e se a loja precisa responder. Compara regras simples, um LLM e um modelo pequeno treinado a partir dele, medindo acerto e custo de cada um.

## O problema

Uma loja grande recebe milhares de avaliações por mês, e ninguém lê todas. A nota em estrelas não ajuda a triar: uma nota 1 pode ser um pedido que nunca chegou, uma peça quebrada ou a cor errada, e cada caso vai para uma equipe diferente. Alguns pedem resposta hoje; outros são só desabafo.

O classificador responde, para cada avaliação, duas perguntas: **qual o motivo principal** e **a loja precisa responder?**

## Plano

1. **Conjunto de referência** *(rotulado; revisão humana em andamento)*: 200 avaliações rotuladas seguindo o [guia de rotulagem](GUIA_DE_ROTULAGEM.md). É a referência contra a qual tudo é medido. Veja abaixo quem fez os rótulos.
2. **Linha de base por regras**: palavras-chave e medição de acerto por categoria. É o número que os outros precisam superar.
3. **Classificador com LLM**: o Claude com saída estruturada, medido no mesmo conjunto, com custo por mil avaliações.
4. **Modelo pequeno**: um BERT em português (BERTimbau) treinado com os rótulos do LLM em milhares de avaliações. Comparação de acerto, custo e velocidade com o LLM; modelo publicado no Hugging Face e notebook no Kaggle.

## Como rodar

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements-dev.txt

python -m src.amostra             # sorteia as 200 avaliações (já está em dados/amostra.csv)
python -m src.rotular             # rotula à mão, uma por vez; pode parar e continuar
python -m src.rotular --revisar   # confere os rótulos feitos pelo Claude

pytest -q                                  # testes
ruff check . && ruff format --check .      # lint
```

Para sortear de novo, baixe o [dataset da Olist no Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) e coloque `olist_order_reviews_dataset.csv` em `dados/brutos/`.

## Decisões de projeto

- **Amostra com o mesmo número de cada nota.** Metade das avaliações com texto tem nota 5. Numa amostra proporcional, as reclamações, que são o que mais importa acertar, apareceriam pouco para medir. São 40 avaliações de cada nota, em ordem embaralhada, para a nota não puxar o julgamento de quem rotula.
- **Desenvolvimento separado do teste.** 50 avaliações servem para ajustar regras e prompts olhando os erros; as outras 150 só medem o resultado final. Medir no mesmo conjunto usado para ajustar daria um número otimista.
- **Um motivo principal, por ordem de gravidade.** Muitas avaliações trazem mais de um problema ("atrasou e veio quebrado"). Um rótulo só, decidido por uma ordem fixa, deixa a medição simples e os rótulos consistentes.
- **Categorias numa fonte única.** `src/categorias.py` alimenta a ferramenta de rotulagem, a medição e o prompt do LLM. Mudar uma definição muda em todos.
- **Rotulagem que não perde trabalho.** Cada rótulo é gravado na hora; dá para parar a qualquer momento e continuar de onde parou.
- **Quem rotulou fica registrado.** Os 200 rótulos de `dados/rotulos.csv` foram feitos pelo Claude, lendo cada avaliação e seguindo o guia, e a coluna `autor` diz isso (`claude`). Isso pesa na etapa 3: medir o Claude contra rótulos do próprio Claude favorece o Claude. Por isso existe `python -m src.rotular --revisar`, em que uma pessoa confere cada rótulo (Enter confirma, um número corrige) e o autor passa a `revisado`. Os relatórios dizem quantos rótulos do conjunto medido foram revisados.

## Dados e licença

O código está sob a licença MIT ([LICENSE](LICENSE)). As avaliações vêm do [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), publicado sob a licença [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). O arquivo original não está neste repositório; a amostra em `dados/` é derivada dele e segue a mesma licença. Os nomes de lojas nos textos já vêm anonimizados pela Olist.
