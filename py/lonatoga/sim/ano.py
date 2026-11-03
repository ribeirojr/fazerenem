"""Um ano de vida: o que o plano do jogador faz com saber, saude, comida e dinheiro.

Cada turno do jogo e UM ANO. O jogador reparte `orcamento` pontos de tempo entre
as acoes da etapa (escola, estudo, roca, bico...). Aqui ficam as contas; a ordem
das telas (relatorio, evento, Enem...) e do engine.py.

Moeda: reais inteiros. Os valores de programas (Bolsa Familia, Pe-de-Meia) sao
aproximacoes de jogo, nao os valores oficiais do ano.
"""

from .content import (
    ACOES, DADOS_VIAS, ETAPAS_ESCOLA, FREQ_MIN, IDADE_MIN_BICO, MAXIMO,
    ORCAMENTO_BASE, PADRAO, REGIOES, AREAS,
)
from .util import State, arred, clamp

# ---- economia
CONSUMO_FAMILIA = 27.0       # comida que a familia gasta por ano
DIVISOR_RENDA = 150.0        # cada R$150 de renda vira 1 ponto de comida
FUNDO_ESCOLA = 0.35          # fatia do Bolsa Familia e do bico que sobra pro seu estudo (o resto e da casa)
BOLSA_FAMILIA = 1200         # exige frequencia
PE_DE_MEIA_MENSAL = 1800     # 9 parcelas de R$200, no ensino medio, com frequencia
PE_DE_MEIA_POUPANCA = 1000   # por ano aprovado, so liberada ao concluir e fazer o Enem
PE_DE_MEIA_ENEM = 200
BICO_PAGA = 650
ESTAGIO_PAGA = 1000
FACULDADE_VIDA = 2600
MORADIA = 3000               # morar perto da federal quando ela fica longe do acampamento
OAB_VIDA = 2400
OAB_TAXA = 280
MUDANCA = 600

# ---- aprendizado
GANHO_ESCOLA = 1.25
GANHO_ESCOLA_REDACAO = 0.7
GANHO_CURSINHO = 1.7
GANHO_CURSINHO_REDACAO = 1.1
GANHO_ESTUDO = 2.1
SOBRA_ESTUDO = 0.18          # estudar uma area ajuda um pouco as outras
ESQUECIMENTO = 0.01
GANHO_AULA = 1.9
GANHO_ESTUDO_DIREITO = 2.3
GANHO_ESTAGIO = 3.0
GANHO_EXTENSAO = 3.0

FOTO = ("saude", "animo", "comida", "luta", "dinheiro", "terra_ameaca")


def foto(e: State) -> dict:
    """Retrato dos numeros do jogador, pra mostrar 'antes -> depois' no relatorio."""
    f = {k: arred(e[k], 1) for k in FOTO}
    f.update({a: arred(e["saber"][a], 1) for a in AREAS})
    f.update({k: arred(e[k], 1) for k in ("juridico", "pratica", "rede")})
    return f


def eficiencia(e: State) -> float:
    """Quanto rende uma hora de estudo: corpo e cabeca descansados rendem mais."""
    base = 0.55 + e["animo"] / 250 + e["saude"] / 400
    if e["etapa"] in ETAPAS_ESCOLA and e["comida"] < 35:
        base -= 0.15
    return clamp(base, 0.4, 1.15)


def dim(k: float) -> float:
    """Retorno decrescente: quem ja sabe muito aprende mais devagar."""
    return max(0.4, 1 - k / 180)


def orcamento(e: State) -> int:
    b = ORCAMENTO_BASE
    if e["etapa"] == "faculdade":
        b += DADOS_VIAS[e["via"]].tempo_extra
    if e["saude"] < 30:
        b -= 2
    return b


def maximo(e: State, acao: str) -> int:
    if acao == "bico" and e["idade"] < IDADE_MIN_BICO:
        return 0
    if acao == "estagio" and e["etapa"] == "faculdade" and e["serie"] < 2:
        return 0
    return MAXIMO[acao]


def acao_bloqueada(e: State, acao: str) -> str:
    """Chave de texto com o motivo, ou '' se a acao esta liberada."""
    if acao == "bico" and e["idade"] < IDADE_MIN_BICO:
        return "bloqueio.bico_idade"
    if acao == "estagio" and e["etapa"] == "faculdade" and e["serie"] < 2:
        return "bloqueio.estagio_serie"
    return ""


def area_mais_fraca(e: State) -> str:
    return min(AREAS, key=lambda a: e["saber"][a])


def plano_padrao(e: State) -> dict:
    """Plano sugerido: o do tipo da etapa, ajustado ao orcamento e aos bloqueios."""
    et = e["etapa"]
    if et not in PADRAO:  # advocacia: nao ha plano de tempo, so as acoes do caso
        return {"acoes": {}, "foco": area_mais_fraca(e)}
    acoes = {a: min(v, maximo(e, a)) for a, v in PADRAO[et].items()}
    return {"acoes": _ajustar(e, acoes), "foco": area_mais_fraca(e)}


def _ajustar(e: State, acoes: dict) -> dict:
    """Garante soma == orcamento: tira de bico/roca e poe em descanso/estudo."""
    b = orcamento(e)
    sobra = b - sum(acoes.values())
    tirar = [a for a in ("bico", "roca", "comunidade", "extensao", "estagio", "estudo", "descanso") if a in acoes]
    poe = [a for a in ("descanso", "estudo") if a in acoes]
    while sobra < 0 and any(acoes[a] > 0 for a in tirar):
        for a in tirar:
            if sobra < 0 and acoes[a] > 0:
                acoes[a] -= 1
                sobra += 1
    while sobra > 0 and any(acoes[a] < maximo(e, a) for a in poe):
        for a in poe:
            if sobra > 0 and acoes[a] < maximo(e, a):
                acoes[a] += 1
                sobra -= 1
    return acoes


def normalizar_plano(e: State, plano: dict | None) -> dict:
    """Aceita qualquer plano vindo do navegador e devolve um plano valido."""
    plano = plano or {}
    validas = ACOES[e["etapa"]]
    bruto = plano.get("acoes", {}) or {}
    acoes = {}
    for a in validas:
        try:
            v = int(bruto.get(a, 0))
        except (TypeError, ValueError):
            v = 0
        acoes[a] = max(0, min(v, maximo(e, a)))
    excesso = sum(acoes.values()) - orcamento(e)
    for a in reversed(validas):
        while excesso > 0 and acoes[a] > 0:
            acoes[a] -= 1
            excesso -= 1
    foco = plano.get("foco")
    if foco not in AREAS:
        foco = area_mais_fraca(e)
    return {"acoes": acoes, "foco": foco}


def economia(e: State, a: dict) -> dict:
    """Renda, custo e variacao de comida do plano `a` (so as contas, sem sortear nada)."""
    et = e["etapa"]
    reg = REGIOES[e["regiao"]]
    g = a.get
    if et in ETAPAS_ESCOLA:
        bico = BICO_PAGA * g("bico", 0)
        bolsa = BOLSA_FAMILIA if et in ("fundamental", "medio") and g("escola", 0) >= FREQ_MIN else 0
        pdm = PE_DE_MEIA_MENSAL if et == "medio" and g("escola", 0) >= FREQ_MIN else 0
        renda = bico + bolsa + pdm
        custo = reg.custo_escola + {"fundamental": 150, "medio": 1100, "cursinho": 0}[et]
        fundo = FUNDO_ESCOLA * (bico + bolsa) + pdm
        d_comida = 5.5 * g("roca", 0) * reg.roca + renda / DIVISOR_RENDA - CONSUMO_FAMILIA
        fad = g("estudo", 0) + g("roca", 0) + g("bico", 0) + g("comunidade", 0)
    elif et == "faculdade":
        via = DADOS_VIAS[e["via"]]
        renda = via.auxilio + ESTAGIO_PAGA * g("estagio", 0) + BICO_PAGA * g("bico", 0)
        custo = FACULDADE_VIDA + via.custo_extra + (MORADIA if via.publica and reg.univ_longe else 0)
        fundo = renda
        d_comida = 0.0
        fad = g("estudo", 0) + g("estagio", 0) + g("extensao", 0) + g("bico", 0)
    else:  # oab
        renda = ESTAGIO_PAGA * g("estagio", 0) + BICO_PAGA * g("bico", 0)
        custo = OAB_VIDA + OAB_TAXA
        fundo = renda
        d_comida = 0.0
        fad = g("estudo", 0) + g("estagio", 0) + g("bico", 0)
    return {"renda": int(renda), "fundo": int(fundo), "custo": int(custo), "d_comida": d_comida, "fad": fad}


def _vitais_corpo(e: State, a: dict, eco: dict) -> None:
    if e["etapa"] in ETAPAS_ESCOLA:
        e["comida"] = clamp(e["comida"] + eco["d_comida"])
    else:
        e["comida"] = 60.0
    ds = 4 + 4 * a.get("descanso", 0) - 1.5 * eco["fad"]
    if e["comida"] < 30:
        ds -= 7
    elif e["comida"] >= 70:
        ds += 2
    ds -= max(0.0, e["saude"] - 75) * 0.1
    e["saude"] = clamp(e["saude"] + ds)


def _vitais_animo(e: State, a: dict, aprovado: bool) -> None:
    com = a.get("comunidade", 0)
    da = -2 + 3 * min(com, 2) + 2.2 * a.get("descanso", 0) + (3 if aprovado else -10)
    if e["comida"] < 30:
        da -= 5
    elif e["comida"] > 70:
        da += 2
    da -= (e["animo"] - 55) * 0.12
    e["animo"] = clamp(e["animo"] + da)
    e["luta"] = clamp(e["luta"] + 5 * com + 4 * a.get("extensao", 0))


def esperado(e: State) -> float:
    """O que a escola espera de saber medio nesta serie (global: 1..9 fund, 10..12 medio)."""
    g = e["serie"] + (9 if e["etapa"] == "medio" else 0)
    return 20 + 4.2 * g


def media_saber(e: State) -> float:
    return sum(e["saber"][a] for a in AREAS) / len(AREAS)


def boletim(e: State) -> float:
    """Nota de 0 a 10; 5.0 aprova. Igual ao esperado da serie vale 5.6."""
    return clamp(5 + (media_saber(e) - esperado(e)) / 5 + 0.6, 0, 10)


def ano_escola(e: State, plano: dict) -> dict:
    """Fundamental, medio ou cursinho. Muda `e` e devolve o relatorio do ano."""
    et = e["etapa"]
    a = plano["acoes"]
    foco = plano["foco"]
    antes = foto(e)
    eco = economia(e, a)

    e["dinheiro"] += eco["fundo"]
    pago = min(max(e["dinheiro"], 0), eco["custo"])
    falta = 1 - pago / eco["custo"] if eco["custo"] else 0.0
    e["dinheiro"] = max(0, e["dinheiro"] - eco["custo"])

    ef = eficiencia(e) * (1 - 0.25 * falta)
    internado = e["saude"] <= 8
    if internado:
        ef *= 0.4

    reg = REGIOES[e["regiao"]]
    if et == "cursinho":
        base_pts, g_base, g_red, q = a.get("cursinho", 0), GANHO_CURSINHO, GANHO_CURSINHO_REDACAO, 1.0
    else:
        base_pts, g_base, g_red, q = a.get("escola", 0), GANHO_ESCOLA, GANHO_ESCOLA_REDACAO, reg.escola_q
    estudo = a.get("estudo", 0)
    for ar in AREAS:
        k = e["saber"][ar] * (1 - ESQUECIMENTO)
        d = dim(k)
        ganho = (g_red if ar == "redacao" else g_base) * base_pts * q * ef * d
        if ar == foco:
            ganho += GANHO_ESTUDO * estudo * ef * d
        else:
            ganho += SOBRA_ESTUDO * GANHO_ESTUDO * estudo * ef * d
        e["saber"][ar] = clamp(k + ganho)

    _vitais_corpo(e, a, eco)
    internado = internado or e["saude"] <= 8

    aprovado, motivo = True, ""
    tem_boletim = et != "cursinho"
    if tem_boletim:
        if a.get("escola", 0) < FREQ_MIN:
            aprovado, motivo = False, "faltas"
        elif internado:
            aprovado, motivo = False, "saude"
        elif boletim(e) < 5.0:
            aprovado, motivo = False, "notas"

    if et == "medio" and aprovado:
        e["poupanca_pdm"] += PE_DE_MEIA_POUPANCA

    _vitais_animo(e, a, aprovado)
    # Pressao do dono sobre o acampamento: cresce sozinha, a comunidade segura.
    e["terra_ameaca"] = clamp(
        e["terra_ameaca"] + 4 + reg.dono / 14 - e["luta"] / 30 - 2 * a.get("comunidade", 0))

    return {
        "tipo": "relatorio", "etapa": et, "serie": e["serie"], "aprovado": aprovado, "motivo": motivo,
        "tem_boletim": tem_boletim, "boletim": arred(boletim(e), 1), "esperado": arred(esperado(e), 1),
        "media": arred(media_saber(e), 1), "renda": eco["renda"], "fundo": eco["fundo"], "custo": eco["custo"],
        "falta_dinheiro": falta > 0.01, "antes": antes, "depois": foto(e),
        "idade": e["idade"], "ano": e["ano"],
    }


def esperado_faculdade(serie: int) -> float:
    return 12.0 * serie - 4


def ano_faculdade(e: State, plano: dict) -> dict:
    a = plano["acoes"]
    via = DADOS_VIAS[e["via"]]
    antes = foto(e)
    eco = economia(e, a)
    e["dinheiro"] += eco["renda"] - eco["custo"]
    e["divida"] += via.divida_ano

    ef = eficiencia(e)
    if e["saude"] <= 8:
        ef *= 0.4
    d = dim(e["juridico"])
    e["juridico"] = clamp(e["juridico"] + (
        GANHO_AULA * a.get("aulas", 0) * via.qualidade + GANHO_ESTUDO_DIREITO * a.get("estudo", 0)) * ef * d)
    dp = dim(e["pratica"])
    e["pratica"] = clamp(e["pratica"] + (
        GANHO_ESTAGIO * a.get("estagio", 0) + GANHO_EXTENSAO * a.get("extensao", 0)) * ef * dp)
    e["rede"] = clamp(e["rede"] + (
        2.2 * a.get("estagio", 0) + 3.5 * a.get("extensao", 0)
        + 0.8 * a.get("aulas", 0) * (1.0 if via.publica else 0.6)) * ef)

    _vitais_corpo(e, a, eco)
    aprovado, motivo = True, ""
    if a.get("aulas", 0) < FREQ_MIN:
        aprovado, motivo = False, "faltas"
    elif e["saude"] <= 8:
        aprovado, motivo = False, "saude"
    elif e["juridico"] < esperado_faculdade(e["serie"]):
        aprovado, motivo = False, "notas"
    _vitais_animo(e, a, aprovado)
    e["terra_ameaca"] = clamp(
        e["terra_ameaca"] + 4 + REGIOES[e["regiao"]].dono / 14 - e["luta"] / 30)

    return {
        "tipo": "relatorio", "etapa": "faculdade", "serie": e["serie"], "aprovado": aprovado, "motivo": motivo,
        "tem_boletim": False, "boletim": 0, "esperado": esperado_faculdade(e["serie"]),
        "media": arred(e["juridico"], 1), "renda": eco["renda"], "fundo": eco["fundo"], "custo": eco["custo"],
        "falta_dinheiro": e["dinheiro"] < 0, "antes": antes, "depois": foto(e),
        "idade": e["idade"], "ano": e["ano"],
    }


def ano_oab_preparo(e: State, plano: dict) -> dict:
    """Estudo, estagio e trabalho do ano. A prova em si e sorteada pelo engine."""
    a = plano["acoes"]
    antes = foto(e)
    eco = economia(e, a)
    e["dinheiro"] += eco["renda"] - eco["custo"]
    ef = eficiencia(e)
    e["juridico"] = clamp(e["juridico"] + 1.5 * a.get("estudo", 0) * ef * dim(e["juridico"]))
    e["pratica"] = clamp(e["pratica"] + 2.5 * a.get("estagio", 0) * ef * dim(e["pratica"]))
    e["rede"] = clamp(e["rede"] + 1.5 * a.get("estagio", 0) * ef)
    _vitais_corpo(e, a, eco)
    _vitais_animo(e, a, True)
    e["terra_ameaca"] = clamp(
        e["terra_ameaca"] + 4 + REGIOES[e["regiao"]].dono / 14 - e["luta"] / 30)
    return {
        "tipo": "relatorio", "etapa": "oab", "serie": e["serie"], "aprovado": True, "motivo": "",
        "tem_boletim": False, "boletim": 0, "esperado": 0, "media": arred(e["juridico"], 1),
        "renda": eco["renda"], "fundo": eco["fundo"], "custo": eco["custo"], "falta_dinheiro": e["dinheiro"] < 0,
        "antes": antes, "depois": foto(e), "idade": e["idade"], "ano": e["ano"],
    }
