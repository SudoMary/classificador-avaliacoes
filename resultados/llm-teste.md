# LLM (nvidia/nemotron-3.5-super-vl:free) · conjunto de teste

150 avaliações do conjunto de teste.
Rótulos de referência: 0 conferidos por uma pessoa e 150 só do Claude.
Modelo grátis do OpenRouter: `nvidia/nemotron-3.5-super-vl:free`, custo US$ 0.
Requisições nesta execução: 9. Respostas reaproveitadas do cache: 15. Inválidas (contadas como erro): 0.

## Motivo principal

- Acerto: 96,0% (144 de 150)
- F1 macro: 0,95

| Motivo | Precisão | Revocação | F1 | Avaliações |
|---|---|---|---|---|
| Não recebido | 92,9% | 92,9% | 0,93 | 14 |
| Entrega incompleta | 100,0% | 95,7% | 0,98 | 23 |
| Produto errado | 100,0% | 100,0% | 1,00 | 6 |
| Defeito ou avaria | 100,0% | 100,0% | 1,00 | 8 |
| Atraso | 100,0% | 90,9% | 0,95 | 11 |
| Qualidade ruim | 100,0% | 100,0% | 1,00 | 9 |
| Atendimento | 100,0% | 88,9% | 0,94 | 9 |
| Elogio | 98,4% | 96,8% | 0,98 | 62 |
| Outro | 66,7% | 100,0% | 0,80 | 8 |

Com menos de 10 avaliações na referência, um único acerto ou erro muda muito o número: Produto errado, Defeito ou avaria, Qualidade ruim, Atendimento, Outro.

## Matriz de confusão

Linhas: a referência. Colunas: o que o classificador disse (pelo número do motivo).

| Referência | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|
| 1 Não recebido | 13 | · | · | · | · | · | · | · | 1 |
| 2 Entrega incompleta | 1 | 22 | · | · | · | · | · | · | · |
| 3 Produto errado | · | · | 6 | · | · | · | · | · | · |
| 4 Defeito ou avaria | · | · | · | 8 | · | · | · | · | · |
| 5 Atraso | · | · | · | · | 10 | · | · | 1 | · |
| 6 Qualidade ruim | · | · | · | · | · | 9 | · | · | · |
| 7 Atendimento | · | · | · | · | · | · | 8 | · | 1 |
| 8 Elogio | · | · | · | · | · | · | · | 60 | 2 |
| 9 Outro | · | · | · | · | · | · | · | · | 8 |

## A loja precisa responder?

- Acerto: 95,3% (143 de 150)
- Das que o classificador mandou responder, eram mesmo para responder (precisão): 89,5%
- Das que precisavam de resposta, quantas ele pegou (revocação): 98,1% de 52
- F1: 0,94
