"""Métricas: quanto as previsões de um classificador batem com a referência.

Para o motivo, o acerto geral engana quando as categorias têm tamanhos muito
diferentes: um classificador que sempre diz "elogio" acerta 40% da amostra
sem entender nada. Por isso vêm também a precisão, a revocação e o F1 de cada
categoria, e o F1 macro, que é a média simples dos F1: cada categoria pesa o
mesmo, grande ou pequena.

- Precisão: das vezes em que o classificador disse X, quantas eram X.
- Revocação: das avaliações que eram X, quantas ele chamou de X.
- F1: média harmônica das duas; só é alto quando as duas são.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .categorias import CODIGOS, MOTIVOS

# Abaixo disso, uma categoria muda vários pontos com um único acerto ou erro.
POUCAS_AVALIACOES = 10


@dataclass(frozen=True)
class Rotulo:
    """O que se diz de uma avaliação: na referência ou na previsão."""

    motivo: str
    precisa_resposta: str  # "sim" ou "nao"


@dataclass(frozen=True)
class Metricas:
    precisao: float
    revocacao: float
    f1: float
    suporte: int  # quantas avaliações da referência são desta categoria


@dataclass(frozen=True)
class Resultado:
    total: int
    acertos_motivo: int
    acerto_motivo: float
    f1_macro_motivo: float
    por_motivo: dict[str, Metricas]
    matriz: dict[tuple[str, str], int]  # (referência, previsão) -> quantas
    acertos_resposta: int
    acerto_resposta: float
    resposta_sim: Metricas


def medir(referencias: list[Rotulo], previsoes: list[Rotulo]) -> Resultado:
    """Compara as previsões com a referência, avaliação por avaliação."""
    if len(referencias) != len(previsoes) or not referencias:
        raise ValueError("Referência e previsões precisam ter o mesmo tamanho, maior que zero.")
    total = len(referencias)
    motivos_ref = [rotulo.motivo for rotulo in referencias]
    motivos_prev = [rotulo.motivo for rotulo in previsoes]
    # Conta também categoria prevista que não existe na referência: é erro e pesa na média.
    presentes = [codigo for codigo in CODIGOS if codigo in set(motivos_ref) | set(motivos_prev)]
    por_motivo = {codigo: _metricas(codigo, motivos_ref, motivos_prev) for codigo in presentes}

    respostas_ref = [rotulo.precisa_resposta for rotulo in referencias]
    respostas_prev = [rotulo.precisa_resposta for rotulo in previsoes]
    acertos_motivo = sum(r == p for r, p in zip(motivos_ref, motivos_prev, strict=True))
    acertos_resposta = sum(r == p for r, p in zip(respostas_ref, respostas_prev, strict=True))
    return Resultado(
        total=total,
        acertos_motivo=acertos_motivo,
        acerto_motivo=acertos_motivo / total,
        f1_macro_motivo=sum(m.f1 for m in por_motivo.values()) / len(por_motivo),
        por_motivo=por_motivo,
        matriz=dict(Counter(zip(motivos_ref, motivos_prev, strict=True))),
        acertos_resposta=acertos_resposta,
        acerto_resposta=acertos_resposta / total,
        resposta_sim=_metricas("sim", respostas_ref, respostas_prev),
    )


def relatorio(resultado: Resultado, *, titulo: str, notas: list[str]) -> str:
    """O resultado em Markdown, para ler no terminal ou no GitHub."""
    nomes = {motivo.codigo: motivo.nome for motivo in MOTIVOS}
    linhas = [f"# {titulo}", ""]
    linhas += [*notas, ""] if notas else []
    linhas += [
        "## Motivo principal",
        "",
        f"- Acerto: {_pct(resultado.acerto_motivo)} "
        f"({resultado.acertos_motivo} de {resultado.total})",
        f"- F1 macro: {_dec(resultado.f1_macro_motivo)}",
        "",
        "| Motivo | Precisão | Revocação | F1 | Avaliações |",
        "|---|---|---|---|---|",
    ]
    for codigo, m in resultado.por_motivo.items():
        linhas.append(
            f"| {nomes[codigo]} | {_pct(m.precisao)} | {_pct(m.revocacao)} | {_dec(m.f1)} "
            f"| {m.suporte} |"
        )
    poucas = [
        nomes[c] for c, m in resultado.por_motivo.items() if 0 < m.suporte < POUCAS_AVALIACOES
    ]
    if poucas:
        linhas += [
            "",
            f"Com menos de {POUCAS_AVALIACOES} avaliações na referência, um único acerto ou "
            f"erro muda muito o número: {', '.join(poucas)}.",
        ]
    linhas += ["", *_matriz(resultado, nomes), "", *_resposta(resultado)]
    return "\n".join(linhas) + "\n"


def _metricas(classe: str, referencias: list[str], previsoes: list[str]) -> Metricas:
    pares = list(zip(referencias, previsoes, strict=True))
    acertos = sum(r == classe and p == classe for r, p in pares)
    previstos = sum(p == classe for _, p in pares)
    reais = sum(r == classe for r, _ in pares)
    # Sem previsão (ou sem caso real) da classe, a métrica é 0, e não divisão por zero.
    precisao = acertos / previstos if previstos else 0.0
    revocacao = acertos / reais if reais else 0.0
    f1 = 2 * precisao * revocacao / (precisao + revocacao) if precisao + revocacao else 0.0
    return Metricas(precisao=precisao, revocacao=revocacao, f1=f1, suporte=reais)


def _matriz(resultado: Resultado, nomes: dict[str, str]) -> list[str]:
    codigos = list(resultado.por_motivo)
    numeros = {codigo: CODIGOS.index(codigo) + 1 for codigo in codigos}
    linhas = [
        "## Matriz de confusão",
        "",
        "Linhas: a referência. Colunas: o que o classificador disse (pelo número do motivo).",
        "",
        "| Referência | " + " | ".join(str(numeros[c]) for c in codigos) + " |",
        "|---|" + "---|" * len(codigos),
    ]
    for ref in codigos:
        celulas = [str(resultado.matriz.get((ref, prev), 0) or "·") for prev in codigos]
        linhas.append(f"| {numeros[ref]} {nomes[ref]} | " + " | ".join(celulas) + " |")
    return linhas


def _resposta(resultado: Resultado) -> list[str]:
    sim = resultado.resposta_sim
    return [
        "## A loja precisa responder?",
        "",
        f"- Acerto: {_pct(resultado.acerto_resposta)} "
        f"({resultado.acertos_resposta} de {resultado.total})",
        f"- Das que o classificador mandou responder, eram mesmo para responder "
        f"(precisão): {_pct(sim.precisao)}",
        f"- Das que precisavam de resposta, quantas ele pegou (revocação): {_pct(sim.revocacao)}"
        f" de {sim.suporte}",
        f"- F1: {_dec(sim.f1)}",
    ]


def _pct(valor: float) -> str:
    return f"{valor * 100:.1f}%".replace(".", ",")


def _dec(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")
