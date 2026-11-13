"""Linha de base: classificador por palavras-chave, sem aprendizado de máquina.

É o número que o LLM e o modelo pequeno precisam superar para valer o custo.
As palavras vêm do guia de rotulagem e do vocabulário comum de reclamação; os
ajustes foram feitos só olhando os erros no conjunto de desenvolvimento. O
conjunto de teste serve apenas para medir.

Como no guia, os motivos são procurados por ordem de gravidade e o primeiro
que aparece vence. Elogio só vale quando nenhuma reclamação aparece.
"""

from __future__ import annotations

import re
import unicodedata

from .medicao import Rotulo

# Parece reclamação, mas não é: apagado antes da busca.
_NAO_E_RECLAMACAO = re.compile(
    r"\b(bom|boa|otimo|otima|excelente|top|dez) atendimento\b"
    r"|\batendimento (foi )?(bom|otimo|excelente|top|dez|nota 10)\b"
)

# Entrega incompleta vem antes de não recebido: "só chegou um" também diz
# que o outro "não chegou".
_PADROES: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (motivo, re.compile("|".join(padroes)))
    for motivo, padroes in (
        (
            "entrega_incompleta",
            (
                r"\b(so|somente|apenas) (chegou|chegaram|veio|vieram|recebi|recebemos"
                r"|foi entregue|foram entregues|entregaram)\b",
                r"\b(chegou|chegaram|veio|vieram|recebi|entregaram) (so|somente|apenas)\b",
                r"\bfalt(ou|ando|aram|am)\b",
                r"\bveio sem\b",
                r"\bmetade\b",
                r"\bentrega parcial\b",
                r"\bnao (veio|vieram|chegou|chegaram) (o|a|os|as) (outr|restante|demais|segund)",
            ),
        ),
        (
            "nao_recebido",
            (
                # "Não recebi resposta" é sobre a loja, não sobre o pedido.
                r"\bnao (recebi|recebemos)\b(?! (nenhum |nenhuma )?(feedback|contato|resposta"
                r"|retorno|e-?mail|nota|informac))",
                r"\bnao (chegou|chegaram|foi entregue|foram entregues|entregaram)\b",
                r"\b(aguardando|esperando|aguardo) (a |o |minha |meu |pela |pelo )?"
                r"(entrega|encomenda|pedido|produto|mercadoria)",
                r"\bnunca chegou\b",
                r"\bextravi",
            ),
        ),
        (
            "produto_errado",
            (
                r"\berrad[oa]s?\b",
                r"\bdiferente",
                r"\btrocad[oa]s?\b",
                r"\bveio outr",
                r"\boutr[oa] (cor|modelo|produto|coisa|tamanho)\b",
                r"\bfalsificad",
                r"\breplica\b",
                r"\bnao (e )?original\b",
                r"\bgeneric[oa]\b",
                r"\benganos[oa]\b",
            ),
        ),
        (
            "defeito_ou_avaria",
            (
                r"\bdefeit",
                r"\bquebr(ad|ou)",
                r"\bdanificad",
                r"\bavariad",
                r"\bamassad",
                r"\b(rachad|trincad|riscad|furad|estragad)",
                r"\bnao funciona",
                r"\bparou de funcionar\b",
                r"\bnao liga\b",
            ),
        ),
        (
            "atraso",
            (
                r"\batras",
                r"\bdemor",
                r"\b(fora|depois|alem) do prazo\b",
                r"\bpassou do prazo\b",
                r"\bprazo (muito )?longo\b",
            ),
        ),
        (
            "qualidade_ruim",
            (
                r"\b(baixa|pessima|ma) qualidade\b",
                r"\bqualidade (ruim|baixa|pessima|inferior)\b",
                r"\b(frac[oa]|fragil|vagabund)",
                r"\bnao gostei\b",
                r"\besperava mais\b",
                r"\bpoderia ser melhor\b",
                r"\bnao (foi|era) (o|bem o) que eu esperava\b",
                r"\bdecepcion",
                r"\bruim\b",
            ),
        ),
        (
            "atendimento",
            (
                r"\bnota fiscal\b",
                r"\bcancel",
                r"\b(estorno|reembols|dinheiro de volta)",
                r"\b(sem|nenhuma|nao (tive|obtive|recebi)) (resposta|retorno|contato)\b",
                r"\bninguem (responde|respondeu)\b",
                r"\bnao respond",
                r"\batendimento\b",
                r"\b(indisponivel|estoque)\b",
                r"\bcobr(ad|anca|aram)",
            ),
        ),
    )
)

_ELOGIO = re.compile(
    r"\b(otim|excelent|recomend|perfeit|lind|satisfeit|maravilh|parabens)"
    r"|\b(adorei|amei|gostei|bom|boa|top|show|valeu|ok)\b"
    r"|\b(no|dentro do|antes do) prazo\b|\brapid|\btudo (certo|certinho)\b"
)
_NEGACAO_DE_ELOGIO = re.compile(r"\bnao (recomendo|gostei|amei|indico|e (bom|boa|otim))")

_PRECISAM_DE_RESPOSTA = {"nao_recebido", "entrega_incompleta", "produto_errado", "defeito_ou_avaria"}
_JA_RESOLVIDO = re.compile(r"\b(trocou|trocaram|resolv(eu|eram|ido|ida)|corrigi(u|ram|do))\b")
_PEDIDO = re.compile(
    r"\?|\b(quero|gostaria|aguardo|aguardando|preciso|o que (eu )?faco)\b"
    r"|\b(dinheiro de volta|reembols|estorno)"
    r"|\bnao (veio|recebi) (a )?nota fiscal\b"
)


def classificar(*, titulo: str, texto: str, nota: int) -> Rotulo:
    """Motivo principal e se a loja precisa responder, pelas palavras do texto."""
    normal = _NAO_E_RECLAMACAO.sub(" ", _normalizar(f"{titulo} {texto}"))
    motivo = _motivo(normal, nota)
    return Rotulo(motivo=motivo, precisa_resposta=_resposta(motivo, normal))


def _motivo(normal: str, nota: int) -> str:
    for motivo, padrao in _PADROES:
        if padrao.search(normal):
            return motivo
    if _ELOGIO.search(normal) and not _NEGACAO_DE_ELOGIO.search(normal):
        return "elogio"
    # Sem pista no texto, a nota decide.
    return "elogio" if nota >= 4 else "outro"


def _resposta(motivo: str, normal: str) -> str:
    if motivo in _PRECISAM_DE_RESPOSTA:
        return "nao" if _JA_RESOLVIDO.search(normal) else "sim"
    return "sim" if _PEDIDO.search(normal) else "nao"


def _normalizar(texto: str) -> str:
    """Minúsculas, sem acento e com espaços simples."""
    decomposto = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in decomposto if not unicodedata.combining(c))
    return " ".join(sem_acento.casefold().split())
