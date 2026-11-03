"""Gera saves de momentos interessantes do jogo, pra tirar screenshots e testar a UI.

    python3 tools/make_saves.py <pasta> [seed]

Escreve <pasta>/<nome>.json com o estado exato (o mesmo JSON do localStorage).
Usa os bots de tools/balance.py.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "py"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import balance  # noqa: E402
from lonatoga.sim import engine  # noqa: E402


def avancar_ate(e, pred, regiao_plano=balance.plano_competente, limite=80):
    """Joga com o bot ate `pred(e)` ficar verdadeiro (sem responder a fila no ultimo passo)."""
    for _ in range(limite):
        if pred(e):
            return e
        if e["fila"]:
            h = e["fila"][0]
            if h["tipo"] == "evento":
                e = engine.responder(e, {"opcao": balance.melhor_opcao(e, h)})
            elif h["tipo"] == "treineiro":
                e = engine.responder(e, {"inscrever": e["dinheiro"] >= h["taxa"] + 300})
            elif h["tipo"] == "vias":
                e = engine.responder(e, {"vias": ["ampla", "cota", "prouni"]})
            else:
                e = engine.responder(e, {})
        elif e["etapa"] == "advocacia":
            e = engine.jogar_ano(e, {"casos": balance.melhores_acoes_caso(e)})
        else:
            e = engine.jogar_ano(e, regiao_plano(e))
    raise RuntimeError("nao chegou")


def main() -> None:
    out = Path(sys.argv[1])
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    out.mkdir(parents=True, exist_ok=True)
    e0 = engine.novo_jogo(seed, "pontal", "Rosa", "f")
    marcos = {
        "inicio": lambda e: False,
        "fundamental": lambda e: e["etapa"] == "fundamental" and e["serie"] == 5 and not e["fila"],
        "relatorio": lambda e: e["etapa"] == "fundamental" and e["serie"] == 6 and e["fila"],
        "medio": lambda e: e["etapa"] == "medio" and e["serie"] == 2 and not e["fila"],
        "treineiro": lambda e: any(h["tipo"] == "treineiro" for h in e["fila"][:1]),
        "enem": lambda e: bool(e["fila"]) and e["fila"][0]["tipo"] == "enem",
        "vias": lambda e: bool(e["fila"]) and e["fila"][0]["tipo"] == "vias",
        "faculdade": lambda e: e["etapa"] == "faculdade" and e["serie"] == 3 and not e["fila"],
        "oab": lambda e: e["etapa"] == "oab" and not e["fila"],
        "caso": lambda e: e["etapa"] == "advocacia" and not e["fila"],
    }
    for nome, pred in marcos.items():
        e = e0 if nome == "inicio" else avancar_ate(json.loads(json.dumps(e0)), pred)
        (out / f"{nome}.json").write_text(json.dumps(e), encoding="utf-8")
        print(nome, "->", e["etapa"], e["serie"], "fila:", [h["tipo"] for h in e["fila"]])
    # final de vitoria: um advogado forte vence
    e = json.loads((out / "caso.json").read_text())
    e.update(juridico=95, pratica=80, rede=80, luta=80)
    e["caso"].update(defesa=130, acusacao=5)
    e = avancar_ate(e, lambda e: bool(e["fim"]) and not e["fila"])
    (out / "fim.json").write_text(json.dumps(e), encoding="utf-8")
    print("fim ->", e["fim"]["tipo"])


if __name__ == "__main__":
    main()
