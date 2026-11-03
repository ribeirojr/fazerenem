"""Trava de equilibrio: quem joga bem ganha, quem nao joga nao ganha.

Os bots estao em tools/balance.py (rode `python3 tools/balance.py 30` pra ver o quadro todo).
"""

import balance
from lonatoga.sim.content import ORDEM_REGIOES

SEEDS = range(1, 9)


def taxa_de_vitoria(plano_fn):
    jogos = [balance.jogar(s, r, plano_fn) for r in ORDEM_REGIOES for s in SEEDS]
    return sum(j["fim"]["tipo"] == "vitoria" for j in jogos) / len(jogos), jogos


def test_jogador_competente_ganha_quase_sempre():
    taxa, _ = taxa_de_vitoria(balance.plano_competente)
    assert taxa >= 0.75, taxa


def test_jogador_largado_nunca_ganha():
    taxa, jogos = taxa_de_vitoria(balance.plano_largado)
    assert taxa == 0
    assert all(j["fim"]["tipo"] == "tempo" for j in jogos)


def test_regiao_mais_dificil_e_realmente_mais_dificil():
    """Sul do Para (dono mais forte, escola pior) perde mais que Pontal para o jogador mediano."""
    def vitorias(regiao):
        return sum(balance.jogar(s, regiao, balance.plano_mediano)["fim"]["tipo"] == "vitoria" for s in range(1, 13))
    assert vitorias("sul_para") < vitorias("pontal")


def test_o_jogo_e_longo_o_bastante_pra_valer_a_pena():
    """Quem ganha leva pelo menos 20 anos de vida (6 a 26+)."""
    for s in range(1, 6):
        e = balance.jogar(s, "pontal", balance.plano_competente)
        assert e["fim"]["tipo"] == "vitoria" and e["fim"]["idade"] >= 24
