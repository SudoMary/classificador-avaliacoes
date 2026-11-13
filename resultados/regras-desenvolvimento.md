# Regras por palavras-chave · conjunto de desenvolvimento

50 avaliações do conjunto de desenvolvimento.
Rótulos de referência: 0 conferidos por uma pessoa e 50 só do Claude.

## Motivo principal

- Acerto: 90,0% (45 de 50)
- F1 macro: 0,82

| Motivo | Precisão | Revocação | F1 | Avaliações |
|---|---|---|---|---|
| Não recebido | 90,0% | 100,0% | 0,95 | 9 |
| Entrega incompleta | 100,0% | 100,0% | 1,00 | 1 |
| Produto errado | 100,0% | 75,0% | 0,86 | 4 |
| Defeito ou avaria | 100,0% | 100,0% | 1,00 | 3 |
| Atraso | 100,0% | 50,0% | 0,67 | 2 |
| Qualidade ruim | 66,7% | 50,0% | 0,57 | 4 |
| Atendimento | 100,0% | 80,0% | 0,89 | 5 |
| Elogio | 95,5% | 100,0% | 0,98 | 21 |
| Outro | 33,3% | 100,0% | 0,50 | 1 |

Com menos de 10 avaliações na referência, um único acerto ou erro muda muito o número: Não recebido, Entrega incompleta, Produto errado, Defeito ou avaria, Atraso, Qualidade ruim, Atendimento, Outro.

## Matriz de confusão

Linhas: a referência. Colunas: o que o classificador disse (pelo número do motivo).

| Referência | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| 1 Não recebido | 9 | · | · | · | · | · | · | · | · |
| 2 Entrega incompleta | · | 1 | · | · | · | · | · | · | · |
| 3 Produto errado | 1 | · | 3 | · | · | · | · | · | · |
| 4 Defeito ou avaria | · | · | · | 3 | · | · | · | · | · |
| 5 Atraso | · | · | · | · | 1 | · | · | · | 1 |
| 6 Qualidade ruim | · | · | · | · | · | 2 | · | 1 | 1 |
| 7 Atendimento | · | · | · | · | · | 1 | 4 | · | · |
| 8 Elogio | · | · | · | · | · | · | · | 21 | · |
| 9 Outro | · | · | · | · | · | · | · | · | 1 |

## A loja precisa responder?

- Acerto: 96,0% (48 de 50)
- Das que o classificador mandou responder, eram mesmo para responder (precisão): 90,0%
- Das que precisavam de resposta, quantas ele pegou (revocação): 100,0% de 18
- F1: 0,95
