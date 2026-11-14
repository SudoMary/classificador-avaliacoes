"""Testes do site (src/web.py), da rota ao HTML.

O modelo é falso e a configuração entra pronta: nenhum teste lê o .env nem
chama o OpenRouter.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.llm import ErroDoModelo
from src.web import criar_app

MODELO = "modelo/teste:free"


class ModeloFalso:
    """Responde com o motivo escolhido e conta as chamadas."""

    def __init__(self) -> None:
        self.motivo = "defeito_ou_avaria"
        self.erro: Exception | None = None
        self.chamadas = 0

    def __call__(self, pedido: dict[str, Any]) -> dict[str, Any]:
        self.chamadas += 1
        if self.erro:
            raise self.erro
        item = {"id": 1, "motivo": self.motivo, "precisa_resposta": "sim"}
        return {"choices": [{"message": {"content": json.dumps({"rotulos": [item]})}}]}


@pytest.fixture
def modelo() -> ModeloFalso:
    return ModeloFalso()


@pytest.fixture
def site(modelo: ModeloFalso) -> Iterator[TestClient]:
    app = criar_app(configuracao=(None, MODELO), enviar=modelo, limite_diario_llm=2)
    with TestClient(app) as cliente:
        yield cliente


def _classificar(site: TestClient, texto: str = "A caneca veio quebrada.", nota: str = "1") -> Any:
    return site.post("/", data={"texto": texto, "nota": nota})


class TestPagina:
    def test_tem_formulario_exemplos_e_resultados_medidos(self, site: TestClient) -> None:
        texto = site.get("/").text

        assert 'name="texto"' in texto
        assert "Pedi azul e veio verde." in texto
        # Calculados a partir dos arquivos de resultados/ do repositório.
        assert "78,7%" in texto
        assert "96,0%" in texto

    def test_resultados_ausentes_nao_quebram_a_pagina(
        self, modelo: ModeloFalso, tmp_path: Path
    ) -> None:
        app = criar_app(configuracao=(None, MODELO), enviar=modelo, pasta_resultados=tmp_path)

        with TestClient(app) as cliente:
            assert cliente.get("/").status_code == 200

    def test_saude(self, site: TestClient) -> None:
        assert site.get("/saude").json() == {"status": "ok"}


class TestClassificar:
    def test_mostra_regras_e_llm_lado_a_lado(self, site: TestClient, modelo: ModeloFalso) -> None:
        resposta = _classificar(site)

        assert resposta.status_code == 200
        assert "Regras por palavras-chave" in resposta.text
        assert MODELO in resposta.text
        assert resposta.text.count("Defeito ou avaria") >= 2
        assert "Os dois concordam" in resposta.text
        assert modelo.chamadas == 1

    def test_avisa_quando_discordam(self, site: TestClient, modelo: ModeloFalso) -> None:
        modelo.motivo = "atendimento"

        texto = _classificar(site).text

        assert "Discordam" in texto
        # Números calculados dos arquivos de resultados/ do repositório.
        assert "nas 33 vezes em que discordaram, o LLM acertou 29 e as regras, 3" in texto

    def test_mesmo_texto_de_novo_nao_gasta_cota(
        self, site: TestClient, modelo: ModeloFalso
    ) -> None:
        _classificar(site)
        _classificar(site)

        assert modelo.chamadas == 1

    def test_limite_diario_do_llm_deixa_so_as_regras(
        self, site: TestClient, modelo: ModeloFalso
    ) -> None:
        _classificar(site, "texto um")
        _classificar(site, "texto dois")

        resposta = _classificar(site, "texto três")

        assert resposta.status_code == 200
        assert "limite de hoje" in resposta.text
        assert "Regras por palavras-chave" in resposta.text
        assert modelo.chamadas == 2

    def test_limite_volta_no_dia_seguinte_em_brasilia(self, modelo: ModeloFalso) -> None:
        agora = [datetime(2026, 11, 14, 2, 0, tzinfo=UTC)]  # 23h do dia 13 em Brasília
        app = criar_app(
            configuracao=(None, MODELO),
            enviar=modelo,
            limite_diario_llm=1,
            relogio=lambda: agora[0],
        )
        with TestClient(app) as site:
            _classificar(site, "texto um")
            agora[0] = datetime(2026, 11, 14, 4, 0, tzinfo=UTC)  # 1h do dia 14

            _classificar(site, "texto dois")

        assert modelo.chamadas == 2

    def test_falha_do_modelo_mostra_aviso_e_mantem_as_regras(
        self, site: TestClient, modelo: ModeloFalso
    ) -> None:
        modelo.erro = ErroDoModelo("O modelo está sobrecarregado no fornecedor.")

        resposta = _classificar(site)

        assert resposta.status_code == 200
        assert "sobrecarregado" in resposta.text
        assert "Defeito ou avaria" in resposta.text

    def test_sem_chave_o_llm_fica_desligado(self, modelo: ModeloFalso) -> None:
        app = criar_app(configuracao=(None, MODELO), enviar=None)
        with TestClient(app) as site:
            resposta = _classificar(site)

        assert "desligado" in resposta.text
        assert "Defeito ou avaria" in resposta.text
        assert modelo.chamadas == 0

    def test_texto_digitado_e_escapado(self, site: TestClient) -> None:
        texto = _classificar(site, "<script>alert(1)</script>").text

        assert "<script>alert(1)</script>" not in texto
        assert "&lt;script&gt;" in texto


class TestEntradaInvalida:
    @pytest.mark.parametrize(
        ("texto", "nota", "mensagem"),
        [
            ("   ", "3", "Escreva uma avaliação"),
            ("x" * 501, "3", "500 caracteres"),
            ("Chegou quebrado", "9", "nota de 1 a 5"),
            ("Chegou quebrado", "abc", "nota de 1 a 5"),
        ],
    )
    def test_volta_com_a_mensagem_sem_chamar_o_modelo(
        self, site: TestClient, modelo: ModeloFalso, texto: str, nota: str, mensagem: str
    ) -> None:
        resposta = _classificar(site, texto, nota)

        assert resposta.status_code == 400
        assert mensagem in resposta.text
        assert modelo.chamadas == 0
