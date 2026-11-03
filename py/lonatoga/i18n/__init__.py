"""Textos do jogo em dois idiomas.

O modo Noite fala ingles e o Modo Bandeira fala portugues do Brasil (ver
README). A simulacao devolve CHAVES; quem monta a frase e a UI, com t().

Chaves com sufixo `_1` sao o singular: t("x", n=1) usa "x_1" se existir.
Nomes de lugares, de comidas e de instituicoes (Enem, ProUni, Sisu, OAB...)
ficam em portugues nos dois idiomas, de proposito.
"""

import re

from .en import EN
from .pt import PT

IDIOMAS = {"pt": PT, "en": EN}

# Variaveis de genero ({adv}, {o}...) vem de g.<m|f>.<nome>, nao do codigo que chama t().
GENERO = re.compile(r"^g\.[mf]\.")


def textos(lang: str) -> dict:
    return dict(IDIOMAS.get(lang, EN))


def t(lang: str, chave: str, **v) -> str:
    """Versao Python do t() da UI. Usada pelos testes; a UI tem a sua em JS."""
    d = IDIOMAS.get(lang, EN)
    if v.get("n") == 1 and f"{chave}_1" in d:
        chave = f"{chave}_1"
    s = d.get(chave, EN.get(chave, chave))
    return re.sub(r"\{(\w+)\}", lambda m: str(v.get(m.group(1), m.group(0))), s)
