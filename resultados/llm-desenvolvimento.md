# LLM (nvidia/nemotron-3.5-super-vl:free) · conjunto de desenvolvimento

50 avaliações do conjunto de desenvolvimento.
Rótulos de referência: 0 conferidos por uma pessoa e 50 só do Claude.
Modelo grátis do OpenRouter: `nvidia/nemotron-3.5-super-vl:free`, custo US$ 0.
Requisições nesta execução: 4. Respostas reaproveitadas do cache: 0. Inválidas (contadas como erro): 0.

## Motivo principal

- Acerto: 96,0% (48 de 50)
- F1 macro: 0,93

| Motivo | Precisão | Revocação | F1 | Avaliações |
|---|---|---|---|---|
| Não recebido | 100,0% | 100,0% | 1,00 | 9 |
| Entrega incompleta | 100,0% | 100,0% | 1,00 | 1 |
| Produto errado | 100,0% | 100,0% | 1,00 | 4 |
| Defeito ou avaria | 75,0% | 100,0% | 0,86 | 3 |
| Atraso | 100,0% | 100,0% | 1,00 | 2 |
| Qualidade ruim | 100,0% | 75,0% | 0,86 | 4 |
| Atendimento | 100,0% | 100,0% | 1,00 | 5 |
| Elogio | 100,0% | 95,2% | 0,98 | 21 |
| Outro | 50,0% | 100,0% | 0,67 | 1 |

Com menos de 10 avaliações na referência, um único acerto ou erro muda muito o número: Não recebido, Entrega incompleta, Produto errado, Defeito ou avaria, Atraso, Qualidade ruim, Atendimento, Outro.

## Matriz de confusão

Linhas: a referência. Colunas: o que o classificador disse (pelo número do motivo).

| Referência | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| 1 Não recebido | 9 | · | · | · | · | · | · | · | · |
| 2 Entrega incompleta | · | 1 | · | · | · | · | · | · | · |
| 3 Produto errado | · | · | 4 | · | · | · | · | · | · |
| 4 Defeito ou avaria | · | · | · | 3 | · | · | · | · | · |
| 5 Atraso | · | · | · | · | 2 | · | · | · | · |
| 6 Qualidade ruim | · | · | · | 1 | · | 3 | · | · | · |
| 7 Atendimento | · | · | · | · | · | · | 5 | · | · |
| 8 Elogio | · | · | · | · | · | · | · | 20 | 1 |
| 9 Outro | · | · | · | · | · | · | · | · | 1 |

## A loja precisa responder?

- Acerto: 92,0% (46 de 50)
- Das que o classificador mandou responder, eram mesmo para responder (precisão): 81,8%
- Das que precisavam de resposta, quantas ele pegou (revocação): 100,0% de 18
- F1: 0,90
