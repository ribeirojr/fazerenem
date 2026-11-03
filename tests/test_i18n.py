"""Os dois idiomas tem as mesmas chaves, e nenhuma chave usada fica sem texto."""

import re
from pathlib import Path

from lonatoga.i18n import GENERO, textos, t
from lonatoga.i18n.en import EN
from lonatoga.i18n.pt import PT
from lonatoga.sim.content import chaves_exigidas

RAIZ = Path(__file__).resolve().parent.parent
GENERO_VARS = {"adv", "aprov", "form", "o"}
PLACEHOLDER = re.compile(r"\{(\w+)\}")
TAG = re.compile(r"</?(\w+)[^>]*>")


def test_mesmas_chaves_nos_dois_idiomas():
    assert set(PT) == set(EN), (sorted(set(PT) ^ set(EN)))


def test_mesmas_variaveis_nos_dois_idiomas():
    """{n} no pt tem que ser {n} no en. As de genero so existem no pt, e ok."""
    ruins = []
    for k in PT:
        a = set(PLACEHOLDER.findall(PT[k])) - GENERO_VARS
        b = set(PLACEHOLDER.findall(EN[k])) - GENERO_VARS
        if a != b:
            ruins.append((k, a, b))
    assert not ruins, ruins


def test_html_so_negrito_e_igual_nos_dois():
    for k in PT:
        tp = sorted(TAG.findall(PT[k]))
        te = sorted(TAG.findall(EN[k]))
        assert tp == te, k
        assert set(tp) <= {"b", "em"}, k


def test_singular_tem_base():
    for d in (PT, EN):
        for k in d:
            if k.endswith("_1"):
                assert k[:-2] in d, k


def test_genero_tem_as_duas_variantes_nos_dois_idiomas():
    for d in (PT, EN):
        for k in [k for k in d if GENERO.match(k)]:
            outro = k.replace("g.m.", "g.f.") if k.startswith("g.m.") else k.replace("g.f.", "g.m.")
            assert outro in d, k


def test_conteudo_so_referencia_chaves_que_existem():
    falta = chaves_exigidas() - set(PT)
    assert not falta, sorted(falta)


def test_cada_texto_tem_conteudo():
    for d in (PT, EN):
        for k, v in d.items():
            assert v.strip(), k


def test_app_js_so_usa_chaves_que_existem():
    """Qualquer literal 'grupo.nome' em app.js e uma chave de texto."""
    src = (RAIZ / "app.js").read_text(encoding="utf-8")
    achadas = set(re.findall(r"""["']([a-z]+(?:\.[a-z0-9_]+)+)["']""", src))
    achadas -= {"es.module"}
    falta = {k for k in achadas if k not in PT}
    assert not falta, sorted(falta)


def test_mensagens_da_simulacao_existem():
    """Chaves que o Python devolve (log, aviso, bloqueio) tem texto."""
    achadas = set()
    for p in (RAIZ / "py" / "lonatoga" / "sim").glob("*.py"):
        achadas |= set(re.findall(r'"((?:log|aviso|bloqueio)\.[a-z0-9_]+)"', p.read_text(encoding="utf-8")))
    falta = {k for k in achadas if k not in PT}
    assert not falta, sorted(falta)


def test_motivos_de_reprovacao_tem_texto():
    for m in ("faltas", "saude", "notas"):
        assert f"rel.reprovou.{m}" in PT and f"rel.motivo.{m}" in PT


def test_t_do_python_troca_variaveis_e_plural():
    assert t("pt", "aviso.excesso", n=3) == "3 pontos acima do tempo que você tem."
    assert t("pt", "aviso.excesso", n=1) == "1 ponto acima do tempo que você tem."
    assert t("en", "chip.idade", n=7) == "7 yrs"
    assert t("en", "chave.que.nao.existe") == "chave.que.nao.existe"


def test_textos_devolve_copia():
    d = textos("pt")
    d["app.tag"] = "x"
    assert PT["app.tag"] != "x"
