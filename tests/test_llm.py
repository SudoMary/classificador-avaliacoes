"""Testes do classificador com LLM (src/llm.py).

O modelo é falso: nenhum teste chama a rede nem gasta a cota do OpenRouter.
"""

from __future__ import annotations

import io
import json
import re
import urllib.error
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from src.categorias import CODIGOS
from src.llm import (
    MODELO_PADRAO,
    ClassificadorLLM,
    ErroDoModelo,
    enviar_openrouter,
    interpretar,
    ler_configuracao,
    montar_pedido,
)
from src.medicao import Rotulo

MODELO = "modelo/teste:free"


def _avaliacoes(quantidade: int) -> list[dict[str, Any]]:
    return [
        {"review_id": f"r{i}", "nota": "5", "titulo": "", "texto": f"Ótimo produto {i}"}
        for i in range(1, quantidade + 1)
    ]


def _resposta(conteudo: str) -> dict[str, Any]:
    return {"choices": [{"message": {"content": conteudo}}]}


def _json(*itens: tuple[int, str, str]) -> str:
    return json.dumps(
        {"rotulos": [{"id": i, "motivo": m, "precisa_resposta": r} for i, m, r in itens]}
    )


def _quantidade(pedido: dict[str, Any]) -> int:
    return len(re.findall(r"^\d+\. ", pedido["messages"][-1]["content"], re.MULTILINE))


class ModeloFalso:
    """Responde "elogio" para tudo, ou o que `conteudo` mandar, e guarda os pedidos."""

    def __init__(
        self,
        conteudo: Callable[[int], str] | None = None,
        erro_no_pedido: int | None = None,
    ) -> None:
        self.conteudo = conteudo
        self.erro_no_pedido = erro_no_pedido
        self.pedidos: list[dict[str, Any]] = []

    def __call__(self, pedido: dict[str, Any]) -> dict[str, Any]:
        self.pedidos.append(pedido)
        if self.erro_no_pedido == len(self.pedidos):
            raise ErroDoModelo("O OpenRouter recusou por limite de uso.")
        quantidade = _quantidade(pedido)
        if self.conteudo:
            return _resposta(self.conteudo(quantidade))
        return _resposta(_json(*[(i, "elogio", "nao") for i in range(1, quantidade + 1)]))


def _classificador(modelo: ModeloFalso, pasta: Path, **opcoes: Any) -> ClassificadorLLM:
    return ClassificadorLLM(
        enviar=modelo, modelo=MODELO, pasta_cache=pasta, dormir=lambda _: None, **opcoes
    )


class TestPedido:
    def test_leva_o_guia_e_os_codigos_nas_instrucoes(self) -> None:
        pedido = montar_pedido(_avaliacoes(1), MODELO)

        sistema = pedido["messages"][0]["content"]
        assert pedido["messages"][0]["role"] == "system"
        assert "Casos decididos durante a rotulagem" in sistema
        for codigo in CODIGOS:
            assert codigo in sistema

    def test_numera_as_avaliacoes_com_nota_titulo_e_texto(self) -> None:
        avaliacoes = [
            {"review_id": "a", "nota": "1", "titulo": "Ruim", "texto": "Veio quebrado"},
            {"review_id": "b", "nota": "5", "titulo": "", "texto": "Adorei"},
        ]

        usuario = montar_pedido(avaliacoes, MODELO)["messages"][1]["content"]

        assert "1. (nota 1 de 5) Título: Ruim. Texto: Veio quebrado" in usuario
        assert "2. (nota 5 de 5) Texto: Adorei" in usuario

    def test_pede_json_com_esquema_estrito_e_os_codigos_permitidos(self) -> None:
        pedido = montar_pedido(_avaliacoes(1), MODELO)

        formato = pedido["response_format"]
        assert pedido["model"] == MODELO
        assert formato["type"] == "json_schema"
        assert formato["json_schema"]["strict"] is True
        item = formato["json_schema"]["schema"]["properties"]["rotulos"]["items"]
        assert item["properties"]["motivo"]["enum"] == list(CODIGOS)
        assert item["properties"]["precisa_resposta"]["enum"] == ["sim", "nao"]


class TestInterpretar:
    def test_resposta_valida(self) -> None:
        resposta = _resposta(_json((1, "atraso", "nao"), (2, "defeito_ou_avaria", "sim")))

        assert interpretar(resposta, 2) == [
            Rotulo("atraso", "nao"),
            Rotulo("defeito_ou_avaria", "sim"),
        ]

    def test_aceita_json_dentro_de_bloco_de_codigo_com_texto_em_volta(self) -> None:
        conteudo = "Aqui está:\n```json\n" + _json((1, "elogio", "nao")) + "\n```\nPronto."

        assert interpretar(_resposta(conteudo), 1) == [Rotulo("elogio", "nao")]

    def test_item_fora_do_esquema_vira_none_so_naquele_item(self) -> None:
        resposta = _resposta(
            _json((1, "elogio", "nao"), (2, "inventado", "sim"), (3, "outro", "x"))
        )

        assert interpretar(resposta, 3) == [Rotulo("elogio", "nao"), None, None]

    def test_item_faltando_e_id_repetido(self) -> None:
        resposta = _resposta(_json((1, "elogio", "nao"), (1, "atraso", "nao")))

        assert interpretar(resposta, 2) == [Rotulo("elogio", "nao"), None]

    def test_resposta_sem_json_e_toda_invalida(self) -> None:
        assert interpretar(_resposta("Não sei classificar."), 2) == [None, None]
        assert interpretar({"choices": []}, 1) == [None]


class TestClassificador:
    def test_divide_em_lotes_e_espera_entre_as_requisicoes(self, tmp_path: Path) -> None:
        esperas: list[float] = []
        modelo = ModeloFalso()
        classificador = ClassificadorLLM(
            enviar=modelo,
            modelo=MODELO,
            pasta_cache=tmp_path,
            dormir=esperas.append,
            por_requisicao=15,
        )

        rotulos = classificador.classificar(_avaliacoes(32))

        assert [_quantidade(p) for p in modelo.pedidos] == [15, 15, 2]
        assert len(esperas) == 2
        assert rotulos == [Rotulo("elogio", "nao")] * 32
        assert classificador.requisicoes == 3

    def test_medir_de_novo_usa_o_cache_e_nao_gasta_cota(self, tmp_path: Path) -> None:
        _classificador(ModeloFalso(), tmp_path).classificar(_avaliacoes(3))
        modelo = ModeloFalso()
        classificador = _classificador(modelo, tmp_path)

        rotulos = classificador.classificar(_avaliacoes(3))

        assert modelo.pedidos == []
        assert classificador.do_cache == 3
        assert rotulos == [Rotulo("elogio", "nao")] * 3

    def test_resposta_invalida_conta_vira_outro_e_nao_vai_para_o_cache(
        self, tmp_path: Path
    ) -> None:
        modelo = ModeloFalso(conteudo=lambda _: _json((1, "elogio", "nao")))
        classificador = _classificador(modelo, tmp_path)

        rotulos = classificador.classificar(_avaliacoes(2))

        assert rotulos == [Rotulo("elogio", "nao"), Rotulo("outro", "nao")]
        assert classificador.invalidas == 1
        # Na próxima vez, só a inválida volta ao modelo.
        segundo = ModeloFalso()
        _classificador(segundo, tmp_path).classificar(_avaliacoes(2))
        assert [_quantidade(p) for p in segundo.pedidos] == [1]

    def test_cache_e_separado_por_modelo(self, tmp_path: Path) -> None:
        _classificador(ModeloFalso(), tmp_path).classificar(_avaliacoes(1))
        modelo = ModeloFalso()

        ClassificadorLLM(
            enviar=modelo, modelo="outro/modelo:free", pasta_cache=tmp_path, dormir=lambda _: None
        ).classificar(_avaliacoes(1))

        assert len(modelo.pedidos) == 1

    def test_erro_do_modelo_sobe_e_o_que_ja_veio_fica_guardado(self, tmp_path: Path) -> None:
        modelo = ModeloFalso(erro_no_pedido=2)

        with pytest.raises(ErroDoModelo):
            _classificador(modelo, tmp_path, por_requisicao=2).classificar(_avaliacoes(4))

        segundo = ModeloFalso()
        _classificador(segundo, tmp_path, por_requisicao=2).classificar(_avaliacoes(4))
        assert [_quantidade(p) for p in segundo.pedidos] == [2]


class TestConfiguracao:
    def test_le_a_chave_do_env_quando_o_ambiente_nao_tem(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_MODELO", raising=False)
        env = tmp_path / ".env"
        env.write_text("# comentário\nOPENROUTER_API_KEY= sk-or-teste \n", encoding="utf-8")

        chave, modelo = ler_configuracao(env)

        assert chave == "sk-or-teste"
        assert modelo == MODELO_PADRAO

    def test_ambiente_vence_o_env_e_chave_vazia_e_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env = tmp_path / ".env"
        env.write_text("OPENROUTER_API_KEY=\nOPENROUTER_MODELO=do/env:free\n", encoding="utf-8")
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_MODELO", "do/ambiente:free")

        assert ler_configuracao(env) == (None, "do/ambiente:free")


class TestEnviar:
    def test_limite_de_uso_vira_mensagem_clara(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def recusar(*_: Any, **__: Any) -> Any:
            raise urllib.error.HTTPError(
                "https://openrouter.ai", 429, "Too Many Requests", None, io.BytesIO(b"{}")
            )

        monkeypatch.setattr("urllib.request.urlopen", recusar)

        with pytest.raises(ErroDoModelo, match="limite de uso"):
            enviar_openrouter("sk-or-teste")({"model": MODELO, "messages": []})

    def test_erro_no_corpo_da_resposta_sobe(self, monkeypatch: pytest.MonkeyPatch) -> None:
        corpo = json.dumps({"error": {"message": "modelo indisponível"}}).encode()
        monkeypatch.setattr("urllib.request.urlopen", lambda *_, **__: io.BytesIO(corpo))

        with pytest.raises(ErroDoModelo, match="modelo indisponível"):
            enviar_openrouter("sk-or-teste")({"model": MODELO, "messages": []})


def _erro_http(codigo: int, corpo: str) -> urllib.error.HTTPError:
    return urllib.error.HTTPError(
        "https://openrouter.ai", codigo, "erro", None, io.BytesIO(corpo.encode())
    )


class TestSobrecarga:
    """Modelo grátis cheio no fornecedor: tenta de novo, sem confundir com o fim da cota."""

    def test_tenta_de_novo_e_segue_quando_o_fornecedor_libera(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        respostas: list[Any] = [
            _erro_http(429, '{"error": {"metadata": {"raw": "rate-limited upstream"}}}'),
            io.BytesIO(json.dumps(_resposta(_json((1, "elogio", "nao")))).encode()),
        ]

        def responder(*_: Any, **__: Any) -> Any:
            resposta = respostas.pop(0)
            if isinstance(resposta, Exception):
                raise resposta
            return resposta

        monkeypatch.setattr("urllib.request.urlopen", responder)
        esperas: list[float] = []

        resposta = enviar_openrouter("sk-or-teste", dormir=esperas.append)({"model": MODELO})

        assert interpretar(resposta, 1) == [Rotulo("elogio", "nao")]
        assert esperas == [15.0]

    def test_desiste_depois_das_tentativas_com_mensagem_clara(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def recusar(*_: Any, **__: Any) -> Any:
            raise _erro_http(429, '{"error": {"metadata": {"raw": "rate-limited upstream"}}}')

        monkeypatch.setattr("urllib.request.urlopen", recusar)
        esperas: list[float] = []

        with pytest.raises(ErroDoModelo, match="sobrecarregado"):
            enviar_openrouter("sk-or-teste", dormir=esperas.append)({"model": MODELO})

        assert esperas == [15.0, 30.0, 60.0]
