"""Testes do comando de medição (src/medir.py), com arquivos pequenos numa pasta temporária."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.amostra import gravar
from src.medir import main

AMOSTRA = [
    {"review_id": "d1", "conjunto": "desenvolvimento", "nota": 2, "titulo": "", "texto": "Atrasou"},
    {"review_id": "d2", "conjunto": "desenvolvimento", "nota": 2, "titulo": "", "texto": "Demorou"},
    {"review_id": "t1", "conjunto": "teste", "nota": 1, "titulo": "", "texto": "Veio quebrado"},
    {"review_id": "t2", "conjunto": "teste", "nota": 5, "titulo": "", "texto": "Ótimo produto"},
]
ROTULOS = [
    ("d1", "atraso", "nao", "claude"),
    ("d2", "atraso", "nao", "claude"),
    ("t1", "defeito_ou_avaria", "sim", "revisado"),
    ("t2", "elogio", "nao", "claude"),
]


@pytest.fixture
def pasta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    gravar(AMOSTRA, Path("dados/amostra.csv"))
    _gravar_rotulos(ROTULOS)
    return tmp_path


def _gravar_rotulos(linhas: list[tuple[str, str, str, str]]) -> None:
    with Path("dados/rotulos.csv").open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo)
        escritor.writerow(["review_id", "motivo", "precisa_resposta", "autor"])
        escritor.writerows(linhas)


def test_regras_no_teste_grava_relatorio_e_previsoes(
    pasta: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["regras"]) == 0

    relatorio = Path("resultados/regras-teste.md").read_text(encoding="utf-8")
    assert relatorio.startswith("# Regras por palavras-chave · conjunto de teste")
    assert "Acerto: 100,0% (2 de 2)" in relatorio
    assert "1 conferidos por uma pessoa e 1 só do Claude" in relatorio
    assert relatorio in capsys.readouterr().out
    with Path("resultados/regras-teste.csv").open(encoding="utf-8", newline="") as arquivo:
        previsoes = list(csv.DictReader(arquivo))
    assert [(p["review_id"], p["motivo_previsto"], p["acertou_motivo"]) for p in previsoes] == [
        ("t1", "defeito_ou_avaria", "sim"),
        ("t2", "elogio", "sim"),
    ]


def test_maioria_aprende_so_com_o_desenvolvimento(pasta: Path) -> None:
    # No desenvolvimento só há atraso; no teste não há nenhum.
    assert main(["maioria"]) == 0

    with Path("resultados/maioria-teste.csv").open(encoding="utf-8", newline="") as arquivo:
        assert {p["motivo_previsto"] for p in csv.DictReader(arquivo)} == {"atraso"}


def test_mede_o_conjunto_escolhido(pasta: Path) -> None:
    assert main(["regras", "--conjunto", "desenvolvimento"]) == 0

    assert Path("resultados/regras-desenvolvimento.md").exists()


def test_rotulo_faltando_impede_a_medicao(pasta: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _gravar_rotulos(ROTULOS[:3])

    assert main(["regras"]) == 1
    assert "Falta rótulo para 1 avaliação" in capsys.readouterr().err
