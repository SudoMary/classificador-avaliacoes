"""Testes da ferramenta de rotulagem (src/rotular.py).

A pessoa que rotula é simulada por uma fila de respostas. Uma pergunta além
da fila estoura `IndexError` e reprova o teste.
"""

from __future__ import annotations

import csv
from collections.abc import Callable
from pathlib import Path

import pytest

from src.amostra import gravar
from src.categorias import PRECISA_RESPOSTA
from src.rotular import ler_rotulos, main, rotular

AMOSTRA = [
    {"review_id": "r1", "conjunto": "teste", "nota": "2", "titulo": "", "texto": "Veio quebrado."},
    {"review_id": "r2", "conjunto": "teste", "nota": "5", "titulo": "Top", "texto": "Adorei."},
]


def _pessoa(*respostas: str) -> Callable[[str], str]:
    fila = list(respostas)
    return lambda _pergunta: fila.pop(0)


class Tela:
    """Guarda tudo o que a ferramenta mostrou."""

    def __init__(self) -> None:
        self.linhas: list[str] = []

    def __call__(self, texto: str = "") -> None:
        self.linhas.append(texto)

    @property
    def texto(self) -> str:
        return "\n".join(self.linhas)


def _rotular(caminho: Path, *respostas: str, amostra: list[dict] | None = None) -> Tela:
    tela = Tela()
    rotular(amostra or AMOSTRA, caminho, entrada=_pessoa(*respostas), saida=tela)
    return tela


def _gravados(caminho: Path) -> list[tuple[str, str, str]]:
    with caminho.open(encoding="utf-8", newline="") as arquivo:
        return [
            (linha["review_id"], linha["motivo"], linha["precisa_resposta"])
            for linha in csv.DictReader(arquivo)
        ]


class TestRotular:
    def test_grava_motivo_e_resposta_de_cada_avaliacao(self, tmp_path: Path) -> None:
        caminho = tmp_path / "rotulos.csv"

        tela = _rotular(caminho, "4", "s", "8", "n")

        assert _gravados(caminho) == [
            ("r1", "defeito_ou_avaria", "sim"),
            ("r2", "elogio", "nao"),
        ]
        assert "Veio quebrado." in tela.texto
        assert "Avaliação 1 de 2" in tela.texto

    def test_continua_de_onde_parou(self, tmp_path: Path) -> None:
        caminho = tmp_path / "rotulos.csv"
        _rotular(caminho, "4", "s", "q")

        tela = _rotular(caminho, "8", "n")

        assert "Veio quebrado." not in tela.texto
        assert "Avaliação 2 de 2" in tela.texto
        assert [linha[0] for linha in _gravados(caminho)] == ["r1", "r2"]

    def test_resposta_invalida_pergunta_de_novo(self, tmp_path: Path) -> None:
        caminho = tmp_path / "rotulos.csv"

        tela = _rotular(caminho, "0", "x", "10", "4", "talvez", "s", "q")

        assert _gravados(caminho) == [("r1", "defeito_ou_avaria", "sim")]
        assert "Digite um número de 1 a 9." in tela.texto
        assert "Digite s ou n." in tela.texto

    def test_q_sai_sem_gravar_a_avaliacao_atual(self, tmp_path: Path) -> None:
        caminho = tmp_path / "rotulos.csv"

        _rotular(caminho, "4", "q")

        assert ler_rotulos(caminho) == {}

    def test_v_refaz_a_avaliacao_anterior(self, tmp_path: Path) -> None:
        caminho = tmp_path / "rotulos.csv"

        _rotular(caminho, "4", "s", "v", "3", "n", "8", "n")

        assert _gravados(caminho) == [("r1", "produto_errado", "nao"), ("r2", "elogio", "nao")]

    def test_v_refaz_tambem_a_ultima_da_sessao_anterior(self, tmp_path: Path) -> None:
        caminho = tmp_path / "rotulos.csv"
        _rotular(caminho, "4", "s", "q")

        _rotular(caminho, "v", "3", "s", "q")

        assert _gravados(caminho) == [("r1", "produto_errado", "sim")]

    def test_v_sem_anterior_avisa(self, tmp_path: Path) -> None:
        caminho = tmp_path / "rotulos.csv"

        tela = _rotular(caminho, "v", "q")

        assert "Não há avaliação anterior" in tela.texto

    def test_v_na_segunda_pergunta_volta_ao_motivo(self, tmp_path: Path) -> None:
        caminho = tmp_path / "rotulos.csv"

        _rotular(caminho, "4", "v", "3", "s", "q")

        assert _gravados(caminho) == [("r1", "produto_errado", "sim")]

    def test_interrogacao_mostra_as_definicoes(self, tmp_path: Path) -> None:
        caminho = tmp_path / "rotulos.csv"

        tela = _rotular(caminho, "?", "4", "?", "s", "q")

        assert "Chegou quebrado, amassado, danificado, ou não funciona." in tela.texto
        assert PRECISA_RESPOSTA in tela.texto

    def test_devolve_quantas_estao_rotuladas(self, tmp_path: Path) -> None:
        caminho = tmp_path / "rotulos.csv"

        total = rotular(AMOSTRA, caminho, entrada=_pessoa("4", "s", "q"), saida=Tela())

        assert total == 1


class TestMain:
    def test_sem_amostra_explica_o_que_fazer(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)

        assert main() == 1
        assert "python -m src.amostra" in capsys.readouterr().err

    def test_rotula_e_mostra_o_total(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        gravar(AMOSTRA, Path("dados/amostra.csv"))
        monkeypatch.setattr("builtins.input", _pessoa("4", "s", "q"))

        assert main() == 0
        assert "Rotuladas: 1 de 2" in capsys.readouterr().out

    def test_ctrl_c_para_sem_perder_o_que_foi_gravado(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.chdir(tmp_path)
        gravar(AMOSTRA, Path("dados/amostra.csv"))
        respostas = iter(["4", "s"])

        def pessoa(_pergunta: str) -> str:
            try:
                return next(respostas)
            except StopIteration:
                raise KeyboardInterrupt from None

        monkeypatch.setattr("builtins.input", pessoa)

        assert main() == 0
        assert "Rotuladas: 1 de 2" in capsys.readouterr().out
