"""Testes das métricas (src/medicao.py), com contas feitas à mão."""

from __future__ import annotations

import pytest

from src.medicao import Rotulo, medir, relatorio

DEFEITO = Rotulo("defeito_ou_avaria", "sim")
ATRASO = Rotulo("atraso", "nao")
ELOGIO = Rotulo("elogio", "nao")


class TestMotivo:
    def test_previsoes_perfeitas(self) -> None:
        referencias = [DEFEITO, ATRASO, ELOGIO]

        resultado = medir(referencias, referencias)

        assert resultado.acerto_motivo == 1.0
        assert resultado.f1_macro_motivo == 1.0

    def test_contas_por_categoria(self) -> None:
        # Referência: 2 defeitos e 2 elogios. O classificador acerta um defeito,
        # chama o outro de elogio e acerta os dois elogios.
        referencias = [DEFEITO, DEFEITO, ELOGIO, ELOGIO]
        previsoes = [DEFEITO, ELOGIO, ELOGIO, ELOGIO]

        resultado = medir(referencias, previsoes)

        assert resultado.acerto_motivo == 0.75
        defeito = resultado.por_motivo["defeito_ou_avaria"]
        assert (defeito.precisao, defeito.revocacao, defeito.suporte) == (1.0, 0.5, 2)
        assert defeito.f1 == pytest.approx(2 / 3)
        elogio = resultado.por_motivo["elogio"]
        assert (elogio.precisao, elogio.revocacao) == (pytest.approx(2 / 3), 1.0)
        assert elogio.f1 == pytest.approx(0.8)
        assert resultado.f1_macro_motivo == pytest.approx((2 / 3 + 0.8) / 2)

    def test_categoria_nunca_prevista_tem_precisao_zero_sem_erro(self) -> None:
        resultado = medir([DEFEITO, ELOGIO], [ELOGIO, ELOGIO])

        defeito = resultado.por_motivo["defeito_ou_avaria"]
        assert (defeito.precisao, defeito.revocacao, defeito.f1) == (0.0, 0.0, 0.0)

    def test_f1_macro_conta_categoria_prevista_que_nao_existe_na_referencia(self) -> None:
        # Prever "atraso" onde não há atraso é erro, e precisa pesar na média.
        resultado = medir([ELOGIO, ELOGIO], [ELOGIO, ATRASO])

        assert set(resultado.por_motivo) == {"elogio", "atraso"}
        assert resultado.por_motivo["atraso"].suporte == 0
        assert resultado.f1_macro_motivo == pytest.approx((2 / 3 + 0.0) / 2)

    def test_matriz_de_confusao(self) -> None:
        resultado = medir([DEFEITO, DEFEITO, ELOGIO], [DEFEITO, ELOGIO, ELOGIO])

        assert resultado.matriz == {
            ("defeito_ou_avaria", "defeito_ou_avaria"): 1,
            ("defeito_ou_avaria", "elogio"): 1,
            ("elogio", "elogio"): 1,
        }

    def test_listas_de_tamanho_diferente_levantam_erro(self) -> None:
        with pytest.raises(ValueError):
            medir([DEFEITO], [])


class TestResposta:
    def test_mede_a_classe_sim(self) -> None:
        # Referência: sim, sim, não, não. Previsto: sim, não, sim, não.
        referencias = [DEFEITO, DEFEITO, ELOGIO, ELOGIO]
        previsoes = [
            Rotulo("defeito_ou_avaria", "sim"),
            Rotulo("defeito_ou_avaria", "nao"),
            Rotulo("elogio", "sim"),
            Rotulo("elogio", "nao"),
        ]

        resultado = medir(referencias, previsoes)

        assert resultado.acerto_resposta == 0.5
        assert resultado.resposta_sim.precisao == 0.5
        assert resultado.resposta_sim.revocacao == 0.5
        assert resultado.resposta_sim.suporte == 2


class TestRelatorio:
    def test_traz_titulo_notas_e_numeros_formatados(self) -> None:
        resultado = medir([DEFEITO, DEFEITO, ELOGIO, ELOGIO], [DEFEITO, ELOGIO, ELOGIO, ELOGIO])

        texto = relatorio(resultado, titulo="Regras · teste", notas=["Rótulos revisados: 0 de 4."])

        assert texto.startswith("# Regras · teste")
        assert "Rótulos revisados: 0 de 4." in texto
        assert "Acerto: 75,0% (3 de 4)" in texto
        assert "| Defeito ou avaria | 100,0% | 50,0% | 0,67 | 2 |" in texto
        assert "## Matriz de confusão" in texto

    def test_avisa_quando_ha_poucas_avaliacoes_na_categoria(self) -> None:
        resultado = medir([DEFEITO, ELOGIO], [DEFEITO, ELOGIO])

        assert "menos de 10 avaliações" in relatorio(resultado, titulo="t", notas=[])
