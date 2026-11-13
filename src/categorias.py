"""As categorias de rotulagem: a fonte única para quem rotula, para as regras e para a medição.

Cada avaliação recebe um motivo principal e a indicação de se a loja precisa
responder. Quando o texto traz mais de um problema, vale o que aparece
primeiro em `MOTIVOS`: a ordem é a de gravidade para o cliente. Definições e
exemplos em GUIA_DE_ROTULAGEM.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Motivo:
    codigo: str
    nome: str
    definicao: str


MOTIVOS: tuple[Motivo, ...] = (
    Motivo(
        "nao_recebido",
        "Não recebido",
        "O pedido não chegou até o momento da avaliação.",
    ),
    Motivo(
        "entrega_incompleta",
        "Entrega incompleta",
        "Chegou só parte do pedido: faltou item ou unidade.",
    ),
    Motivo(
        "produto_errado",
        "Produto errado",
        "Chegou diferente do pedido ou do anúncio: modelo, cor, tamanho, marca ou falsificado.",
    ),
    Motivo(
        "defeito_ou_avaria",
        "Defeito ou avaria",
        "Chegou quebrado, amassado, danificado, ou não funciona.",
    ),
    Motivo(
        "atraso",
        "Atraso",
        "Chegou, mas depois do prazo, ou o cliente reclama da demora.",
    ),
    Motivo(
        "qualidade_ruim",
        "Qualidade ruim",
        "É o produto pedido e funciona, mas a qualidade decepcionou.",
    ),
    Motivo(
        "atendimento",
        "Atendimento",
        "Problema com a loja: sem resposta, cancelamento, cobrança, troca ou devolução difícil.",
    ),
    Motivo(
        "elogio",
        "Elogio",
        "Avaliação positiva, sem reclamação.",
    ),
    Motivo(
        "outro",
        "Outro",
        "Neutra, sem informação suficiente ou fora das categorias acima.",
    ),
)

CODIGOS: tuple[str, ...] = tuple(motivo.codigo for motivo in MOTIVOS)

PRECISA_RESPOSTA = (
    "Sim quando o cliente tem um problema não resolvido que pede ação da loja: não recebeu, "
    "faltou item, veio errado ou com defeito, pede troca, devolução, reembolso ou contato. "
    "Não quando é só elogio, desabafo sobre algo já resolvido (como um atraso de entrega já "
    "feita) ou opinião sobre a qualidade sem pedido."
)
