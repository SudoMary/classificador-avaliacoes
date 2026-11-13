"""Testes do sorteio da amostra (src/amostra.py), com arquivos no formato da Olist."""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

import pytest

from src.amostra import Avaliacao, gravar, ler_avaliacoes, main, sortear

CABECALHO = (
    "review_id",
    "order_id",
    "review_score",
    "review_comment_title",
    "review_comment_message",
    "review_creation_date",
    "review_answer_timestamp",
)


def _escrever_olist(caminho: Path, linhas: list[tuple[str, int, str, str]]) -> Path:
    """Cada linha é (review_id, nota, título, texto), no formato do arquivo da Olist."""
    with caminho.open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.writer(arquivo, quoting=csv.QUOTE_NONNUMERIC)
        escritor.writerow(CABECALHO)
        for review_id, nota, titulo, texto in linhas:
            escritor.writerow([review_id, "pedido", nota, titulo, texto, "2018-01-01 00:00:00", ""])
    return caminho


def _avaliacoes(por_nota: int) -> list[Avaliacao]:
    return [
        Avaliacao(review_id=f"r{nota}-{i}", nota=nota, titulo="", texto=f"texto {nota} {i}")
        for nota in range(1, 6)
        for i in range(por_nota)
    ]


class TestLerAvaliacoes:
    def test_descarta_as_sem_texto(self, tmp_path: Path) -> None:
        caminho = _escrever_olist(
            tmp_path / "olist.csv",
            [("a", 5, "", "Ótimo"), ("b", 4, "Bom", ""), ("c", 1, "", "   ")],
        )

        assert [a.review_id for a in ler_avaliacoes(caminho)] == ["a"]

    def test_descarta_review_id_repetido(self, tmp_path: Path) -> None:
        # Na Olist, a mesma avaliação aparece uma vez para cada pedido ligado a ela.
        caminho = _escrever_olist(
            tmp_path / "olist.csv", [("a", 5, "", "Ótimo"), ("a", 5, "", "Ótimo")]
        )

        assert len(ler_avaliacoes(caminho)) == 1

    def test_junta_quebras_de_linha_e_espacos(self, tmp_path: Path) -> None:
        caminho = _escrever_olist(
            tmp_path / "olist.csv", [("a", 2, " Ruim\r\n", "Chegou\r\n  quebrado. ")]
        )

        [avaliacao] = ler_avaliacoes(caminho)

        assert avaliacao == Avaliacao(
            review_id="a", nota=2, titulo="Ruim", texto="Chegou quebrado."
        )


class TestSortear:
    def test_mesmo_numero_de_cada_nota(self) -> None:
        sorteadas = sortear(_avaliacoes(10), por_nota=4, desenvolvimento_por_nota=1)

        assert Counter(linha["nota"] for linha in sorteadas) == {n: 4 for n in range(1, 6)}

    def test_desenvolvimento_e_teste_tem_todas_as_notas(self) -> None:
        sorteadas = sortear(_avaliacoes(10), por_nota=4, desenvolvimento_por_nota=1)

        desenvolvimento = [linha for linha in sorteadas if linha["conjunto"] == "desenvolvimento"]
        teste = [linha for linha in sorteadas if linha["conjunto"] == "teste"]
        assert Counter(linha["nota"] for linha in desenvolvimento) == {n: 1 for n in range(1, 6)}
        assert Counter(linha["nota"] for linha in teste) == {n: 3 for n in range(1, 6)}

    def test_mesma_semente_mesmo_sorteio(self) -> None:
        primeira = sortear(_avaliacoes(10), por_nota=4, desenvolvimento_por_nota=1, semente=7)
        segunda = sortear(_avaliacoes(10), por_nota=4, desenvolvimento_por_nota=1, semente=7)

        assert primeira == segunda

    def test_notas_vem_misturadas_para_quem_rotula(self) -> None:
        # Rotular 40 notas 1 seguidas puxaria o julgamento para a reclamação.
        sorteadas = sortear(_avaliacoes(10), por_nota=4, desenvolvimento_por_nota=1)

        notas = [linha["nota"] for linha in sorteadas]
        assert notas != sorted(notas)

    def test_avaliacoes_insuficientes_levanta_erro(self) -> None:
        with pytest.raises(ValueError, match="nota 1"):
            sortear(_avaliacoes(3), por_nota=4, desenvolvimento_por_nota=1)


class TestGravar:
    def test_main_grava_a_amostra_e_nao_sobrescreve(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        linhas = [(f"r{n}-{i}", n, "", f"texto {n} {i}") for n in range(1, 6) for i in range(50)]
        origem = _escrever_olist(tmp_path / "olist.csv", linhas)
        monkeypatch.chdir(tmp_path)

        assert main([str(origem)]) == 0
        with open("dados/amostra.csv", encoding="utf-8", newline="") as arquivo:
            gravadas = list(csv.DictReader(arquivo))
        assert len(gravadas) == 200
        assert set(gravadas[0]) == {"review_id", "conjunto", "nota", "titulo", "texto"}
        assert Counter(linha["conjunto"] for linha in gravadas) == {
            "desenvolvimento": 50,
            "teste": 150,
        }

        # Sortear de novo apagaria a ligação com os rótulos já feitos.
        assert main([str(origem)]) == 1
        assert "já existe" in capsys.readouterr().err

    def test_gravar_cria_a_pasta(self, tmp_path: Path) -> None:
        destino = tmp_path / "nova" / "amostra.csv"

        gravar(sortear(_avaliacoes(4), por_nota=2, desenvolvimento_por_nota=1), destino)

        assert destino.exists()
