"""Regras da simulacao: determinismo, ida e volta em JSON, fila de telas e cada etapa."""

import ast
import json
from pathlib import Path

import pytest

from lonatoga.sim import ano, caso, enem, engine
from lonatoga.sim.content import (
    ACOES, AREAS, EVENTOS, EVENTOS_FIXOS, FREQ_MIN, REGIOES, TODOS_EVENTOS, VIAS,
)
from lonatoga.sim.rng import stream

RAIZ = Path(__file__).resolve().parent.parent


def novo(seed=7, regiao="pontal"):
    return engine.novo_jogo(seed, regiao, "Teste", "f")


def limpar_fila(e, vias=("ampla", "cota", "prouni")):
    while e["fila"]:
        h = e["fila"][0]
        if h["tipo"] == "evento":
            e = engine.responder(e, {"opcao": h["opcoes"][0]["id"]})
        elif h["tipo"] == "vias":
            e = engine.responder(e, {"vias": list(vias)})
        else:
            e = engine.responder(e, {})
    return e


def jogar_ate(e, pred, plano_fn=None, limite=60):
    for _ in range(limite):
        if pred(e):
            return e
        e = limpar_fila(e)
        if pred(e):
            return e
        e = engine.jogar_ano(e, plano_fn(e) if plano_fn else ano.plano_padrao(e))
    raise AssertionError("nao chegou la")


# ------------------------------------------------------------------ RNG e pureza

def test_rng_e_estavel_entre_chamadas():
    a = [stream(1, 2, "x").random() for _ in range(3)]
    b = [stream(1, 2, "x").random() for _ in range(3)]
    assert a == b
    assert stream(1, 2, "x").random() != stream(1, 2, "y").random()


def test_sim_nao_usa_random_global_nem_hash():
    """Mesmo seed + mesmas escolhas = mesmo jogo, em qualquer processo."""
    for p in (RAIZ / "py" / "lonatoga" / "sim").glob("*.py"):
        arvore = ast.parse(p.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Name) and no.func.id == "hash":
                raise AssertionError(f"{p.name} chama hash()")
            if isinstance(no, ast.Attribute) and isinstance(no.value, ast.Name) \
                    and no.value.id == "random" and p.name != "rng.py":
                raise AssertionError(f"{p.name} usa random.{no.attr}")


def test_mesmo_seed_e_mesmas_escolhas_geram_o_mesmo_jogo():
    def rodar():
        e = novo(11)
        for _ in range(12):
            e = limpar_fila(e)
            e = engine.jogar_ano(e, ano.plano_padrao(e))
        return e
    assert rodar() == rodar()


def test_seeds_diferentes_geram_jogos_diferentes():
    assert novo(1)["saber"] != novo(2)["saber"]


# ------------------------------------------------------------------ estado e JSON

def test_estado_inteiro_atravessa_json_sem_perder_nada():
    """O que vai pro navegador e volta (localStorage) tem que ser igual ao estado."""
    e = novo()
    for _ in range(20):
        e = engine.jogar_ano(e, ano.plano_padrao(e)) if not e["fila"] else limpar_fila(e)
        assert json.loads(json.dumps(e)) == e


def test_migrar_completa_campos_que_faltam():
    e = novo()
    antigo = {k: v for k, v in e.items() if k not in ("poupanca_pdm", "ultima_prova", "oab_fase1")}
    assert "poupanca_pdm" not in antigo
    novo_e = engine.migrar(antigo)
    assert novo_e["poupanca_pdm"] == 0 and novo_e["oab_fase1"] is False


def test_jogar_ano_nao_muda_o_estado_recebido():
    e = novo()
    copia = json.loads(json.dumps(e))
    engine.jogar_ano(e, ano.plano_padrao(e))
    assert e == copia


def test_nome_vazio_ganha_nome_padrao_e_nome_longo_e_cortado():
    assert engine.novo_jogo(1, "pontal", "", "f")["nome"] == "Maria"
    assert engine.novo_jogo(1, "pontal", "", "m")["nome"] == "João"
    assert len(engine.novo_jogo(1, "pontal", "x" * 80, "f")["nome"]) == 24


def test_regiao_invalida_cai_na_primeira():
    assert engine.novo_jogo(1, "marte", "A", "f")["regiao"] == "pontal"


# ------------------------------------------------------------------ plano do ano

def test_plano_padrao_soma_exatamente_o_orcamento_em_toda_etapa():
    for etapa in ACOES:
        e = novo()
        e["etapa"], e["serie"], e["idade"] = etapa, 1, 18
        e["via"] = "cota"
        p = ano.plano_padrao(e)
        assert sum(p["acoes"].values()) == ano.orcamento(e), etapa


def test_plano_nao_passa_do_orcamento_nem_do_maximo():
    e = novo()
    p = ano.normalizar_plano(e, {"acoes": {"escola": 99, "estudo": 99, "roca": 99}})
    assert sum(p["acoes"].values()) <= ano.orcamento(e)
    assert all(v <= ano.maximo(e, k) for k, v in p["acoes"].items())


def test_plano_lixo_vira_plano_valido():
    e = novo()
    p = ano.normalizar_plano(e, {"acoes": {"escola": "abc", "roca": None, "xyz": 5}, "foco": "latim"})
    assert p["foco"] in AREAS and set(p["acoes"]) == set(ACOES["fundamental"])


def test_bico_so_a_partir_dos_14_anos():
    e = novo()
    assert ano.maximo(e, "bico") == 0 and ano.acao_bloqueada(e, "bico")
    e["idade"] = 14
    assert ano.maximo(e, "bico") > 0 and not ano.acao_bloqueada(e, "bico")


def test_saude_baixa_reduz_o_tempo():
    e = novo()
    base = ano.orcamento(e)
    e["saude"] = 20
    assert ano.orcamento(e) == base - 2


def test_previsao_avisa_de_faltas_e_excesso():
    e = novo()
    r = engine.previsao(e, {"acoes": {"escola": 1, "estudo": 6, "roca": 5}})
    chaves = {a["k"] for a in r["avisos"]}
    assert "aviso.faltas" in chaves and "aviso.excesso" in chaves and not r["valido"]


# ------------------------------------------------------------------ escola

def test_menos_de_3_pontos_de_escola_reprova_por_faltas_e_corta_o_bolsa_familia():
    e = novo()
    p = ano.plano_padrao(e)
    p["acoes"]["escola"] = FREQ_MIN - 1
    e2 = engine.jogar_ano(e, p)
    rel = e2["fila"][0]
    assert rel["aprovado"] is False and rel["motivo"] == "faltas"
    assert e2["serie"] == 1 and e2["reprovacoes"] == 1
    assert rel["renda"] == 0


def test_ir_a_escola_aprova_e_avanca_a_serie():
    e = engine.jogar_ano(novo(), None)
    assert e["fila"][0]["aprovado"] and e["serie"] == 2 and e["idade"] == 7


def test_fome_derruba_a_saude():
    e = novo()
    e["comida"] = 10
    s0 = e["saude"]
    e2 = engine.jogar_ano(e, {"acoes": {"escola": 4, "descanso": 2, "estudo": 2, "comunidade": 2}})
    assert e2["saude"] < s0


def test_saber_nunca_passa_de_100_nem_fica_negativo():
    e = novo()
    for _ in range(40):
        e = limpar_fila(e)
        if e["fim"]:
            break
        e = engine.jogar_ano(e, ano.plano_padrao(e))
        assert all(0 <= v <= 100 for v in e["saber"].values())
        assert all(0 <= e[k] <= 100 for k in ("saude", "animo", "comida", "luta", "terra_ameaca"))


def test_terminar_o_fundamental_leva_ao_medio():
    e = jogar_ate(novo(), lambda e: e["etapa"] == "medio")
    assert e["serie"] == 1 and e["idade"] >= 15


# ------------------------------------------------------------------ treineiro e Enem

def estado_no_medio(serie=1, saber=70.0):
    e = novo()
    e["etapa"], e["serie"], e["idade"] = "medio", serie, 14 + serie
    e["saber"] = {a: saber for a in AREAS}
    e["dinheiro"] = 1000
    return e


def test_depois_do_1o_e_2o_ano_do_medio_oferece_treineiro():
    e = engine.jogar_ano(estado_no_medio(1), None)
    assert [h["tipo"] for h in e["fila"] if h["tipo"] == "treineiro"] == ["treineiro"]


def test_treineiro_paga_taxa_ganha_pratica_e_a_nota_nao_vale():
    e = limpar_item = engine.jogar_ano(estado_no_medio(1), None)
    while e["fila"][0]["tipo"] != "treineiro":
        e = engine.responder(e, {"opcao": e["fila"][0]["opcoes"][0]["id"]} if e["fila"][0]["tipo"] == "evento" else {})
    d0, x0 = e["dinheiro"], e["exp_prova"]
    e = engine.responder(e, {"inscrever": True})
    assert e["fila"][0]["tipo"] == "treino_res"
    assert e["dinheiro"] == d0 - enem.TAXA_TREINEIRO and e["exp_prova"] > x0
    assert e["via"] == "" and e["etapa"] == "medio"


def test_treineiro_sem_dinheiro_nao_se_inscreve():
    e = estado_no_medio(1)
    e["dinheiro"] = 0
    e = engine.jogar_ano(e, {"acoes": {"escola": 4, "estudo": 3, "descanso": 3}})
    while e["fila"][0]["tipo"] != "treineiro":
        e = engine.responder(e, {"opcao": e["fila"][0]["opcoes"][0]["id"]} if e["fila"][0]["tipo"] == "evento" else {})
    e["dinheiro"] = enem.TAXA_TREINEIRO - 1  # o ano deu renda; aqui falta so a taxa
    e = engine.responder(e, {"inscrever": True})
    assert e["dinheiro"] == enem.TAXA_TREINEIRO - 1 and e["treineiro_feito"] == 0


def test_enem_do_3o_ano_gera_prova_e_escolha_de_vias():
    e = engine.jogar_ano(estado_no_medio(3), None)
    tipos = [h["tipo"] for h in e["fila"]]
    assert "enem" in tipos and tipos.index("enem") < tipos.index("vias")


def test_reprovado_no_3o_ano_nao_faz_enem():
    e = estado_no_medio(3)
    e = engine.jogar_ano(e, {"acoes": {"escola": 0, "descanso": 4}})
    assert "enem" not in [h["tipo"] for h in e["fila"]]


def test_prova_e_deterministica_e_tem_limites():
    e = estado_no_medio(3)
    p1, p2 = enem.prova(e, "enem"), enem.prova(e, "enem")
    assert p1 == p2
    assert all(0 <= v <= 1000 for v in p1["areas"].values()) and 0 <= p1["redacao"] <= 1000
    assert all(c % 40 == 0 and 0 <= c <= 200 for c in p1["comps"])


def test_mais_saber_gera_nota_maior():
    baixo, alto = estado_no_medio(3, 30), estado_no_medio(3, 80)
    assert enem.prova(alto, "enem")["media"] > enem.prova(baixo, "enem")["media"] + 150


def test_prouni_e_fies_exigem_media_minima_e_redacao():
    fraca = {"media": 440.0, "redacao": 600}
    assert enem.elegivel("prouni", fraca, 0) == (False, "minimo")
    assert enem.elegivel("fies", {"media": 600.0, "redacao": 0}, 0) == (False, "minimo")
    assert enem.elegivel("fies", {"media": 500.0, "redacao": 400}, 0) == (True, "")
    assert enem.elegivel("ampla", {"media": 500.0, "redacao": 0}, 400) == (True, "")


def test_cota_tem_corte_menor_que_a_ampla():
    e = estado_no_medio(3)
    for t in range(30):
        e["t"] = t
        c = enem.sorteia_cortes(e)
        assert c["cota"] < c["ampla"] and c["prouni"] < c["cota"]


def test_entrar_pela_melhor_via_marcada():
    e = estado_no_medio(3, 90)
    e = engine.jogar_ano(e, {"acoes": {"escola": 4, "estudo": 3, "descanso": 3}})
    e = limpar_fila(e, vias=("prouni", "fies"))
    assert e["etapa"] == "faculdade" and e["via"] == "prouni"


def test_sem_nenhuma_via_vai_pro_cursinho():
    e = engine.jogar_ano(estado_no_medio(3, 90), None)
    e = limpar_fila(e, vias=())
    assert e["etapa"] == "cursinho" and e["via"] == "" and e["enem_tentativas"] == 1


def test_fies_gera_divida_e_prouni_nao():
    def faculdade(via):
        e = novo()
        e["etapa"], e["serie"], e["idade"], e["via"] = "faculdade", 1, 18, via
        return engine.jogar_ano(e, ano.plano_padrao(e))
    assert faculdade("fies")["divida"] > 0 and faculdade("prouni")["divida"] == 0


def test_pe_de_meia_e_resgatado_no_enem():
    e = jogar_ate(novo(), lambda e: e["etapa"] == "medio")
    e = jogar_ate(e, lambda e: any(h["tipo"] == "enem" for h in e["fila"]))
    enem_item = next(h for h in e["fila"] if h["tipo"] == "enem")
    assert enem_item["resgate"] >= 1000 and e["poupanca_pdm"] == 0


# ------------------------------------------------------------------ faculdade, OAB e caso

def estado_formado(juridico=70, pratica=45, rede=50, luta=50, regiao="pontal"):
    e = novo(regiao=regiao)
    e.update(etapa="oab", serie=1, idade=23, juridico=juridico, pratica=pratica, rede=rede, luta=luta,
             via="cota", dinheiro=3000)
    return e


def test_estagio_so_a_partir_do_2o_ano():
    e = novo()
    e.update(etapa="faculdade", serie=1, idade=18, via="cota")
    assert ano.maximo(e, "estagio") == 0
    e["serie"] = 2
    assert ano.maximo(e, "estagio") > 0


def test_reprovar_na_faculdade_mantem_o_ano():
    e = novo()
    e.update(etapa="faculdade", serie=2, idade=19, via="cota", juridico=5)
    e = engine.jogar_ano(e, {"acoes": {"aulas": 1, "descanso": 4}})
    assert e["serie"] == 2 and e["fila"][0]["aprovado"] is False


def test_oab_aprova_quem_estudou_e_tem_pratica():
    ok = 0
    for seed in range(1, 21):
        e = estado_formado()
        e["seed"] = seed
        e = engine.jogar_ano(e, {"acoes": {"estudo": 6, "estagio": 2, "descanso": 2}})
        ok += e["etapa"] == "advocacia"
    assert ok >= 14


def test_oab_reprova_quem_nao_estudou():
    e = estado_formado(juridico=10, pratica=0)
    e = engine.jogar_ano(e, {"acoes": {"descanso": 4}})
    assert e["etapa"] == "oab"


def test_fase1_aprovada_nao_precisa_ser_refeita():
    e = estado_formado(juridico=90, pratica=0)
    e["oab_fase1"] = True
    e = engine.jogar_ano(e, {"acoes": {"estudo": 2, "descanso": 2}})
    oab = next(h for h in e["fila"] if h["tipo"] == "oab")
    assert oab["fase1"] is None and oab["fase1_antes"] is True


def test_caso_comeca_apos_a_oab_e_vitoria_encerra_o_jogo():
    e = estado_formado(juridico=95, pratica=90, rede=90, luta=90, regiao="campanha")
    e = jogar_ate(e, lambda e: e["etapa"] == "advocacia", lambda e: {"acoes": {"estudo": 6, "estagio": 2, "descanso": 2}})
    assert e["caso"]["defesa"] > 0
    for _ in range(6):
        e = limpar_fila(e)
        if e["fim"]:
            break
        e = engine.jogar_ano(e, {"casos": ["peticao", "laudo"]})
    assert e["fim"]["tipo"] == "vitoria"


def test_caso_perdido_nas_tres_instancias_e_derrota():
    e = estado_formado(juridico=5, pratica=0, rede=0, luta=0, regiao="sul_para")
    e["etapa"] = "advocacia"
    caso.iniciar(e)
    for _ in range(6):
        e = limpar_fila(e)
        if e["fim"]:
            break
        e = engine.jogar_ano(e, {"casos": []})
    assert e["fim"]["tipo"] == "derrota"


def test_acao_repetida_rende_menos():
    e = estado_formado()
    e["etapa"] = "advocacia"
    caso.iniciar(e)
    primeira = caso.valor_acao(e, "peticao", 0)["defesa"]
    segunda = caso.valor_acao(e, "peticao", 1)["defesa"]
    assert segunda < primeira


def test_caso_so_aceita_2_acoes_e_laudo_exige_dinheiro():
    e = estado_formado()
    e["etapa"] = "advocacia"
    caso.iniciar(e)
    e["dinheiro"] = -3000  # o salario do ano (2500) nao cobre o deslocamento do laudo
    e2 = engine.jogar_ano(e, {"casos": ["laudo", "peticao", "mobilizar", "mp"]})
    rel = e2["fila"][0]
    assert "laudo" not in rel["usadas"] and len(rel["usadas"]) <= 2


# ------------------------------------------------------------------ eventos e fila

def test_todo_evento_tem_ao_menos_uma_etapa_valida_e_opcoes_com_efeitos_conhecidos():
    from lonatoga.sim.content import CHAVES_EFEITO, ETAPAS
    for ev in TODOS_EVENTOS.values():
        assert set(ev.etapas) <= set(ETAPAS) and ev.opcoes
        for o in ev.opcoes:
            assert set(o.efeitos) <= set(CHAVES_EFEITO), (ev.id, o.id)


def test_evento_com_custo_alto_cai_na_opcao_gratuita():
    e = novo()
    e["fila"] = [engine._item_evento("ubs")]
    e["dinheiro"] = 0
    e = engine.responder(e, {"opcao": "posto"})
    assert e["fila"][0]["opcao"] == "cha"


def test_responder_sem_fila_e_erro_e_jogar_com_fila_tambem():
    e = novo()
    with pytest.raises(ValueError):
        engine.responder(e, {})
    e = engine.jogar_ano(e, None)
    with pytest.raises(ValueError):
        engine.jogar_ano(e, None)


def test_despejo_dispara_quando_a_pressao_chega_ao_maximo():
    e = novo()
    e["terra_ameaca"] = 100
    e = engine.jogar_ano(e, None)
    assert any(h["tipo"] == "evento" and h["id"] == "despejo" for h in e["fila"])
    e = limpar_fila(e)
    assert e["despejos"] == 1 and e["terra_ameaca"] < 70


def test_limite_de_idade_encerra_o_jogo_sem_a_terra():
    e = novo()
    e["idade"] = 37
    e = engine.jogar_ano(e, None)
    assert e["fim"]["tipo"] == "tempo"


def test_painel_traz_acoes_com_soma_igual_ao_orcamento():
    p = engine.painel(novo())
    assert sum(a["padrao"] for a in p["acoes"]) == p["orcamento"] and p["pode_jogar"]
    assert [x["estado"] for x in p["trilha"]].count("atual") == 1


def test_trilha_marca_tudo_como_feito_na_vitoria():
    e = novo()
    e["etapa"] = "advocacia"
    caso.iniciar(e)
    e["fim"] = {"tipo": "vitoria"}
    assert all(x["estado"] == "feito" for x in engine.painel(e)["trilha"])
