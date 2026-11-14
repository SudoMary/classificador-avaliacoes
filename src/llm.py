"""Classificador com LLM, pela API do OpenRouter (formato compatível com o da OpenAI).

O modelo recebe o mesmo guia de rotulagem que a referência seguiu e classifica
as avaliações em lotes, várias por requisição: o plano grátis do OpenRouter dá
50 requisições por dia. A resposta vem em JSON com esquema fixo e é conferida
item por item. O que vier fora do esquema conta como inválido e vira
"outro"/"nao", para o erro aparecer na medição em vez de sumir.

As respostas válidas ficam guardadas em .cache/, por modelo e versão das
instruções: medir de novo não gasta cota. A chave e o modelo vêm do ambiente
ou do arquivo .env (fora do Git).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .categorias import CODIGOS, MOTIVOS, PRECISA_RESPOSTA
from .medicao import Rotulo

URL = "https://openrouter.ai/api/v1/chat/completions"
MODELO_PADRAO = "google/gemma-4-31b-it:free"
POR_REQUISICAO = 15
# O plano grátis aceita 20 requisições por minuto; 4 segundos deixa folga.
INTERVALO_SEGUNDOS = 4.0
GUIA = Path(__file__).resolve().parent.parent / "GUIA_DE_ROTULAGEM.md"
CACHE = Path(".cache")
ENV = Path(".env")

Enviar = Callable[[dict[str, Any]], dict[str, Any]]


class ErroDoModelo(Exception):
    """A API falhou; a mensagem está pronta para mostrar ao usuário."""


def ler_configuracao(caminho_env: Path = ENV) -> tuple[str | None, str]:
    """Chave e modelo: primeiro do ambiente, depois do .env. Chave vazia vira ``None``."""
    arquivo: dict[str, str] = {}
    if caminho_env.exists():
        for linha in caminho_env.read_text(encoding="utf-8").splitlines():
            if "=" in linha and not linha.lstrip().startswith("#"):
                nome, valor = linha.split("=", 1)
                arquivo[nome.strip()] = valor.strip()
    chave = os.environ.get("OPENROUTER_API_KEY") or arquivo.get("OPENROUTER_API_KEY") or None
    modelo = os.environ.get("OPENROUTER_MODELO") or arquivo.get("OPENROUTER_MODELO")
    return chave, modelo or MODELO_PADRAO


def instrucoes() -> str:
    codigos = "\n".join(f"- {m.codigo}: {m.nome}. {m.definicao}" for m in MOTIVOS)
    return (
        "Você classifica avaliações de clientes de uma loja online brasileira. Siga "
        "exatamente o guia de rotulagem abaixo.\n\n"
        "Para cada avaliação, devolva o motivo principal, usando um destes códigos:\n"
        f"{codigos}\n\n"
        "E se a loja precisa responder, com 'sim' ou 'nao': "
        f"{PRECISA_RESPOSTA}\n\n"
        "Responda só com JSON, sem comentários, no formato "
        '{"rotulos": [{"id": 1, "motivo": "<código>", "precisa_resposta": "sim"}]}, '
        "com um item para cada avaliação, usando o número dela como id.\n\n"
        "# Guia de rotulagem\n\n" + GUIA.read_text(encoding="utf-8")
    )


def montar_pedido(avaliacoes: list[dict[str, Any]], modelo: str) -> dict[str, Any]:
    linhas = []
    for numero, avaliacao in enumerate(avaliacoes, start=1):
        titulo = f"Título: {avaliacao['titulo']}. " if avaliacao["titulo"] else ""
        linhas.append(
            f"{numero}. (nota {avaliacao['nota']} de 5) {titulo}Texto: {avaliacao['texto']}"
        )
    return {
        "model": modelo,
        "messages": [
            {"role": "system", "content": instrucoes()},
            {"role": "user", "content": "Avaliações:\n\n" + "\n".join(linhas)},
        ],
        "response_format": {"type": "json_schema", "json_schema": _ESQUEMA},
        "temperature": 0,
    }


def interpretar(resposta: dict[str, Any], quantidade: int) -> list[Rotulo | None]:
    """Os rótulos da resposta, na ordem das avaliações; ``None`` onde veio inválido."""
    try:
        conteudo = resposta["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return [None] * quantidade
    dados = _json_do_texto(conteudo)
    itens = dados.get("rotulos") if isinstance(dados, dict) else dados
    resultado: list[Rotulo | None] = [None] * quantidade
    for item in itens if isinstance(itens, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            posicao = int(item.get("id")) - 1
        except (TypeError, ValueError):
            continue
        valido = (
            0 <= posicao < quantidade
            and item.get("motivo") in CODIGOS
            and item.get("precisa_resposta") in ("sim", "nao")
        )
        # Se o mesmo id vier duas vezes, vale o primeiro.
        if valido and resultado[posicao] is None:
            resultado[posicao] = Rotulo(item["motivo"], item["precisa_resposta"])
    return resultado


class ClassificadorLLM:
    """Classifica em lotes, guarda as respostas válidas e conta o que gastou."""

    def __init__(
        self,
        *,
        enviar: Enviar,
        modelo: str,
        pasta_cache: Path = CACHE,
        dormir: Callable[[float], None] = time.sleep,
        por_requisicao: int = POR_REQUISICAO,
    ) -> None:
        self.enviar = enviar
        self.modelo = modelo
        self.dormir = dormir
        self.por_requisicao = por_requisicao
        versao = hashlib.sha256((modelo + instrucoes()).encode()).hexdigest()[:12]
        nome = re.sub(r"[^a-z0-9]+", "-", modelo.lower()).strip("-")
        self.arquivo_cache = pasta_cache / f"llm-{nome}-{versao}.json"
        self.requisicoes = 0
        self.do_cache = 0
        self.invalidas = 0

    def classificar(self, avaliacoes: list[dict[str, Any]]) -> list[Rotulo]:
        cache = self._ler_cache()
        faltando = [a for a in avaliacoes if a["review_id"] not in cache]
        self.do_cache += len(avaliacoes) - len(faltando)
        for inicio in range(0, len(faltando), self.por_requisicao):
            lote = faltando[inicio : inicio + self.por_requisicao]
            if self.requisicoes:
                self.dormir(INTERVALO_SEGUNDOS)
            self.requisicoes += 1
            rotulos = interpretar(self.enviar(montar_pedido(lote, self.modelo)), len(lote))
            for avaliacao, rotulo in zip(lote, rotulos, strict=True):
                if rotulo is not None:
                    cache[avaliacao["review_id"]] = {
                        "motivo": rotulo.motivo,
                        "precisa_resposta": rotulo.precisa_resposta,
                    }
            # Grava a cada lote: se a cota acabar no meio, o que já veio não se perde.
            self._gravar_cache(cache)

        resultado = []
        for avaliacao in avaliacoes:
            guardado = cache.get(avaliacao["review_id"])
            if guardado is None:
                self.invalidas += 1
                resultado.append(Rotulo("outro", "nao"))
            else:
                resultado.append(Rotulo(guardado["motivo"], guardado["precisa_resposta"]))
        return resultado

    def _ler_cache(self) -> dict[str, dict[str, str]]:
        if not self.arquivo_cache.exists():
            return {}
        return json.loads(self.arquivo_cache.read_text(encoding="utf-8"))

    def _gravar_cache(self, cache: dict[str, dict[str, str]]) -> None:
        self.arquivo_cache.parent.mkdir(parents=True, exist_ok=True)
        texto = json.dumps(cache, ensure_ascii=False, indent=1)
        self.arquivo_cache.write_text(texto, encoding="utf-8")


def enviar_openrouter(chave: str, *, timeout: float = 120.0) -> Enviar:
    """Função que manda um pedido ao OpenRouter e devolve a resposta em dict."""

    def enviar(pedido: dict[str, Any]) -> dict[str, Any]:
        requisicao = urllib.request.Request(
            URL,
            data=json.dumps(pedido).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {chave}",
                "Content-Type": "application/json",
                "X-Title": "classificador-avaliacoes",
            },
        )
        try:
            with urllib.request.urlopen(requisicao, timeout=timeout) as resposta:
                corpo = json.load(resposta)
        except urllib.error.HTTPError as erro:
            if erro.code == 429:
                raise ErroDoModelo(
                    "O OpenRouter recusou por limite de uso (HTTP 429). O plano grátis dá 50 "
                    "requisições por dia; as respostas já recebidas estão guardadas em .cache/."
                ) from erro
            raise ErroDoModelo(f"O OpenRouter respondeu HTTP {erro.code}.") from erro
        except urllib.error.URLError as erro:
            raise ErroDoModelo("Sem conexão com o OpenRouter.") from erro
        if "error" in corpo:
            mensagem = corpo["error"].get("message", "erro sem mensagem")
            raise ErroDoModelo(f"O OpenRouter devolveu um erro: {mensagem}")
        return corpo

    return enviar


def _json_do_texto(texto: str) -> Any:
    """JSON da resposta, mesmo com bloco de código ou texto em volta."""
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        pass
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fim <= inicio:
        return None
    try:
        return json.loads(texto[inicio : fim + 1])
    except json.JSONDecodeError:
        return None


_ESQUEMA: dict[str, Any] = {
    "name": "rotulos",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "rotulos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer"},
                        "motivo": {"type": "string", "enum": list(CODIGOS)},
                        "precisa_resposta": {"type": "string", "enum": ["sim", "nao"]},
                    },
                    "required": ["id", "motivo", "precisa_resposta"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["rotulos"],
        "additionalProperties": False,
    },
}
