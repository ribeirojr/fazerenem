"""Funcoes pequenas usadas pela simulacao inteira."""

from typing import Any

State = dict[str, Any]


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def arred(x: float, n: int = 1) -> float:
    return round(float(x), n)


def log(e: State, k: str, **v: Any) -> None:
    """Registra no diario. Guarda a CHAVE e as variaveis, nunca o texto:
    assim trocar de idioma traduz o historico inteiro."""
    e["log"].insert(0, {"k": k, "v": v, "ano": e["ano"], "idade": e["idade"]})
    del e["log"][80:]
