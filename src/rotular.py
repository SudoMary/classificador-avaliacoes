"""Ferramenta para rotular a amostra à mão, uma avaliação por vez.

Uso:
    python -m src.rotular              rotula as avaliações que faltam
    python -m src.rotular --revisar    confere os rótulos feitos pelo Claude

Para cada avaliação, pergunta o motivo principal (um número) e se a loja
precisa responder (s ou n). Cada rótulo é gravado na hora em
dados/rotulos.csv: dá para sair com "q" (ou Ctrl+C) e continuar depois de
onde parou. "v" volta à avaliação anterior e "?" mostra as definições.

Cada rótulo guarda o autor: "pessoa" (feito na ferramenta), "claude" (feito
pelo modelo) ou "revisado" (feito pelo modelo e conferido por uma pessoa).
Rótulo do Claude sem revisão favorece o próprio Claude quando ele for medido
como classificador; a revisão existe para isso.
"""

from __future__ import annotations

import csv
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .amostra import AMOSTRA
from .categorias import CODIGOS, MOTIVOS, PRECISA_RESPOSTA

ROTULOS = Path("dados/rotulos.csv")
COLUNAS = ("review_id", "motivo", "precisa_resposta", "autor")

PESSOA = "pessoa"
CLAUDE = "claude"
REVISADO = "revisado"

_SAIR = "q"
_VOLTAR = "v"
_AJUDA = "?"
_CONFIRMAR = ""


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
        saida(_cartao(atual, f"Avaliação {len(rotulos) + 1} de {len(amostra)}"))
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

        rotulos[atual["review_id"]] = {
            "motivo": motivo,
            "precisa_resposta": resposta,
            "autor": PESSOA,
        }
        _gravar(rotulos, caminho)
        fila.pop(0)
    return len(rotulos)


def revisar(
    amostra: list[dict[str, Any]],
    caminho: Path,
    *,
    entrada: Callable[[str], str] = input,
    saida: Callable[[str], None] = print,
) -> int:
    """Passa pelos rótulos do Claude ainda não conferidos; devolve quantos já foram revisados.

    Enter confirma o rótulo; um número corrige o motivo e pergunta de novo a
    resposta. Confirmado ou corrigido, o autor passa a ser "revisado".
    """
    rotulos = ler_rotulos(caminho)
    pendentes = [
        avaliacao
        for avaliacao in amostra
        if rotulos.get(avaliacao["review_id"], {}).get("autor") == CLAUDE
    ]
    posicao = 0
    while posicao < len(pendentes):
        atual = pendentes[posicao]
        rotulo = rotulos[atual["review_id"]]
        saida(_cartao(atual, f"Revisão {posicao + 1} de {len(pendentes)}"))
        saida(f"Rótulo do Claude: {_descrever(rotulo)}")
        escolha = _perguntar_motivo(entrada, saida, aceita_confirmar=True)
        if escolha == _SAIR:
            break
        if escolha == _VOLTAR:
            if posicao == 0:
                saida("Não há avaliação anterior nesta revisão.")
            posicao = max(posicao - 1, 0)
            continue
        if escolha == _CONFIRMAR:
            motivo, resposta = rotulo["motivo"], rotulo["precisa_resposta"]
        else:
            motivo, resposta = escolha, _perguntar_resposta(entrada, saida)
            if resposta == _SAIR:
                break
            if resposta == _VOLTAR:
                continue
        rotulos[atual["review_id"]] = {
            "motivo": motivo,
            "precisa_resposta": resposta,
            "autor": REVISADO,
        }
        _gravar(rotulos, caminho)
        posicao += 1
    return sum(1 for rotulo in rotulos.values() if rotulo["autor"] == REVISADO)


def ler_rotulos(caminho: Path) -> dict[str, dict[str, str]]:
    """Rótulos já gravados, por ``review_id``, na ordem em que foram feitos."""
    if not caminho.exists():
        return {}
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return {
            linha["review_id"]: {
                "motivo": linha["motivo"],
                "precisa_resposta": linha["precisa_resposta"],
                "autor": linha.get("autor") or PESSOA,
            }
            for linha in csv.DictReader(arquivo)
        }


def main(argumentos: list[str] | None = None) -> int:
    argumentos = sys.argv[1:] if argumentos is None else argumentos
    if not AMOSTRA.exists():
        print("Sorteie a amostra antes: python -m src.amostra", file=sys.stderr)
        return 1
    with AMOSTRA.open(encoding="utf-8", newline="") as arquivo:
        amostra = list(csv.DictReader(arquivo))
    modo_revisao = "--revisar" in argumentos
    try:
        if modo_revisao:
            revisar(amostra, ROTULOS, entrada=input, saida=print)
        else:
            rotular(amostra, ROTULOS, entrada=input, saida=print)
    except (KeyboardInterrupt, EOFError):
        # Tudo o que foi respondido já está gravado; só a avaliação atual se perde.
        print()
    rotulos = ler_rotulos(ROTULOS)
    if modo_revisao:
        do_claude = sum(1 for rotulo in rotulos.values() if rotulo["autor"] in (CLAUDE, REVISADO))
        revisados = sum(1 for rotulo in rotulos.values() if rotulo["autor"] == REVISADO)
        print(f"Revisadas por uma pessoa: {revisados} de {do_claude} rotuladas pelo Claude.")
    else:
        print(f"Rotuladas: {len(rotulos)} de {len(amostra)}. Os rótulos ficam em {ROTULOS}.")
    return 0


def _perguntar_motivo(
    entrada: Callable[[str], str],
    saida: Callable[[str], None],
    *,
    aceita_confirmar: bool = False,
) -> str:
    pergunta = (
        f"Enter confirma; para corrigir, o motivo (1-{len(MOTIVOS)}). ? ajuda, v volta, q sai: "
        if aceita_confirmar
        else f"Motivo (1-{len(MOTIVOS)}, ? ajuda, v volta, q sai): "
    )
    while True:
        resposta = entrada(pergunta).strip().lower()
        if resposta in (_SAIR, _VOLTAR) or (aceita_confirmar and resposta == _CONFIRMAR):
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


def _cartao(avaliacao: dict[str, Any], cabecalho: str) -> str:
    linhas = ["", "-" * 72, f"{cabecalho} · nota {avaliacao['nota']} de 5"]
    if avaliacao["titulo"]:
        linhas.append(f"Título: {avaliacao['titulo']}")
    linhas += [avaliacao["texto"], ""]
    opcoes = [f"{numero} {motivo.nome:<20}" for numero, motivo in enumerate(MOTIVOS, start=1)]
    for inicio in range(0, len(opcoes), 3):
        linhas.append(" " + " ".join(opcoes[inicio : inicio + 3]).rstrip())
    return "\n".join(linhas)


def _descrever(rotulo: dict[str, str]) -> str:
    numero = CODIGOS.index(rotulo["motivo"]) + 1
    resposta = "sim" if rotulo["precisa_resposta"] == "sim" else "não"
    return f"{numero} {MOTIVOS[numero - 1].nome} · responder: {resposta}"


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
