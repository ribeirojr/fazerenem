"""A causa da terra: o ultimo ato do jogo.

Voce e a advogada ou o advogado do proprio acampamento. Duas barras, como no
Lona Preta: a SUA DEFESA e a ACUSACAO do dono. A cada etapa do processo
(liminar, pericia, sentenca e ate 2 apelacoes) voce escolhe ate 2 acoes; a
margem entre as duas barras, mais um sorteio, decide se a etapa e ganha.
"""

from .content import (
    ACOES_CASO, CUSTO_CASO, ETAPAS_CASO, MAX_ACOES_CASO, REGIOES,
)
from .rng import stream
from .util import State, clamp, log

BONUS_ETAPA_FIXA = 0.4       # fracao do bonus de uma etapa que fica pro resto do processo
RUIDO = 7.0
BONUS_APELACAO = 4.0         # a apelacao traz argumentos novos
BONUS_VITORIA_PREVIA = 3.0   # cada etapa ganha antes pesa na sentenca


def iniciar(e: State) -> None:
    reg = REGIOES[e["regiao"]]
    defesa = 8 + 0.4 * e["juridico"] + 0.25 * e["pratica"] + 0.12 * e["rede"] + 0.1 * e["luta"]
    acusacao = reg.dono + 2 * e["despejos"] - min(8, reg.improdutiva / 3)
    e["caso"] = {
        "idx": 0, "defesa": round(defesa, 1), "acusacao": round(acusacao, 1),
        "vitorias": 0, "usos": {}, "improdutiva": reg.improdutiva,
    }


def valor_acao(e: State, acao: str, usos: int) -> dict:
    """Efeito da acao agora: {'defesa': x, 'acusacao': y}. Repetir a mesma acao rende menos."""
    c = e["caso"]
    f = 0.7 ** usos
    j, p, r, lu = e["juridico"], e["pratica"], e["rede"], e["luta"]
    d = a = 0.0
    if acao == "peticao":
        d = 2 + j / 18
    elif acao == "laudo":
        d = 1.5 + r / 22
        a = -(1 + c["improdutiva"] / 10)
    elif acao == "mobilizar":
        d = 1.5 + lu / 14
    elif acao == "acordo":
        a = -(1 + p / 12) * (1.0 if p >= 20 else 0.5)
    elif acao == "mp":
        d = (1.5 + r / 16 + 1.2 * e["despejos"]) * (1.0 if r >= 20 else 0.5)
    return {"defesa": round(d * f, 1), "acusacao": round(a * f, 1)}


def previsao(e: State) -> dict:
    """O que cada acao rende agora, pra UI mostrar antes de escolher."""
    c = e["caso"]
    return {a: {**valor_acao(e, a, c["usos"].get(a, 0)), "custo": CUSTO_CASO.get(a, 0)}
            for a in ACOES_CASO}


def margem_base(e: State) -> float:
    return e["caso"]["defesa"] - e["caso"]["acusacao"]


def jogar_etapa(e: State, acoes: list[str]) -> dict:
    """Resolve UMA etapa do processo (um ano). Pode terminar o jogo."""
    c = e["caso"]
    etapa = ETAPAS_CASO[c["idx"]]
    rng = stream(e["seed"], e["t"], "caso")

    escolhidas: list[str] = []
    for a in acoes:
        if a in ACOES_CASO and a not in escolhidas and len(escolhidas) < MAX_ACOES_CASO:
            escolhidas.append(a)

    bonus_d = bonus_a = 0.0
    gasto = 0
    usadas = []
    for a in escolhidas:
        custo = CUSTO_CASO.get(a, 0)
        if custo > max(e["dinheiro"], 0):
            continue  # sem dinheiro: a acao nao sai do papel
        e["dinheiro"] -= custo
        gasto += custo
        v = valor_acao(e, a, c["usos"].get(a, 0))
        bonus_d += v["defesa"]
        bonus_a += v["acusacao"]
        c["usos"][a] = c["usos"].get(a, 0) + 1
        usadas.append(a)

    extra = 0.0
    if etapa == "sentenca":
        extra += BONUS_VITORIA_PREVIA * c["vitorias"]
    if etapa.startswith("apelacao"):
        extra += BONUS_APELACAO
    sorteio = rng.gauss(0, RUIDO)
    margem = margem_base(e) + bonus_d - bonus_a + extra + sorteio
    ganhou = margem >= 0

    # parte do esforco fica no processo
    c["defesa"] = round(clamp(c["defesa"] + BONUS_ETAPA_FIXA * bonus_d, 0, 140), 1)
    c["acusacao"] = round(clamp(c["acusacao"] + BONUS_ETAPA_FIXA * bonus_a, 0, 140), 1)

    rel = {
        "tipo": "caso", "etapa": etapa, "ganhou": ganhou, "margem": round(margem, 1),
        "usadas": usadas, "gasto": gasto, "defesa": c["defesa"], "acusacao": c["acusacao"],
        "fim": "",
    }

    if ganhou:
        c["vitorias"] += 1
    if etapa == "liminar":
        if ganhou:
            e["terra_ameaca"] = clamp(e["terra_ameaca"] - 30)
            e["animo"] = clamp(e["animo"] + 8)
        else:
            e["despejos"] += 1
            e["animo"] = clamp(e["animo"] - 8)
            c["acusacao"] = round(c["acusacao"] + 2, 1)
    elif etapa == "pericia" and ganhou:
        c["defesa"] = round(c["defesa"] + 4, 1)

    if etapa in ("sentenca", "apelacao1", "apelacao2"):
        if ganhou:
            rel["fim"] = "vitoria"
        elif etapa == "apelacao2":
            rel["fim"] = "derrota"
        c["idx"] = c["idx"] + 1 if not rel["fim"] else c["idx"]
    else:
        c["idx"] += 1
    log(e, "log.caso_ganhou" if ganhou else "log.caso_perdeu", etapa=etapa)
    return rel
