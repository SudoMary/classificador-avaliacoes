"""O que a página do site mostra, já pronto para o template.

Decisões de apresentação (textos, exemplos, a história dos números) moram
aqui; os classificadores e as métricas continuam nos seus módulos. Os números
são calculados dos arquivos de previsões em resultados/, e não copiados, para
o site sempre bater com o repositório.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .categorias import CODIGOS, MOTIVOS
from .medicao import Resultado, Rotulo, duas_casas, medir, por_cento

# Frases inventadas, no estilo das avaliações: textos de clientes ficam fora do
# site. A primeira mostra a diferença: não tem a palavra "errado", e as regras erram.
EXEMPLOS: tuple[tuple[str, int], ...] = (
    ("Pedi azul e veio verde.", 2),
    ("Comprei três camisetas e só chegaram duas.", 2),
    ("Até hoje não recebi meu pedido.", 1),
    ("O tecido é bem fino, esperava mais.", 3),
)

# Arquivos de previsões gravados por `python -m src.medir`, na ordem da história.
CLASSIFICADORES: tuple[tuple[str, str], ...] = (
    ("maioria", "Sempre a classe mais comum"),
    ("regras", "Regras por palavras-chave"),
    ("llm", "LLM grátis"),
)

# Um bloco da barra de discordâncias só leva o número dentro se couber.
_FRACAO_MINIMA_PARA_ROTULO = 0.06
# No gráfico por motivo, o ganho do LLM aparece escrito só nas linhas que contam a história.
_LINHAS_COM_GANHO_ESCRITO = 3
# Sinal de menos tipográfico, mais legível que o hífen ao lado de números.
_MENOS = chr(0x2212)


def cartao(rotulo: Rotulo) -> dict[str, Any]:
    """Um resultado de classificador, com o nome e a definição do motivo."""
    motivo = MOTIVOS[CODIGOS.index(rotulo.motivo)]
    return {
        "codigo": motivo.codigo,
        "nome": motivo.nome,
        "definicao": motivo.definicao,
        "responder": rotulo.precisa_resposta == "sim",
    }


def historia(pasta: Path) -> dict[str, Any] | None:
    """Os números da seção "O que os números mostram", ou ``None`` se faltar arquivo."""
    previsoes: dict[str, list[dict[str, str]]] = {}
    for chave, _ in CLASSIFICADORES:
        caminho = pasta / f"{chave}-teste.csv"
        if not caminho.exists():
            return None
        with caminho.open(encoding="utf-8", newline="") as arquivo:
            previsoes[chave] = list(csv.DictReader(arquivo))
        if not previsoes[chave]:
            return None

    resultados = {chave: _medir(linhas) for chave, linhas in previsoes.items()}
    classificadores = [
        _classificador(chave, nome, resultados[chave]) for chave, nome in CLASSIFICADORES
    ]
    por_chave = {c["chave"]: c for c in classificadores}
    return {
        "total": resultados["llm"].total,
        "classificadores": classificadores,
        "maioria": por_chave["maioria"],
        "regras": por_chave["regras"],
        "llm": por_chave["llm"],
        "por_motivo": _por_motivo(resultados["regras"], resultados["llm"]),
        "discordancias": _discordancias(previsoes["regras"], previsoes["llm"]),
    }


def _medir(linhas: list[dict[str, str]]) -> Resultado:
    return medir(
        [Rotulo(p["motivo_referencia"], p["resposta_referencia"]) for p in linhas],
        [Rotulo(p["motivo_previsto"], p["resposta_prevista"]) for p in linhas],
    )


def _classificador(chave: str, nome: str, resultado: Resultado) -> dict[str, Any]:
    return {
        "chave": chave,
        "nome": nome,
        "fracao": f"{resultado.acerto_motivo:.4f}",
        "acerto": por_cento(resultado.acerto_motivo),
        "acerto_curto": f"{round(resultado.acerto_motivo * 100)}%",
        "f1": duas_casas(resultado.f1_macro_motivo),
        "resposta": por_cento(resultado.acerto_resposta),
        "destaque": chave == "llm",
    }


def _por_motivo(regras: Resultado, llm: Resultado) -> list[dict[str, Any]]:
    """F1 de regras e LLM por motivo, do maior ganho do LLM para o menor."""
    nomes = {motivo.codigo: motivo.nome for motivo in MOTIVOS}
    linhas = []
    for codigo in CODIGOS:
        if codigo not in regras.por_motivo or codigo not in llm.por_motivo:
            continue
        f1_regras = regras.por_motivo[codigo].f1
        f1_llm = llm.por_motivo[codigo].f1
        linhas.append(
            {
                "nome": nomes[codigo],
                "avaliacoes": llm.por_motivo[codigo].suporte,
                "regras": f"{f1_regras:.4f}",
                "llm": f"{f1_llm:.4f}",
                "regras_texto": duas_casas(f1_regras),
                "llm_texto": duas_casas(f1_llm),
                "diferenca": f1_llm - f1_regras,
                "ganho": f"{'+' if f1_llm >= f1_regras else _MENOS}"
                f"{duas_casas(abs(f1_llm - f1_regras))}",
            }
        )
    linhas.sort(key=lambda linha: (-linha["diferenca"], linha["nome"]))
    for posicao, linha in enumerate(linhas):
        linha["ganho_escrito"] = posicao < _LINHAS_COM_GANHO_ESCRITO
    return linhas


def _discordancias(
    regras: list[dict[str, str]], llm: list[dict[str, str]]
) -> dict[str, Any] | None:
    """Quando regras e LLM deram motivos diferentes, quantas vezes cada um acertou."""
    por_llm = {p["review_id"]: p for p in llm}
    casos = [
        (previsao, por_llm[previsao["review_id"]])
        for previsao in regras
        if previsao["review_id"] in por_llm
        and previsao["motivo_previsto"] != por_llm[previsao["review_id"]]["motivo_previsto"]
    ]
    if not casos:
        return None
    total = len(casos)
    acertos_llm = sum(m["acertou_motivo"] == "sim" for _, m in casos)
    acertos_regras = sum(r["acertou_motivo"] == "sim" for r, _ in casos)
    # Motivos diferentes não podem estar os dois certos: o resto errou nos dois.
    nenhum = total - acertos_llm - acertos_regras
    segmentos = [
        ("llm", "O LLM acertou", acertos_llm),
        ("regras", "As regras acertaram", acertos_regras),
        ("nenhum", "Nenhum acertou", nenhum),
    ]
    return {
        "total": total,
        "llm": acertos_llm,
        "regras": acertos_regras,
        "nenhum": nenhum,
        "segmentos": [
            {
                "chave": chave,
                "nome": nome,
                "quantidade": quantidade,
                "rotulo_visivel": quantidade / total >= _FRACAO_MINIMA_PARA_ROTULO,
            }
            for chave, nome, quantidade in segmentos
            if quantidade
        ],
    }
