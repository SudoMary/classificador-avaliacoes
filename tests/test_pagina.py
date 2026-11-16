"""Testes dos números da página (src/pagina.py).

Uma parte usa os arquivos reais de resultados/, para a história do site bater
com o repositório; outra usa arquivos pequenos, com as contas feitas à mão.
"""

from __future__ import annotations

import csv
from pathlib import Path

from src.medicao import Rotulo
from src.pagina import cartao, historia

RESULTADOS = Path(__file__).resolve().parent.parent / "resultados"
COLUNAS = (
    "review_id",
    "motivo_referencia",
    "motivo_previsto",
    "acertou_motivo",
    "resposta_referencia",
    "resposta_prevista",
)


def _gravar(pasta: Path, nome: str, linhas: list[tuple[str, str, str]]) -> None:
    """Cada linha é (review_id, motivo da referência, motivo previsto)."""
    with (pasta / f"{nome}-teste.csv").open("w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS)
        escritor.writeheader()
        for review_id, referencia, previsto in linhas:
            escritor.writerow(
                {
                    "review_id": review_id,
                    "motivo_referencia": referencia,
                    "motivo_previsto": previsto,
                    "acertou_motivo": "sim" if referencia == previsto else "nao",
                    "resposta_referencia": "nao",
                    "resposta_prevista": "nao",
                }
            )


class TestHistoriaComOsResultadosDoRepositorio:
    def test_manchete_e_classificadores(self) -> None:
        h = historia(RESULTADOS)

        assert h is not None
        assert h["total"] == 150
        assert [c["chave"] for c in h["classificadores"]] == ["maioria", "regras", "llm"]
        assert [c["destaque"] for c in h["classificadores"]] == [False, False, True]
        assert (h["llm"]["acerto_curto"], h["regras"]["acerto_curto"]) == ("96%", "79%")
        assert h["llm"]["acerto"] == "96,0%"

    def test_motivos_do_maior_ganho_do_llm_para_o_menor(self) -> None:
        h = historia(RESULTADOS)

        assert h is not None
        motivos = h["por_motivo"]
        assert len(motivos) == 9
        assert motivos[0]["nome"] == "Produto errado"
        assert motivos[0]["ganho"] == "+0,50"
        diferencas = [m["diferenca"] for m in motivos]
        assert diferencas == sorted(diferencas, reverse=True)
        # O ganho aparece escrito só nas três linhas que contam a história.
        assert [m["ganho_escrito"] for m in motivos] == [True] * 3 + [False] * 6

    def test_discordancias(self) -> None:
        h = historia(RESULTADOS)

        assert h is not None
        d = h["discordancias"]
        assert (d["total"], d["llm"], d["regras"], d["nenhum"]) == (33, 29, 3, 1)
        assert [(s["chave"], s["rotulo_visivel"]) for s in d["segmentos"]] == [
            ("llm", True),
            ("regras", True),
            ("nenhum", False),
        ]


class TestHistoriaComArquivosPequenos:
    def _tres_arquivos(self, pasta: Path, regras: list, llm: list) -> None:
        _gravar(pasta, "maioria", [(i, r, "elogio") for i, r, _ in regras])
        _gravar(pasta, "regras", regras)
        _gravar(pasta, "llm", llm)

    def test_arquivo_faltando_ou_vazio_tira_a_historia_da_pagina(self, tmp_path: Path) -> None:
        assert historia(tmp_path) is None

        _gravar(tmp_path, "maioria", [])
        _gravar(tmp_path, "regras", [("a", "elogio", "elogio")])
        _gravar(tmp_path, "llm", [("a", "elogio", "elogio")])
        assert historia(tmp_path) is None

    def test_sem_discordancia_nao_ha_barra(self, tmp_path: Path) -> None:
        linhas = [("a", "atraso", "atraso"), ("b", "elogio", "elogio")]
        self._tres_arquivos(tmp_path, linhas, linhas)

        h = historia(tmp_path)

        assert h is not None
        assert h["discordancias"] is None

    def test_quando_as_regras_vencem_o_ganho_e_negativo_com_sinal_de_menos(
        self, tmp_path: Path
    ) -> None:
        regras = [("a", "atraso", "atraso"), ("b", "atraso", "atraso")]
        llm = [("a", "atraso", "atraso"), ("b", "atraso", "elogio")]
        self._tres_arquivos(tmp_path, regras, llm)

        h = historia(tmp_path)

        assert h is not None
        atraso = next(m for m in h["por_motivo"] if m["nome"] == "Atraso")
        assert atraso["ganho"].startswith(chr(0x2212))


class TestCartao:
    def test_nome_definicao_e_resposta(self) -> None:
        resultado = cartao(Rotulo("produto_errado", "sim"))

        assert resultado["nome"] == "Produto errado"
        assert resultado["definicao"].startswith("Chegou diferente")
        assert resultado["responder"] is True
