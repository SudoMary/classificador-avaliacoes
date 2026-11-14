"""Site do classificador: `uvicorn src.web:app`.

Uma página: a pessoa cola uma avaliação, escolhe a nota e vê, lado a lado, o
que dizem as regras e o LLM grátis. Abaixo, os números medidos no conjunto de
teste, calculados dos arquivos de resultados/.

O LLM gasta a cota grátis do OpenRouter (50 requisições por dia, divididas com
outros usos da mesma chave). Por isso tem um limite diário próprio e um cache
por texto; passado o limite, a página responde só com as regras. O contador e
o cache ficam na memória: a hospedagem grátis apaga tudo ao dormir, e zerar o
contador ali só devolve cota que a chave ainda limita do lado do OpenRouter.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .llm import (
    Enviar,
    ErroDoModelo,
    enviar_openrouter,
    interpretar,
    ler_configuracao,
    montar_pedido,
)
from .medicao import Rotulo
from .pagina import EXEMPLOS, cartao, discordancias, resultados_medidos
from .regras import classificar as classificar_por_regras

_PASTA = Path(__file__).resolve().parent
_TEMPLATES = Jinja2Templates(directory=_PASTA / "templates")
RESULTADOS = _PASTA.parent / "resultados"
TAMANHO_MAXIMO = 500
LIMITE_DIARIO_LLM = 15
# Brasília não tem horário de verão desde 2019.
_FUSO_DE_BRASILIA = timedelta(hours=-3)


class _LimiteDiario:
    """Conta os usos do LLM no dia de Brasília. Seguro com várias requisições ao mesmo tempo."""

    def __init__(self, limite: int, relogio: Callable[[], datetime]) -> None:
        self.limite = limite
        self.relogio = relogio
        self.dia: date | None = None
        self.usadas = 0
        self._trava = threading.Lock()

    def tentar(self) -> bool:
        with self._trava:
            self._virar_o_dia()
            if self.usadas >= self.limite:
                return False
            self.usadas += 1
            return True

    def restantes(self) -> int:
        with self._trava:
            self._virar_o_dia()
            return self.limite - self.usadas

    def _virar_o_dia(self) -> None:
        hoje = (self.relogio().astimezone(UTC) + _FUSO_DE_BRASILIA).date()
        if hoje != self.dia:
            self.dia, self.usadas = hoje, 0


def criar_app(
    *,
    configuracao: tuple[str | None, str] | None = None,
    enviar: Enviar | None = None,
    limite_diario_llm: int = LIMITE_DIARIO_LLM,
    pasta_resultados: Path = RESULTADOS,
    relogio: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> FastAPI:
    """Monta o site. `configuracao` e `enviar` existem para os testes não lerem o .env."""
    chave, modelo = configuracao if configuracao is not None else ler_configuracao()
    if enviar is None and chave is not None:
        enviar = enviar_openrouter(chave)
    limite = _LimiteDiario(limite_diario_llm, relogio)
    cache: dict[tuple[str, int], Rotulo] = {}

    @asynccontextmanager
    async def ciclo_de_vida(app: FastAPI):  # type: ignore[no-untyped-def]
        # Lidos uma vez: os arquivos de resultados só mudam com um novo deploy.
        app.state.medidos = resultados_medidos(pasta_resultados)
        app.state.discordancias = discordancias(pasta_resultados)
        yield

    app = FastAPI(
        title="Classificador de avaliações",
        lifespan=ciclo_de_vida,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.mount("/estatico", StaticFiles(directory=_PASTA / "estatico"), name="estatico")

    def _pagina(request: Request, status_code: int = 200, **conteudo: Any) -> Response:
        contexto = {
            "exemplos": EXEMPLOS,
            "medidos": request.app.state.medidos,
            "discordancias": request.app.state.discordancias,
            "modelo": modelo,
            "llm_ligado": enviar is not None,
            "restantes": limite.restantes(),
            "tamanho_maximo": TAMANHO_MAXIMO,
            "texto": "",
            "nota": 3,
            **conteudo,
        }
        return _TEMPLATES.TemplateResponse(
            request, "pagina.html", contexto, status_code=status_code
        )

    @app.get("/", response_class=HTMLResponse)
    def inicio(request: Request) -> Response:
        return _pagina(request)

    @app.post("/", response_class=HTMLResponse)
    def classificar(request: Request, texto: str = Form(""), nota: str = Form("3")) -> Response:
        texto = texto.strip()
        erro = _validar(texto, nota)
        if erro:
            return _pagina(request, 400, texto=texto, erro=erro)
        nota_valida = int(nota)
        regras = classificar_por_regras(titulo="", texto=texto, nota=nota_valida)
        llm = _classificar_com_llm(texto, nota_valida)
        return _pagina(
            request,
            texto=texto,
            nota=nota_valida,
            regras=cartao(regras),
            llm=llm,
            concordam=llm.get("rotulo") == regras if llm.get("rotulo") else None,
        )

    def _classificar_com_llm(texto: str, nota: int) -> dict[str, Any]:
        """O resultado do LLM, ou o motivo de não haver resultado."""
        if enviar is None:
            return {"aviso": "O LLM está desligado neste ambiente: falta a chave do OpenRouter."}
        chave_do_cache = (texto, nota)
        if chave_do_cache in cache:
            rotulo = cache[chave_do_cache]
            return {"rotulo": rotulo, "cartao": cartao(rotulo)}
        if not limite.tentar():
            return {
                "aviso": "O LLM atingiu o limite de hoje, que protege a cota grátis. "
                "Amanhã tem mais; as regras continuam respondendo."
            }
        avaliacao = {"review_id": "site", "nota": str(nota), "titulo": "", "texto": texto}
        try:
            [rotulo] = interpretar(enviar(montar_pedido([avaliacao], modelo)), 1)
        except ErroDoModelo as erro:
            return {"aviso": str(erro)}
        if rotulo is None:
            return {"aviso": "O modelo respondeu fora do formato combinado. Tente de novo."}
        cache[chave_do_cache] = rotulo
        return {"rotulo": rotulo, "cartao": cartao(rotulo)}

    @app.get("/saude")
    def saude() -> dict[str, str]:
        """Usado pela hospedagem para saber se o processo está de pé."""
        return {"status": "ok"}

    return app


def _validar(texto: str, nota: str) -> str | None:
    if not texto:
        return "Escreva uma avaliação para classificar."
    if len(texto) > TAMANHO_MAXIMO:
        return f"A avaliação passou de {TAMANHO_MAXIMO} caracteres. Encurte e tente de novo."
    if not nota.isdigit() or not 1 <= int(nota) <= 5:
        return "Escolha uma nota de 1 a 5."
    return None


app = criar_app()
