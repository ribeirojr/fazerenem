"""Bots que jogam o jogo inteiro, pra conferir o equilibrio.

    python3 tools/balance.py [n_sementes]

Um jogador competente tem que ganhar na maioria das sementes, um jogador
largado (so descansa) nao pode ganhar. Os testes (tests/test_balance.py) usam
os mesmos bots como trava.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "py"))

from lonatoga.sim import engine  # noqa: E402
from lonatoga.sim.ano import plano_padrao  # noqa: E402
from lonatoga.sim.content import ORDEM_REGIOES, TODOS_EVENTOS, VIAS  # noqa: E402

LIMITE_PASSOS = 400


def plano_competente(e: dict) -> dict:
    """O padrao da etapa, trocando alguns pontos conforme a situacao."""
    p = plano_padrao(e)
    a = p["acoes"]
    if e["etapa"] in ("fundamental", "medio", "cursinho"):
        if e["comida"] < 40 and "roca" in a and a["descanso"] > 0:
            a["roca"] += 1
            a["descanso"] -= 1
        if e["saude"] < 40 and a.get("bico", 0) > 0:
            a["bico"] -= 1
            a["descanso"] += 1
    return p


def plano_largado(e: dict) -> dict:
    a = {k: 0 for k in plano_padrao(e)["acoes"]}
    a["descanso"] = 4
    a["bico"] = 0
    return {"acoes": a, "foco": "matematica"}


def plano_mediano(e: dict) -> dict:
    """Quem estuda, mas divide o tempo com trabalho e nao reforca a area fraca."""
    p = plano_padrao(e)
    a = p["acoes"]
    for k in a:
        a[k] = 0
    if e["etapa"] in ("fundamental", "medio"):
        a.update({"escola": 3, "estudo": 1, "roca": 2, "bico": 2 if e["idade"] >= 14 else 0, "descanso": 2})
        a["roca"] += 10 - sum(a.values())
    elif e["etapa"] == "cursinho":
        a.update({"cursinho": 3, "estudo": 1, "roca": 2, "bico": 2, "descanso": 2})
    elif e["etapa"] == "faculdade":
        a.update({"aulas": 3, "estudo": 1, "bico": 3, "descanso": 3})
    else:
        a.update({"estudo": 3, "bico": 3, "descanso": 4})
    return {"acoes": a, "foco": p["foco"]}


def melhores_acoes_caso(e: dict) -> list[str]:
    from lonatoga.sim import caso
    prev = caso.previsao(e)
    pontos = {k: v["defesa"] - v["acusacao"] for k, v in prev.items() if v["custo"] <= e["dinheiro"]}
    return sorted(pontos, key=pontos.get, reverse=True)[:2]


def responder_tudo(e: dict, vias: tuple, escolher_opcao) -> dict:
    while e["fila"]:
        h = e["fila"][0]
        t = h["tipo"]
        if t == "evento":
            e = engine.responder(e, {"opcao": escolher_opcao(e, h)})
        elif t == "treineiro":
            e = engine.responder(e, {"inscrever": e["dinheiro"] >= h["taxa"] + 300})
        elif t == "vias":
            e = engine.responder(e, {"vias": list(vias)})
        else:
            e = engine.responder(e, {})
    return e


def melhor_opcao(e: dict, h: dict) -> str:
    """Escolhe a opcao com maior soma de efeitos 'bons' que o jogador consegue pagar."""
    def valor(o):
        ef = o["efeitos"]
        return sum(v for k, v in ef.items() if k not in ("despejos", "terra_ameaca")) \
            - (o["custo"] / 200) + (-ef.get("terra_ameaca", 0) / 8)
    cabe = [o for o in h["opcoes"] if o["custo"] <= max(e["dinheiro"], 0)] or h["opcoes"]
    return max(cabe, key=valor)["id"]


def jogar(seed: int, regiao: str, plano_fn=plano_competente, vias: tuple = VIAS, inteligente=True) -> dict:
    e = engine.novo_jogo(seed, regiao, "Teste", "f")
    for _ in range(LIMITE_PASSOS):
        if e["fim"] and not e["fila"]:
            break
        if e["fila"]:
            e = responder_tudo(e, vias, melhor_opcao if inteligente else (lambda e, h: h["opcoes"][0]["id"]))
            continue
        if e["etapa"] == "advocacia":
            e = engine.jogar_ano(e, {"casos": melhores_acoes_caso(e)})
        else:
            e = engine.jogar_ano(e, plano_fn(e))
    return e


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    for nome, fn in (("competente", plano_competente), ("mediano", plano_mediano), ("largado", plano_largado)):
        fins, vias_usadas, idades, reprov = Counter(), Counter(), [], []
        for regiao in ORDEM_REGIOES:
            for seed in range(1, n + 1):
                e = jogar(seed, regiao, fn)
                fins[e["fim"].get("tipo", "?")] += 1
                vias_usadas[e["via"] or "-"] += 1
                idades.append(e["fim"].get("idade", 0))
                reprov.append(e["reprovacoes"])
        tot = sum(fins.values())
        print(f"\n== {nome} ({tot} jogos)")
        print("  fins:", dict(fins))
        print("  vias:", dict(vias_usadas))
        print(f"  idade media ao fim: {sum(idades)/len(idades):.1f}; reprovacoes medias: {sum(reprov)/len(reprov):.2f}")


if __name__ == "__main__":
    main()
