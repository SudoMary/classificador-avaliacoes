# Regras por palavras-chave · conjunto de teste

150 avaliações do conjunto de teste.
Rótulos de referência: 0 conferidos por uma pessoa e 150 só do Claude.

## Motivo principal

- Acerto: 78,7% (118 de 150)
- F1 macro: 0,70

| Motivo | Precisão | Revocação | F1 | Avaliações |
|---|---|---|---|---|
| Não recebido | 66,7% | 71,4% | 0,69 | 14 |
| Entrega incompleta | 95,0% | 82,6% | 0,88 | 23 |
| Produto errado | 100,0% | 33,3% | 0,50 | 6 |
| Defeito ou avaria | 85,7% | 75,0% | 0,80 | 8 |
| Atraso | 88,9% | 72,7% | 0,80 | 11 |
| Qualidade ruim | 80,0% | 44,4% | 0,57 | 9 |
| Atendimento | 87,5% | 77,8% | 0,82 | 9 |
| Elogio | 87,9% | 93,5% | 0,91 | 62 |
| Outro | 22,2% | 50,0% | 0,31 | 8 |

Com menos de 10 avaliações na referência, um único acerto ou erro muda muito o número: Produto errado, Defeito ou avaria, Qualidade ruim, Atendimento, Outro.

## Matriz de confusão

Linhas: a referência. Colunas: o que o classificador disse (pelo número do motivo).

| Referência | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| 1 Não recebido | 10 | · | · | 1 | · | · | 1 | · | 2 |
| 2 Entrega incompleta | 4 | 19 | · | · | · | · | · | · | · |
| 3 Produto errado | 1 | · | 2 | · | · | · | · | 1 | 2 |
| 4 Defeito ou avaria | · | · | · | 6 | · | · | · | · | 2 |
| 5 Atraso | · | · | · | · | 8 | · | · | 1 | 2 |
| 6 Qualidade ruim | · | 1 | · | · | · | 4 | · | 1 | 3 |
| 7 Atendimento | · | · | · | · | · | 1 | 7 | 1 | · |
| 8 Elogio | · | · | · | · | 1 | · | · | 58 | 3 |
| 9 Outro | · | · | · | · | · | · | · | 4 | 4 |

## A loja precisa responder?

- Acerto: 91,3% (137 de 150)
- Das que o classificador mandou responder, eram mesmo para responder (precisão): 89,8%
- Das que precisavam de resposta, quantas ele pegou (revocação): 84,6% de 52
- F1: 0,87
