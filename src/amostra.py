"""Sorteia as avaliações que serão rotuladas à mão.

Lê o arquivo de avaliações da Olist, descarta as sem texto e as repetidas e
sorteia o mesmo número de avaliações de cada nota, de 1 a 5. Nos dados, a
nota 5 é metade das avaliações com texto; sorteando por nota, as reclamações,
que são o que o classificador mais precisa acertar, aparecem o bastante para
medir.

A amostra se divide em dois conjuntos. O de desenvolvimento serve para
ajustar regras e prompts olhando os erros; o de teste só mede o resultado
final. Medir no mesmo conjunto usado para ajustar daria um número otimista.

Uso: python -m src.amostra [caminho do CSV de avaliações da Olist]
"""

from __future__ import annotations

import csv
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

POR_NOTA = 40
DESENVOLVIMENTO_POR_NOTA = 10
SEMENTE = 2026

ORIGEM_PADRAO = Path("dados/brutos/olist_order_reviews_dataset.csv")
AMOSTRA = Path("dados/amostra.csv")
COLUNAS = ("review_id", "conjunto", "nota", "titulo", "texto")


@dataclass(frozen=True)
class Avaliacao:
    review_id: str
    nota: int
    titulo: str
    texto: str


def ler_avaliacoes(caminho: Path) -> list[Avaliacao]:
    """Avaliações com texto, uma por ``review_id``, na ordem do arquivo."""
    avaliacoes: list[Avaliacao] = []
    vistas: set[str] = set()
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        for linha in csv.DictReader(arquivo):
            texto = _limpar(linha["review_comment_message"])
            # Na Olist, a mesma avaliação se repete para cada pedido ligado a ela.
            if not texto or linha["review_id"] in vistas:
                continue
            vistas.add(linha["review_id"])
            avaliacoes.append(
                Avaliacao(
                    review_id=linha["review_id"],
                    nota=int(linha["review_score"]),
                    titulo=_limpar(linha["review_comment_title"]),
                    texto=texto,
                )
            )
    return avaliacoes


def sortear(
    avaliacoes: list[Avaliacao],
    *,
    por_nota: int = POR_NOTA,
    desenvolvimento_por_nota: int = DESENVOLVIMENTO_POR_NOTA,
    semente: int = SEMENTE,
) -> list[dict[str, Any]]:
    """Sorteia ``por_nota`` avaliações de cada nota e embaralha o resultado.

    De cada nota, ``desenvolvimento_por_nota`` vão para o desenvolvimento e o
    resto para o teste: os dois conjuntos têm todas as notas na mesma proporção.
    A mesma semente sobre o mesmo arquivo dá sempre o mesmo sorteio.
    """
    gerador = random.Random(semente)
    linhas: list[dict[str, Any]] = []
    for nota in range(1, 6):
        grupo = [avaliacao for avaliacao in avaliacoes if avaliacao.nota == nota]
        if len(grupo) < por_nota:
            raise ValueError(
                f"Só há {len(grupo)} avaliações com nota {nota}; são precisas {por_nota}."
            )
        for posicao, avaliacao in enumerate(gerador.sample(grupo, por_nota)):
            conjunto = "desenvolvimento" if posicao < desenvolvimento_por_nota else "teste"
            linhas.append(
                {
                    "review_id": avaliacao.review_id,
                    "conjunto": conjunto,
                    "nota": avaliacao.nota,
                    "titulo": avaliacao.titulo,
                    "texto": avaliacao.texto,
                }
            )
    # Misturadas, as notas não puxam o julgamento de quem rotula numa direção.
    gerador.shuffle(linhas)
    return linhas


def gravar(linhas: list[dict[str, Any]], destino: Path) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        escritor.writeheader()
        escritor.writerows(linhas)


def main(argumentos: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argumentos is None else argumentos
    origem = Path(argumentos[0]) if argumentos else ORIGEM_PADRAO
    if AMOSTRA.exists():
        print(
            f"{AMOSTRA} já existe. Sortear de novo desligaria os rótulos já feitos; "
            "apague o arquivo antes, se for isso mesmo que você quer.",
            file=sys.stderr,
        )
        return 1
    linhas = sortear(ler_avaliacoes(origem))
    gravar(linhas, AMOSTRA)
    print(f"{len(linhas)} avaliações sorteadas em {AMOSTRA}.")
    return 0


def _limpar(texto: str | None) -> str:
    """Junta quebras de linha e espaços repetidos."""
    return " ".join((texto or "").split())


if __name__ == "__main__":
    raise SystemExit(main())
