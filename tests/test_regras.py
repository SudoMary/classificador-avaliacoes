"""Testes do classificador por regras (src/regras.py).

As frases são inventadas, no estilo das avaliações: as da amostra ficam para
medir, e não para escrever as regras.
"""

from __future__ import annotations

import pytest

from src.medicao import Rotulo
from src.regras import classificar


def _motivo(texto: str, nota: int = 3, titulo: str = "") -> str:
    return classificar(titulo=titulo, texto=texto, nota=nota).motivo


class TestMotivo:
    @pytest.mark.parametrize(
        ("texto", "esperado"),
        [
            ("Até agora não recebi meu pedido", "nao_recebido"),
            ("O produto ainda não chegou", "nao_recebido"),
            ("Estou aguardando a entrega faz duas semanas", "nao_recebido"),
            ("Comprei três e só chegaram duas", "entrega_incompleta"),
            ("Recebi apenas um dos itens do pedido", "entrega_incompleta"),
            ("Veio faltando a tampa", "entrega_incompleta"),
            ("Pedi azul e veio verde, cor errada", "produto_errado"),
            ("Produto falsificado, não é original", "produto_errado"),
            ("Chegou diferente do anúncio", "produto_errado"),
            ("A caneca veio quebrada", "defeito_ou_avaria"),
            ("O fone não funciona", "defeito_ou_avaria"),
            ("Chegou com defeito no zíper", "defeito_ou_avaria"),
            ("Chegou, mas com muito atraso", "atraso"),
            ("Demorou demais para entregar", "atraso"),
            ("Material de baixa qualidade, bem fino", "qualidade_ruim"),
            ("Mandei e-mail e ninguém respondeu, péssimo atendimento", "atendimento"),
            ("Cancelaram minha compra sem avisar", "atendimento"),
            ("Ótimo produto, recomendo", "elogio"),
            ("Chegou antes do prazo, adorei", "elogio"),
        ],
    )
    def test_frases_tipicas(self, texto: str, esperado: str) -> None:
        assert _motivo(texto) == esperado

    def test_ignora_maiusculas_e_acentos(self) -> None:
        assert _motivo("NAO RECEBI O PRODUTO") == "nao_recebido"

    def test_o_titulo_tambem_conta(self) -> None:
        assert _motivo("Não gostei.", titulo="Produto com defeito") == "defeito_ou_avaria"

    def test_mais_de_um_problema_vale_o_mais_grave(self) -> None:
        assert _motivo("Atrasou e ainda veio quebrado") == "defeito_ou_avaria"

    def test_reclamacao_vence_elogio(self) -> None:
        assert _motivo("Entrega rápida, mas veio a cor errada", nota=4) == "produto_errado"

    def test_negacao_desfaz_o_elogio(self) -> None:
        assert _motivo("Não recomendo", nota=1) != "elogio"

    def test_elogio_ao_atendimento_nao_e_reclamacao(self) -> None:
        assert _motivo("Ótimo atendimento", nota=5) == "elogio"

    def test_nota_fiscal_que_nao_veio_nao_e_entrega_incompleta(self) -> None:
        assert _motivo("Não veio a nota fiscal") == "atendimento"

    def test_sem_pista_no_texto_a_nota_decide(self) -> None:
        assert _motivo("Comprei para minha mãe", nota=5) == "elogio"
        assert _motivo("Comprei para minha mãe", nota=2) == "outro"


class TestResposta:
    @pytest.mark.parametrize(
        ("texto", "esperado"),
        [
            ("Até agora não recebi", "sim"),
            ("Veio quebrado", "sim"),
            ("Chegou atrasado", "nao"),
            ("Ótimo produto", "nao"),
            ("Material fraco", "nao"),
            ("Cancelaram e quero meu dinheiro de volta", "sim"),
            ("Ótimo, mas como faço para trocar a pilha?", "sim"),
            ("Veio errado, mas a loja trocou rapidinho", "nao"),
        ],
    )
    def test_frases_tipicas(self, texto: str, esperado: str) -> None:
        assert classificar(titulo="", texto=texto, nota=3).precisa_resposta == esperado

    def test_devolve_um_rotulo(self) -> None:
        assert classificar(titulo="", texto="Ótimo", nota=5) == Rotulo("elogio", "nao")
