"""O Enem: a prova, a redacao, os cortes do Sisu/ProUni e a escolha da via.

Resumo das regras de jogo (simplificadas das regras reais do Inep/MEC):
- 4 areas objetivas valem 300-1000 cada; a redacao vale 0-1000 (5 competencias de 0-200).
- A nota final de admissao e a media das 5 notas.
- Treineiro faz a prova pra treinar: paga taxa, nao tem isencao, e a nota nao vale.
- Sisu (ampla / cota) tem nota de corte que muda todo ano; ProUni e Fies exigem
  media >= 450 e redacao diferente de zero.
"""

from .content import (
    AREAS, AREAS_OBJETIVAS, CORTE_BASE, CORTE_VARIACAO, MEDIA_MINIMA, VIAS,
)
from .rng import stream
from .util import State, clamp

TAXA_TREINEIRO = 85
EXP_MAXIMA = 40


def _nervosismo(e: State) -> float:
    """Quanto o dia da prova pesa: cansaco, desanimo e falta de pratica."""
    return ((100 - e["saude"]) * 0.05
            + max(0.0, 30 - e["exp_prova"]) * 0.12
            + (100 - e["animo"]) * 0.03)


def prova(e: State, canal: str) -> dict:
    """Faz a prova com o saber de hoje. Nao muda `e`. Deterministica por (seed, ano, canal)."""
    rng = stream(e["seed"], e["t"], canal)
    nerv = _nervosismo(e)
    areas = {}
    for a in AREAS_OBJETIVAS:
        k = e["saber"][a] + e["exp_prova"] * 0.05
        k_eff = k + rng.gauss(0, 4 + nerv)
        areas[a] = int(clamp(round(300 + 6.3 * k_eff), 0, 1000))
    kr = e["saber"]["redacao"]
    comps = []
    for _ in range(5):
        c = kr / 100 * 200 + rng.gauss(0, 18 + nerv * 2)
        comps.append(int(clamp(round(c / 40) * 40, 0, 200)))
    zerou = rng.random() < max(0.0, 0.07 - kr / 1200)
    if zerou:
        comps = [0] * 5
    redacao = sum(comps)
    media = (sum(areas.values()) + redacao) / 5
    fraca = min(AREAS, key=lambda a: redacao if a == "redacao" else areas[a])
    return {"areas": areas, "comps": comps, "redacao": redacao, "media": round(media, 1),
            "zerou": zerou, "fraca": fraca}


def sorteia_cortes(e: State) -> dict:
    """Nota de corte de cada via neste ano (o Fies nao tem corte, so a media minima)."""
    rng = stream(e["seed"], e["t"], "cortes")
    return {v: (0 if CORTE_BASE[v] == 0 else int(round(CORTE_BASE[v] + rng.gauss(0, CORTE_VARIACAO))))
            for v in VIAS}


def elegivel(via: str, p: dict, corte: int) -> tuple[bool, str]:
    """(passou, motivo). motivo e '' se passou, senao 'corte' ou 'minimo'."""
    if via in ("prouni", "fies") and (p["media"] < MEDIA_MINIMA or p["redacao"] == 0):
        return False, "minimo"
    if p["media"] < corte:
        return False, "corte"
    return True, ""


def resolver_vias(e: State, p: dict, escolhidas: list[str]) -> dict:
    """Aplica as vias escolhidas na ordem de prioridade e devolve o resultado."""
    cortes = sorteia_cortes(e)
    escolhidas = [v for v in VIAS if v in set(escolhidas)]
    detalhe = {}
    via = ""
    for v in escolhidas:
        ok, motivo = elegivel(v, p, cortes[v])
        detalhe[v] = {"ok": ok, "motivo": motivo, "corte": cortes[v]}
        if ok and not via:
            via = v
    return {"via": via, "cortes": cortes, "detalhe": detalhe, "escolhidas": escolhidas}
