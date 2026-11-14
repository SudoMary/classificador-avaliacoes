"""O que a página do site mostra, já pronto para o template.

Decisões de apresentação (textos, exemplos, tabela de resultados) moram aqui;
os classificadores e as métricas continuam nos seus módulos.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .categorias import CODIGOS, MOTIVOS
from .medicao import Rotulo, duas_casas, medir, por_cento

# Frases inventadas, no estilo das avaliações: textos de clientes ficam fora do site.
EXEMPLOS: tuple[tuple[str, int], ...] = (
    ("Comprei três camisetas e só chegaram duas.", 2),
    ("Pedi azul e veio verde.", 2),
    ("A tampa veio rachada, quero trocar.", 1),
    ("Até hoje não recebi meu pedido.", 1),
    ("Chegou antes do prazo, recomendo!", 5),
    ("O tecido é bem fino, esperava mais.", 3),
)

# Arquivos de previsões gravados por `python -m src.medir`, na ordem da tabela.
MEDIDOS: tuple[tuple[str, str], ...] = (
    ("maioria-teste.csv", "Sempre a classe mais comum"),
    ("regras-teste.csv", "Regras por palavras-chave"),
    ("llm-teste.csv", "LLM grátis (Nemotron 3.5 Super)"),
)


def cartao(rotulo: Rotulo) -> dict[str, Any]:
    """Um resultado de classificador, com o nome e a definição do motivo."""
    numero = CODIGOS.index(rotulo.motivo)
    motivo = MOTIVOS[numero]
    return {
        "codigo": motivo.codigo,
        "nome": motivo.nome,
        "definicao": motivo.definicao,
        "responder": rotulo.precisa_resposta == "sim",
    }


def resultados_medidos(pasta: Path) -> list[dict[str, str]]:
    """Os números do conjunto de teste, calculados dos arquivos de previsões.

    Calculados aqui, e não copiados, para o site sempre bater com o repositório.
    Arquivo que não existe fica de fora da tabela.
    """
    linhas = []
    for arquivo, nome in MEDIDOS:
        caminho = pasta / arquivo
        if not caminho.exists():
            continue
        with caminho.open(encoding="utf-8", newline="") as aberto:
            previsoes = list(csv.DictReader(aberto))
        if not previsoes:
            continue
        resultado = medir(
            [Rotulo(p["motivo_referencia"], p["resposta_referencia"]) for p in previsoes],
            [Rotulo(p["motivo_previsto"], p["resposta_prevista"]) for p in previsoes],
        )
        linhas.append(
            {
                "nome": nome,
                "acerto_motivo": por_cento(resultado.acerto_motivo),
                "largura": f"{resultado.acerto_motivo * 100:.1f}",
                "f1_macro": duas_casas(resultado.f1_macro_motivo),
                "acerto_resposta": por_cento(resultado.acerto_resposta),
                "total": str(resultado.total),
            }
        )
    return linhas


def discordancias(pasta: Path) -> dict[str, int] | None:
    """Quando regras e LLM discordaram no teste, quantas vezes cada um acertou."""
    regras, llm = pasta / "regras-teste.csv", pasta / "llm-teste.csv"
    if not (regras.exists() and llm.exists()):
        return None
    with (
        regras.open(encoding="utf-8", newline="") as a,
        llm.open(encoding="utf-8", newline="") as b,
    ):
        por_regras = {p["review_id"]: p for p in csv.DictReader(a)}
        por_llm = {p["review_id"]: p for p in csv.DictReader(b)}
    casos = [
        review_id
        for review_id, previsao in por_regras.items()
        if review_id in por_llm
        and previsao["motivo_previsto"] != por_llm[review_id]["motivo_previsto"]
    ]
    return {
        "total": len(casos),
        "llm": sum(por_llm[c]["acertou_motivo"] == "sim" for c in casos),
        "regras": sum(por_regras[c]["acertou_motivo"] == "sim" for c in casos),
    }
