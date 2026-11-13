"""Ferramenta para rotular a amostra à mão, uma avaliação por vez.

Uso: python -m src.rotular

Para cada avaliação, pergunta o motivo principal (um número) e se a loja
precisa responder (s ou n). Cada rótulo é gravado na hora em
dados/rotulos.csv: dá para sair com "q" (ou Ctrl+C) e continuar depois de
onde parou. "v" refaz a avaliação anterior e "?" mostra as definições.
"""

from __future__ import annotations

import csv
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .amostra import AMOSTRA
from .categorias import MOTIVOS, PRECISA_RESPOSTA

ROTULOS = Path("dados/rotulos.csv")
COLUNAS = ("review_id", "motivo", "precisa_resposta")

_SAIR = "q"
_VOLTAR = "v"
_AJUDA = "?"


def rotular(
    amostra: list[dict[str, Any]],
    caminho: Path,
    *,
    entrada: Callable[[str], str] = input,
    saida: Callable[[str], None] = print,
) -> int:
    """Pergunta os rótulos que faltam e devolve quantas avaliações estão rotuladas."""
    rotulos = ler_rotulos(caminho)
    por_id = {avaliacao["review_id"]: avaliacao for avaliacao in amostra}
    fila = [avaliacao for avaliacao in amostra if avaliacao["review_id"] not in rotulos]

    while fila:
        atual = fila[0]
        saida(_cartao(atual, posicao=len(rotulos) + 1, total=len(amostra)))
        motivo = _perguntar_motivo(entrada, saida)
        if motivo == _SAIR:
            break
        if motivo == _VOLTAR:
            if not rotulos:
                saida("Não há avaliação anterior para refazer.")
                continue
            # A anterior é a última gravada, mesmo que tenha sido em outra sessão.
            anterior = list(rotulos)[-1]
            del rotulos[anterior]
            _gravar(rotulos, caminho)
            fila.insert(0, por_id[anterior])
            continue

        resposta = _perguntar_resposta(entrada, saida)
        if resposta == _SAIR:
            break
        if resposta == _VOLTAR:
            continue

        rotulos[atual["review_id"]] = {"motivo": motivo, "precisa_resposta": resposta}
        _gravar(rotulos, caminho)
        fila.pop(0)
    return len(rotulos)


def ler_rotulos(caminho: Path) -> dict[str, dict[str, str]]:
    """Rótulos já gravados, por ``review_id``, na ordem em que foram feitos."""
    if not caminho.exists():
        return {}
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return {
            linha["review_id"]: {
                "motivo": linha["motivo"],
                "precisa_resposta": linha["precisa_resposta"],
            }
            for linha in csv.DictReader(arquivo)
        }


def main() -> int:
    if not AMOSTRA.exists():
        print("Sorteie a amostra antes: python -m src.amostra", file=sys.stderr)
        return 1
    with AMOSTRA.open(encoding="utf-8", newline="") as arquivo:
        amostra = list(csv.DictReader(arquivo))
    try:
        total = rotular(amostra, ROTULOS, entrada=input, saida=print)
    except (KeyboardInterrupt, EOFError):
        # Tudo o que foi respondido já está gravado; só a avaliação atual se perde.
        print()
        total = len(ler_rotulos(ROTULOS))
    print(f"Rotuladas: {total} de {len(amostra)}. Os rótulos ficam em {ROTULOS}.")
    return 0


def _perguntar_motivo(entrada: Callable[[str], str], saida: Callable[[str], None]) -> str:
    while True:
        resposta = entrada(f"Motivo (1-{len(MOTIVOS)}, ? ajuda, v volta, q sai): ").strip().lower()
        if resposta in (_SAIR, _VOLTAR):
            return resposta
        if resposta == _AJUDA:
            saida(_definicoes())
            continue
        if resposta.isdigit() and 1 <= int(resposta) <= len(MOTIVOS):
            return MOTIVOS[int(resposta) - 1].codigo
        saida(f"Digite um número de 1 a {len(MOTIVOS)}.")


def _perguntar_resposta(entrada: Callable[[str], str], saida: Callable[[str], None]) -> str:
    while True:
        resposta = (
            entrada("A loja precisa responder? (s/n, ? ajuda, v volta ao motivo, q sai): ")
            .strip()
            .lower()
        )
        if resposta in (_SAIR, _VOLTAR):
            return resposta
        if resposta == _AJUDA:
            saida(PRECISA_RESPOSTA)
            continue
        if resposta in ("s", "n"):
            return "sim" if resposta == "s" else "nao"
        saida("Digite s ou n.")


def _cartao(avaliacao: dict[str, Any], *, posicao: int, total: int) -> str:
    linhas = ["", "-" * 72, f"Avaliação {posicao} de {total} · nota {avaliacao['nota']} de 5"]
    if avaliacao["titulo"]:
        linhas.append(f"Título: {avaliacao['titulo']}")
    linhas += [avaliacao["texto"], ""]
    opcoes = [f"{numero} {motivo.nome:<20}" for numero, motivo in enumerate(MOTIVOS, start=1)]
    for inicio in range(0, len(opcoes), 3):
        linhas.append(" " + " ".join(opcoes[inicio : inicio + 3]).rstrip())
    return "\n".join(linhas)


def _definicoes() -> str:
    return "\n".join(
        f"{numero} {motivo.nome}: {motivo.definicao}"
        for numero, motivo in enumerate(MOTIVOS, start=1)
    )


def _gravar(rotulos: dict[str, dict[str, str]], caminho: Path) -> None:
    """Regrava o arquivo inteiro por um temporário, para um Ctrl+C não deixá-lo pela metade."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(".tmp")
    with temporario.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        escritor.writeheader()
        for review_id, rotulo in rotulos.items():
            escritor.writerow({"review_id": review_id, **rotulo})
    temporario.replace(caminho)


if __name__ == "__main__":
    raise SystemExit(main())
