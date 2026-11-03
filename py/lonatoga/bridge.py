"""Ponte entre a simulacao e o navegador (Pyodide).

Regra: so entra e sai JSON puro (dict/list/str/int/float/bool). O estado do
jogo ja e um dict assim, entao nao ha serializacao a manter em dois lugares:
o que o navegador guarda no localStorage e exatamente o que a simulacao usa.

Erros viram {"erro": "<chave>"} em vez de excecao, pra UI decidir o que mostrar.
"""

from typing import Any

from .i18n import textos as _textos
from .sim import engine
from .sim.content import ORDEM_REGIOES, REGIOES


def textos(lang: str) -> dict:
    """Todos os textos do idioma ('pt' ou 'en'), pra UI traduzir com t()."""
    return _textos(lang)


def regioes() -> list[dict]:
    return [
        {"key": k, "escola_q": r.escola_q, "roca": r.roca, "dono": r.dono,
         "custo_escola": r.custo_escola, "univ_longe": r.univ_longe, "improdutiva": r.improdutiva}
        for k, r in ((k, REGIOES[k]) for k in ORDEM_REGIOES)
    ]


def _seguro(fn, *args) -> Any:
    try:
        return fn(*args)
    except ValueError as ex:
        return {"erro": str(ex)}


def novo_jogo(seed: int, regiao: str, nome: str, genero: str) -> dict:
    return engine.novo_jogo(int(seed), regiao, nome, genero)


def restaurar(estado: dict) -> dict:
    """Carrega um save (possivelmente antigo) e completa os campos que faltam."""
    return engine.migrar(estado)


def painel(estado: dict) -> dict:
    return engine.painel(estado)


def previsao(estado: dict, plano: dict) -> dict:
    return engine.previsao(estado, plano)


def jogar_ano(estado: dict, plano: dict) -> dict:
    return _seguro(engine.jogar_ano, estado, plano)


def responder(estado: dict, resposta: dict) -> dict:
    return _seguro(engine.responder, estado, resposta)
