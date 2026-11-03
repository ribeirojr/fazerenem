"""Orquestra o jogo: novo jogo, um ano, as telas pendentes e o painel.

O estado inteiro e um dict JSON puro. Isso de proposito: o que atravessa a
ponte pro navegador (e volta) e identico ao que fica no localStorage, entao
nao existe campo que "se perde" na ida e volta.

Depois de jogar_ano(), o estado traz uma `fila` de telas (relatorio, evento,
Enem, escolha de vias...). A UI mostra a cabeca da fila e chama responder().
So quando a fila esvazia da pra jogar o proximo ano.
"""

import copy

from . import caso, enem
from .ano import (
    MUDANCA, PE_DE_MEIA_ENEM, acao_bloqueada, ano_escola, ano_faculdade,
    ano_oab_preparo, area_mais_fraca, boletim, economia, eficiencia, esperado,
    maximo, media_saber, normalizar_plano, orcamento, plano_padrao,
)
from .content import (
    ACOES, ACOES_CASO, AREAS, AREAS_OBJETIVAS, ANO_INICIAL, DADOS_VIAS, ETAPAS_CASO,
    ETAPAS_ESCOLA, EVENTOS, EVENTOS_FIXOS, FREQ_MIN, IDADE_INICIAL, IDADE_LIMITE,
    MAX_ACOES_CASO, ORDEM_REGIOES, REGIOES, SERIES, TODOS_EVENTOS, TRILHA, VIAS,
)
from .rng import stream
from .util import State, clamp, log

SALARIO_ADVOGADO = 2500
CHANCE_EVENTO = 0.6
LIMITE_APERTO = -3000

CONDICOES = {
    "": lambda e: True,
    "serie2": lambda e: e["serie"] >= 2,
    "publica_longe": lambda e: bool(e["via"]) and DADOS_VIAS[e["via"]].publica
                                and REGIOES[e["regiao"]].univ_longe,
}


# ------------------------------------------------------------------ estado

def _estado_base(seed: int, regiao: str, nome: str, genero: str) -> State:
    rng = stream(seed, 0, "inicio")
    return {
        "versao": 1, "seed": int(seed), "t": 0,
        "nome": nome, "genero": genero if genero in ("m", "f") else "f", "regiao": regiao,
        "idade": IDADE_INICIAL, "ano": ANO_INICIAL,
        "etapa": "fundamental", "serie": 1,
        "saber": {a: round(rng.uniform(17, 26), 1) for a in AREAS},
        "saude": 80.0, "animo": 70.0, "comida": 62.0, "luta": 12.0,
        "dinheiro": 600, "divida": 0, "poupanca_pdm": 0,
        "exp_prova": 0.0, "treineiro_feito": 0,
        "terra_ameaca": 20.0, "despejos": 0, "familia": 5,
        "juridico": 0.0, "pratica": 0.0, "rede": 0.0,
        "via": "", "enem_tentativas": 0, "oab_tentativas": 0, "oab_fase1": False,
        "reprovacoes": 0, "ultima_prova": {},
        "caso": {}, "fila": [], "log": [], "fim": {},
    }


def novo_jogo(seed: int, regiao: str, nome: str = "", genero: str = "f") -> State:
    if regiao not in REGIOES:
        regiao = ORDEM_REGIOES[0]
    nome = (nome or "").strip()[:24] or ("Maria" if genero != "m" else "João")
    e = _estado_base(seed, regiao, nome, genero)
    log(e, "log.inicio", regiao=regiao)
    return e


def migrar(e: State) -> State:
    """Preenche campos que saves antigos nao tem (sempre com .setdefault, nunca apagando)."""
    base = _estado_base(e.get("seed", 1), e.get("regiao", ORDEM_REGIOES[0]),
                        e.get("nome", ""), e.get("genero", "f"))
    for k, v in base.items():
        e.setdefault(k, v)
    for a in AREAS:
        e["saber"].setdefault(a, 20.0)
    return e


# ------------------------------------------------------------------ efeitos e eventos

def aplicar_efeitos(e: State, efeitos: dict) -> None:
    for k, v in efeitos.items():
        if k == "dinheiro":
            e["dinheiro"] += int(v)
        elif k == "despejos":
            e["despejos"] += int(v)
        elif k == "saber":
            for a in AREAS_OBJETIVAS:
                e["saber"][a] = clamp(e["saber"][a] + v)
        elif k.startswith("saber_"):
            a = k[len("saber_"):]
            e["saber"][a] = clamp(e["saber"][a] + v)
        elif k == "exp_prova":
            e["exp_prova"] = clamp(e["exp_prova"] + v, 0, enem.EXP_MAXIMA)
        else:
            e[k] = clamp(e[k] + v)


def _sortear_evento(e: State, rng) -> str:
    if rng.random() > CHANCE_EVENTO:
        return ""
    pool = [ev for ev in EVENTOS.values()
            if e["etapa"] in ev.etapas and CONDICOES[ev.cond](e)]
    if not pool:
        return ""
    total = sum(ev.peso for ev in pool)
    x = rng.random() * total
    for ev in pool:
        x -= ev.peso
        if x <= 0:
            return ev.id
    return pool[-1].id


def _item_evento(ev_id: str) -> dict:
    ev = TODOS_EVENTOS[ev_id]
    return {"tipo": "evento", "id": ev.id,
            "opcoes": [{"id": o.id, "custo": o.custo, "efeitos": dict(o.efeitos)} for o in ev.opcoes]}


# ------------------------------------------------------------------ o ano

def _fluxo_enem(e: State, fila: list) -> None:
    """Prova do Enem do ano + escolha das vias (Sisu / ProUni / Fies)."""
    p = enem.prova(e, "enem")
    resgate = 0
    if e["poupanca_pdm"] > 0:
        resgate = e["poupanca_pdm"] + PE_DE_MEIA_ENEM
        e["dinheiro"] += resgate
        e["poupanca_pdm"] = 0
        log(e, "log.pe_de_meia", v=resgate)
    e["ultima_prova"] = p
    fila.append({"tipo": "enem", "prova": p, "resgate": resgate, "tentativa": e["enem_tentativas"] + 1})
    fila.append({"tipo": "vias", "prova": p, "ref": dict(enem.CORTE_BASE),
                 "minimo": enem.MEDIA_MINIMA,
                 "min_ok": p["media"] >= enem.MEDIA_MINIMA and p["redacao"] > 0})


def _exame_oab(e: State, plano: dict, fila: list) -> None:
    rng = stream(e["seed"], e["t"], "oab")
    estudo = plano["acoes"].get("estudo", 0)
    e["oab_tentativas"] += 1
    f1 = e["oab_fase1"]
    novo_f1 = None
    if not f1:
        novo_f1 = (e["juridico"] * 0.62 + estudo * 3.4 + rng.gauss(0, 5)) >= 56
        e["oab_fase1"] = f1 = novo_f1
    f2 = None
    if f1:
        f2 = (e["pratica"] * 0.45 + e["juridico"] * 0.28 + estudo * 1.5 + rng.gauss(0, 5)) >= 41
    passou = bool(f1 and f2)
    fila.append({"tipo": "oab", "fase1": novo_f1, "fase1_antes": bool(f1 and novo_f1 is None),
                 "fase2": f2, "passou": passou, "tentativa": e["oab_tentativas"]})
    if passou:
        e["etapa"], e["serie"] = "advocacia", 1
        e["animo"] = clamp(e["animo"] + 12)
        caso.iniciar(e)
        log(e, "log.oab_passou")


def _transicao(e: State, rel: dict, plano: dict, fila: list) -> None:
    et = e["etapa"]
    ok = rel["aprovado"]
    if not ok:
        e["reprovacoes"] += 1
        log(e, "log.reprovou", etapa=et, motivo=rel["motivo"])
    if et == "fundamental":
        if ok:
            e["serie"] += 1
            if e["serie"] > SERIES["fundamental"]:
                e["etapa"], e["serie"] = "medio", 1
                log(e, "log.entrou_medio")
    elif et == "medio":
        if ok and e["serie"] < SERIES["medio"]:
            e["serie"] += 1
            fila.append({"tipo": "treineiro", "taxa": enem.TAXA_TREINEIRO, "numero": e["treineiro_feito"] + 1})
        elif ok:
            _fluxo_enem(e, fila)
    elif et == "cursinho":
        e["serie"] += 1
        _fluxo_enem(e, fila)
    elif et == "faculdade":
        if ok:
            e["serie"] += 1
            if e["serie"] > SERIES["faculdade"]:
                e["etapa"], e["serie"] = "oab", 1
                log(e, "log.formou")
    elif et == "oab":
        _exame_oab(e, plano, fila)


def _resumo_fim(e: State, tipo: str) -> dict:
    pontos = (1000 + e["luta"] * 3 - max(0, e["idade"] - 24) * 25 - e["divida"] / 50
              - e["despejos"] * 60 + (300 if tipo == "vitoria" else 0))
    return {
        "tipo": tipo, "idade": e["idade"], "ano": e["ano"], "pontos": max(0, int(pontos)),
        "despejos": e["despejos"], "divida": e["divida"], "luta": int(e["luta"]), "via": e["via"],
        "reprovacoes": e["reprovacoes"], "enem_tentativas": e["enem_tentativas"],
        "oab_tentativas": e["oab_tentativas"], "anos": e["t"], "regiao": e["regiao"],
        "familia": e["familia"],
    }


def jogar_ano(e: State, plano: dict | None = None) -> State:
    e = migrar(copy.deepcopy(e))
    if e["fila"]:
        raise ValueError("fila_pendente")
    if e["fim"]:
        raise ValueError("jogo_encerrado")
    et = e["etapa"]
    fila: list = []

    if et == "advocacia":
        e["dinheiro"] += SALARIO_ADVOGADO
        rel = caso.jogar_etapa(e, list((plano or {}).get("casos", [])))
        fila.append(rel)
        if rel["fim"]:
            e["fim"] = _resumo_fim(e, rel["fim"])
    else:
        # Sem plano (ou plano sem acoes) vale o plano sugerido, nao "nao fazer nada".
        if not plano or not plano.get("acoes"):
            plano = plano_padrao(e)
        plano = normalizar_plano(e, plano)
        if et in ETAPAS_ESCOLA:
            rel = ano_escola(e, plano)
        elif et == "faculdade":
            rel = ano_faculdade(e, plano)
        else:
            rel = ano_oab_preparo(e, plano)
        fila.append(rel)

        rng = stream(e["seed"], e["t"], "evento")
        if e["terra_ameaca"] >= 100:
            ev_id = "despejo"
        elif et in ("faculdade", "oab") and e["dinheiro"] < LIMITE_APERTO:
            ev_id = "aperto"
        else:
            ev_id = _sortear_evento(e, rng)
        if ev_id:
            fila.append(_item_evento(ev_id))
        _transicao(e, rel, plano, fila)

    e["t"] += 1
    e["idade"] += 1
    e["ano"] += 1
    if not e["fim"] and e["etapa"] != "advocacia" and e["idade"] >= IDADE_LIMITE:
        e["fim"] = _resumo_fim(e, "tempo")
    e["fila"] = fila
    return e


# ------------------------------------------------------------------ responder as telas

def _vias_validas(e: State, escolhidas) -> list[str]:
    return [v for v in VIAS if v in set(escolhidas or [])]


def _entrar_na_faculdade(e: State, via: str) -> None:
    e["via"] = via
    e["etapa"], e["serie"] = "faculdade", 1
    e["animo"] = clamp(e["animo"] + 15)
    if DADOS_VIAS[via].publica and REGIOES[e["regiao"]].univ_longe:
        e["dinheiro"] -= MUDANCA
    log(e, "log.aprovado", via=via)


def responder(e: State, resp: dict | None = None) -> State:
    e = migrar(copy.deepcopy(e))
    resp = resp or {}
    if not e["fila"]:
        raise ValueError("fila_vazia")
    head = e["fila"][0]
    tipo = head["tipo"]

    if tipo == "evento":
        ev = TODOS_EVENTOS[head["id"]]
        escolha = resp.get("opcao", "")
        op = next((o for o in ev.opcoes if o.id == escolha), None)
        if op is None or op.custo > max(e["dinheiro"], 0):
            op = next((o for o in ev.opcoes if o.custo <= max(e["dinheiro"], 0)), ev.opcoes[-1])
        e["dinheiro"] -= op.custo
        aplicar_efeitos(e, op.efeitos)
        log(e, "log.evento", ev=ev.id, op=op.id)
        if len(ev.opcoes) == 1:
            e["fila"].pop(0)
        else:
            e["fila"][0] = {"tipo": "evento_res", "id": ev.id, "opcao": op.id,
                            "efeitos": dict(op.efeitos), "custo": op.custo}
    elif tipo == "treineiro":
        if resp.get("inscrever") and e["dinheiro"] >= head["taxa"]:
            e["dinheiro"] -= head["taxa"]
            p = enem.prova(e, f"treino{head['numero']}")
            ganho = 16 if head["numero"] == 1 else 10
            e["treineiro_feito"] += 1
            e["exp_prova"] = clamp(e["exp_prova"] + ganho, 0, enem.EXP_MAXIMA)
            e["animo"] = clamp(e["animo"] + 3)
            log(e, "log.treineiro")
            e["fila"][0] = {"tipo": "treino_res", "prova": p, "ganho": ganho, "taxa": head["taxa"]}
        else:
            e["fila"].pop(0)
    elif tipo == "vias":
        p = head["prova"]
        escolhidas = _vias_validas(e, resp.get("vias"))
        res = enem.resolver_vias(e, p, escolhidas)
        e["enem_tentativas"] += 1
        if res["via"]:
            _entrar_na_faculdade(e, res["via"])
        else:
            e["animo"] = clamp(e["animo"] - 8)
            if e["etapa"] == "medio":
                e["etapa"], e["serie"] = "cursinho", 1
            log(e, "log.reprovado_enem")
        e["fila"][0] = {"tipo": "admissao", "prova": p, "res": res}
    else:
        # relatorio, enem, treino_res, evento_res, admissao, oab, caso: so confirmar
        e["fila"].pop(0)
    return e


# ------------------------------------------------------------------ painel e previsao

def _trilha(e: State) -> list[dict]:
    et, serie = e["etapa"], e["serie"]
    atual = {
        "fundamental": "fundamental", "medio": "enem" if serie >= 3 else "medio",
        "cursinho": "enem", "faculdade": "faculdade", "oab": "oab", "advocacia": "terra",
    }[et]
    i = TRILHA.index(atual)
    if e["fim"] and e["fim"]["tipo"] == "vitoria":
        i = len(TRILHA)
    return [{"id": p, "estado": "feito" if k < i else ("atual" if k == i else "futuro")}
            for k, p in enumerate(TRILHA)]


def _info_caso(e: State) -> dict:
    c = e["caso"]
    idx = min(c["idx"], len(ETAPAS_CASO) - 1)
    return {
        "etapa": ETAPAS_CASO[idx], "idx": idx, "defesa": c["defesa"], "acusacao": c["acusacao"],
        "vitorias": c["vitorias"], "max_acoes": MAX_ACOES_CASO, "acoes": caso.previsao(e),
        "etapas": list(ETAPAS_CASO), "dinheiro": e["dinheiro"],
    }


def painel(e: State) -> dict:
    e = migrar(copy.deepcopy(e))
    et = e["etapa"]
    p = {
        "etapa": et, "serie": e["serie"], "idade": e["idade"], "ano": e["ano"],
        "series_total": SERIES.get(et, 0), "trilha": _trilha(e),
        "pode_jogar": not e["fila"] and not e["fim"],
        "orcamento": 0, "acoes": [], "areas": list(AREAS) if et in ETAPAS_ESCOLA else [],
        "foco": area_mais_fraca(e), "esperado": 0, "media": round(media_saber(e), 1),
        "eficiencia": round(eficiencia(e), 2),
        "mostra_comida": et in ETAPAS_ESCOLA,
    }
    if et in ETAPAS_ESCOLA:
        p["esperado"] = round(esperado(e), 1) if et != "cursinho" else 0
        p["boletim"] = round(boletim(e), 1)
    if et == "advocacia":
        p["caso"] = _info_caso(e)
    elif not e["fim"]:
        pad = plano_padrao(e)
        p["orcamento"] = orcamento(e)
        p["foco"] = pad["foco"]
        p["acoes"] = [{"id": a, "max": maximo(e, a), "padrao": pad["acoes"].get(a, 0),
                       "bloqueio": acao_bloqueada(e, a)} for a in ACOES[et]]
    return p


def previsao(e: State, plano: dict | None) -> dict:
    """O que o plano rende (sem sortear nada) e os avisos que a tela mostra enquanto o jogador mexe."""
    e = migrar(copy.deepcopy(e))
    et = e["etapa"]
    if et == "advocacia":
        return {"restante": 0, "valido": True, "avisos": []}
    bruto = (plano or {}).get("acoes", {}) or {}
    a = {}
    for k in ACOES[et]:
        try:
            v = int(bruto.get(k, 0))
        except (TypeError, ValueError):
            v = 0
        a[k] = max(0, min(v, maximo(e, k)))
    restante = orcamento(e) - sum(a.values())
    eco = economia(e, a)
    avisos = []
    if restante < 0:
        avisos.append({"k": "aviso.excesso", "v": {"n": -restante}, "nivel": "perigo"})
    elif restante > 0:
        avisos.append({"k": "aviso.sobra", "v": {"n": restante}, "nivel": "info"})
    if et in ("fundamental", "medio") and a.get("escola", 0) < FREQ_MIN:
        avisos.append({"k": "aviso.faltas", "v": {"min": FREQ_MIN}, "nivel": "perigo"})
    if et == "faculdade" and a.get("aulas", 0) < FREQ_MIN:
        avisos.append({"k": "aviso.aulas", "v": {"min": FREQ_MIN}, "nivel": "perigo"})
    if et in ETAPAS_ESCOLA:
        if e["comida"] + eco["d_comida"] < 30:
            avisos.append({"k": "aviso.fome", "v": {}, "nivel": "atencao"})
        if e["dinheiro"] + eco["fundo"] < eco["custo"]:
            avisos.append({"k": "aviso.sem_dinheiro", "v": {}, "nivel": "atencao"})
    elif e["dinheiro"] + eco["renda"] - eco["custo"] < 0:
        avisos.append({"k": "aviso.aperto", "v": {}, "nivel": "atencao"})
    if e["saude"] + 4 + 4 * a.get("descanso", 0) - 1.5 * eco["fad"] < 25:
        avisos.append({"k": "aviso.cansaco", "v": {}, "nivel": "atencao"})
    return {"restante": restante, "valido": restante >= 0, "renda": eco["renda"],
            "fundo": eco["fundo"], "custo": eco["custo"], "avisos": avisos}
