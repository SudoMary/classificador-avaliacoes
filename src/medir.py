"""Mede um classificador contra os rótulos de referência e grava o relatório.

Uso: python -m src.medir <classificador> [--conjunto teste|desenvolvimento|todos]

Classificadores:
- maioria: sempre a resposta mais comum no conjunto de desenvolvimento. Mostra
  quanto se acerta sem entender nada; todo classificador precisa superá-lo.
- regras: palavras-chave (src/regras.py).

O relatório vai para resultados/<classificador>-<conjunto>.md e cada previsão,
ao lado da referência, para resultados/<classificador>-<conjunto>.csv, que é
onde se olham os erros.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .amostra import AMOSTRA
from .medicao import Rotulo, medir, relatorio
from .regras import classificar as classificar_por_regras
from .rotular import CLAUDE, ROTULOS, ler_rotulos

RESULTADOS = Path("resultados")
NOMES = {"maioria": "Classe mais comum", "regras": "Regras por palavras-chave"}

Classificador = Callable[..., Rotulo]


def main(argumentos: list[str] | None = None) -> int:
    args = _interpretar(argumentos)
    with AMOSTRA.open(encoding="utf-8", newline="") as arquivo:
        amostra = list(csv.DictReader(arquivo))
    rotulos = ler_rotulos(ROTULOS)
    faltando = [a["review_id"] for a in amostra if a["review_id"] not in rotulos]
    if faltando:
        plural = "avaliação" if len(faltando) == 1 else "avaliações"
        print(
            f"Falta rótulo para {len(faltando)} {plural}. Termine com: python -m src.rotular",
            file=sys.stderr,
        )
        return 1

    medidas = [a for a in amostra if args.conjunto in ("todos", a["conjunto"])]
    classificar = _classificador(args.classificador, amostra, rotulos)
    previsoes = [
        classificar(titulo=a["titulo"], texto=a["texto"], nota=int(a["nota"])) for a in medidas
    ]
    referencias = [_rotulo(rotulos[a["review_id"]]) for a in medidas]
    resultado = medir(referencias, previsoes)

    autores = Counter(rotulos[a["review_id"]]["autor"] for a in medidas)
    so_do_claude = autores[CLAUDE]
    notas = [
        f"{len(medidas)} avaliações do conjunto de {args.conjunto}.",
        f"Rótulos de referência: {len(medidas) - so_do_claude} conferidos por uma pessoa e "
        f"{so_do_claude} só do Claude.",
    ]
    nome = f"{args.classificador}-{args.conjunto}"
    texto = relatorio(
        resultado,
        titulo=f"{NOMES[args.classificador]} · conjunto de {args.conjunto}",
        notas=notas,
    )
    RESULTADOS.mkdir(exist_ok=True)
    (RESULTADOS / f"{nome}.md").write_text(texto, encoding="utf-8", newline="\n")
    _gravar_previsoes(RESULTADOS / f"{nome}.csv", medidas, referencias, previsoes)
    print(texto)
    return 0


def _classificador(
    nome: str, amostra: list[dict[str, Any]], rotulos: dict[str, dict[str, str]]
) -> Classificador:
    if nome == "regras":
        return classificar_por_regras
    # A maioria vem só do desenvolvimento: aprender com o teste seria olhar a resposta.
    desenvolvimento = [
        rotulos[a["review_id"]] for a in amostra if a["conjunto"] == "desenvolvimento"
    ]
    motivo = Counter(r["motivo"] for r in desenvolvimento).most_common(1)[0][0]
    resposta = Counter(r["precisa_resposta"] for r in desenvolvimento).most_common(1)[0][0]
    return lambda **_: Rotulo(motivo, resposta)


def _rotulo(rotulo: dict[str, str]) -> Rotulo:
    return Rotulo(motivo=rotulo["motivo"], precisa_resposta=rotulo["precisa_resposta"])


def _gravar_previsoes(
    destino: Path,
    medidas: list[dict[str, Any]],
    referencias: list[Rotulo],
    previsoes: list[Rotulo],
) -> None:
    colunas = (
        "review_id",
        "nota",
        "titulo",
        "texto",
        "motivo_referencia",
        "motivo_previsto",
        "acertou_motivo",
        "resposta_referencia",
        "resposta_prevista",
    )
    with destino.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas, lineterminator="\n")
        escritor.writeheader()
        for avaliacao, referencia, previsao in zip(medidas, referencias, previsoes, strict=True):
            escritor.writerow(
                {
                    "review_id": avaliacao["review_id"],
                    "nota": avaliacao["nota"],
                    "titulo": avaliacao["titulo"],
                    "texto": avaliacao["texto"],
                    "motivo_referencia": referencia.motivo,
                    "motivo_previsto": previsao.motivo,
                    "acertou_motivo": "sim" if referencia.motivo == previsao.motivo else "nao",
                    "resposta_referencia": referencia.precisa_resposta,
                    "resposta_prevista": previsao.precisa_resposta,
                }
            )


def _interpretar(argumentos: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m src.medir", description="Mede um classificador contra a referência."
    )
    parser.add_argument("classificador", choices=sorted(NOMES))
    parser.add_argument(
        "--conjunto", choices=("teste", "desenvolvimento", "todos"), default="teste"
    )
    return parser.parse_args(argumentos)


if __name__ == "__main__":
    raise SystemExit(main())
