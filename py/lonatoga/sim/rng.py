"""Aleatoriedade deterministica. Nunca usar random. no nivel de modulo.

IMPORTANTE: nao usar hash() aqui. O hash de str no Python e randomizado a
cada processo (PYTHONHASHSEED), entao a mesma semente daria jogos diferentes
a cada execucao e o replay por seed quebraria.
"""

import hashlib
from functools import lru_cache
from random import Random


@lru_cache(maxsize=64)
def _canal_id(canal: str) -> int:
    """Numero estavel pro nome do canal, igual em qualquer processo."""
    digest = hashlib.blake2b(canal.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def stream(seed: int, t: int, canal: str) -> Random:
    """Random independente por (seed, ano do jogo, canal).

    Canais separados evitam que um sorteio novo mude os outros: adicionar um
    evento nao muda o resultado do Enem de um jogo ja conhecido.
    """
    misturado = int(seed) * 1_000_003 + int(t) * 9_176 + _canal_id(canal)
    return Random(misturado & 0x7FFF_FFFF_FFFF)
