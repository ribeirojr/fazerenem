"""Dados do jogo: regioes, vias de ingresso, acoes do ano, eventos e o caso.

So dados e constantes. Nenhuma regra de jogo aqui, e nenhum texto: tudo que o
jogador le sai de chaves de i18n (ver chaves_exigidas() no fim do arquivo).
"""

from dataclasses import dataclass, field

# ------------------------------------------------------------------ saberes

# As 4 areas objetivas do Enem + a redacao. O jogador acumula "saber" (0-100)
# em cada uma; a nota do Enem (300-1000 por area) sai desse saber no dia da prova.
AREAS = ("linguagens", "humanas", "natureza", "matematica", "redacao")
AREAS_OBJETIVAS = AREAS[:4]

# ------------------------------------------------------------------ etapas

ETAPAS = ("fundamental", "medio", "cursinho", "faculdade", "oab", "advocacia")
ETAPAS_ESCOLA = ("fundamental", "medio", "cursinho")
SERIES = {"fundamental": 9, "medio": 3, "faculdade": 5}

# Trilha mostrada no topo: cada passo e uma etapa ou um marco.
TRILHA = ("lona", "fundamental", "medio", "enem", "faculdade", "oab", "terra")

ORCAMENTO_BASE = 10          # "tempo" do ano, em pontos
IDADE_INICIAL = 6
ANO_INICIAL = 2015           # o Enem do jogador cai em 2026
IDADE_LIMITE = 38            # passou disso sem chegar a advocacia: fim sem a terra
IDADE_MIN_BICO = 14          # Jovem Aprendiz: a partir dos 14 anos
FREQ_MIN = 3                 # de 4 pontos de escola: os 75% de frequencia

# ------------------------------------------------------------------ acoes do ano

ACOES = {
    "fundamental": ("escola", "estudo", "roca", "bico", "comunidade", "descanso"),
    "medio": ("escola", "estudo", "roca", "bico", "comunidade", "descanso"),
    "cursinho": ("cursinho", "estudo", "roca", "bico", "comunidade", "descanso"),
    "faculdade": ("aulas", "estudo", "estagio", "extensao", "bico", "descanso"),
    "oab": ("estudo", "estagio", "bico", "descanso"),
}

MAXIMO = {
    "escola": 6, "cursinho": 6, "aulas": 6, "estudo": 6, "roca": 5, "bico": 4,
    "comunidade": 3, "descanso": 4, "estagio": 4, "extensao": 3,
}

PADRAO = {
    "fundamental": {"escola": 4, "estudo": 2, "roca": 3, "bico": 0, "comunidade": 0, "descanso": 1},
    "medio": {"escola": 4, "estudo": 3, "roca": 1, "bico": 1, "comunidade": 0, "descanso": 1},
    "cursinho": {"cursinho": 4, "estudo": 3, "roca": 1, "bico": 1, "comunidade": 0, "descanso": 1},
    "faculdade": {"aulas": 4, "estudo": 2, "estagio": 1, "extensao": 1, "bico": 0, "descanso": 2},
    "oab": {"estudo": 6, "estagio": 1, "bico": 1, "descanso": 2},
}

# ------------------------------------------------------------------ regioes


@dataclass(frozen=True, slots=True)
class Regiao:
    key: str
    escola_q: float       # qualidade da escola mais proxima (multiplica o ganho)
    roca: float           # produtividade da terra do acampamento
    dono: int             # forca do dono da terra no tribunal
    improdutiva: int      # anos de terra improdutiva (argumento da funcao social)
    custo_escola: int     # transporte e material por ano
    univ_longe: bool      # a federal fica em outra cidade?


REGIOES: dict[str, Regiao] = {r.key: r for r in (
    Regiao("pontal", 1.05, 1.00, 72, 14, 250, False),
    Regiao("sul_para", 0.88, 1.10, 84, 11, 420, True),
    Regiao("campanha", 1.10, 0.90, 66, 18, 300, False),
    Regiao("zona_mata", 0.95, 0.95, 78, 9, 300, True),
)}
ORDEM_REGIOES = tuple(REGIOES)

# ------------------------------------------------------------------ vias de ingresso

# Ordem de prioridade na hora de ser chamado: ampla > cota > prouni > fies.
VIAS = ("ampla", "cota", "prouni", "fies")
CORTE_BASE = {"ampla": 850, "cota": 760, "prouni": 690, "fies": 0}
CORTE_VARIACAO = 14          # o corte muda um pouco todo ano
MEDIA_MINIMA = 450           # ProUni e Fies pedem media >= 450 e redacao != 0


@dataclass(frozen=True, slots=True)
class Via:
    key: str
    publica: bool
    qualidade: float         # multiplica o ganho de aprendizado no curso
    tempo_extra: int         # curso noturno libera tempo pra trabalhar
    auxilio: int             # bolsa permanencia / ano
    custo_extra: int         # transporte, material
    divida_ano: int          # Fies


DADOS_VIAS: dict[str, Via] = {v.key: v for v in (
    Via("ampla", True, 1.00, 0, 2400, 0, 0),
    Via("cota", True, 1.00, 0, 2400, 0, 0),
    Via("prouni", False, 0.88, 1, 0, 1200, 0),
    Via("fies", False, 0.88, 1, 0, 1200, 14000),
)}

# ------------------------------------------------------------------ o caso da terra

ETAPAS_CASO = ("liminar", "pericia", "sentenca", "apelacao1", "apelacao2")
ACOES_CASO = ("peticao", "laudo", "mobilizar", "acordo", "mp")
MAX_ACOES_CASO = 2
CUSTO_CASO = {"laudo": 400}

# ------------------------------------------------------------------ eventos


@dataclass(frozen=True, slots=True)
class Opcao:
    id: str
    efeitos: dict = field(default_factory=dict)
    custo: int = 0


@dataclass(frozen=True, slots=True)
class Evento:
    id: str
    etapas: tuple
    peso: int
    opcoes: tuple
    cond: str = ""
    # eventos "ok" tem uma unica opcao: o texto ja conta tudo, so mostra os efeitos


def _ok(**efeitos) -> tuple:
    return (Opcao("ok", efeitos),)


ESCOLA = ETAPAS_ESCOLA
EVENTOS: dict[str, Evento] = {ev.id: ev for ev in (
    # ---- qualquer etapa de escola
    Evento("colheita_boa", ESCOLA, 3, _ok(comida=12, animo=3)),
    Evento("seca", ESCOLA, 3, _ok(comida=-12, animo=-3)),
    Evento("doacao", ESCOLA, 2, _ok(dinheiro=400, animo=3)),
    Evento("ubs", ESCOLA, 3, (
        Opcao("posto", {"saude": -2}, custo=60),
        Opcao("cha", {"saude": -9, "animo": -2}),
    )),
    # ---- 1o grau
    Evento("chuva_estrada", ("fundamental",), 4, (
        Opcao("andar", {"saude": -4, "animo": 2, "saber": 1.5}),
        Opcao("casa", {"animo": -2, "saber": 0.5}),
    )),
    Evento("lamparina", ("fundamental",), 3, (
        Opcao("ler", {"saber_linguagens": 4, "saber_redacao": 1.5, "saude": -2}),
        Opcao("dividir", {"luta": 4, "animo": 4}),
    )),
    Evento("colheita_tio", ("fundamental",), 3, (
        Opcao("ajudar", {"dinheiro": 350, "saude": -3, "saber": -2}),
        Opcao("escola", {"animo": 2, "comida": -4}),
    )),
    Evento("ciranda", ("fundamental",), 3, _ok(luta=6, animo=6)),
    Evento("merenda", ("fundamental", "medio"), 2, _ok(comida=8)),
    # ---- 2o grau
    Evento("olimpiada", ("medio",), 3, (
        Opcao("participar", {"saber_matematica": 5, "exp_prova": 4, "saude": -3}),
        Opcao("recusar", {"animo": 2}),
    )),
    Evento("redacao_prof", ("medio", "cursinho"), 3, (
        Opcao("reescrever", {"saber_redacao": 6, "saude": -2}),
        Opcao("entregar", {"saber_redacao": 1, "animo": 1}),
    )),
    Evento("wifi", ("medio", "cursinho"), 3, (
        Opcao("praca", {"saber": 2.5, "saude": -2}),
        Opcao("apostila", {"saber": 1, "animo": 1}),
    )),
    Evento("cursinho_popular", ("medio",), 2, (
        Opcao("entrar", {"exp_prova": 6, "saber": 2, "saude": -3}),
        Opcao("nao", {"animo": 2}),
    )),
    # ---- cursinho (segunda tentativa em diante)
    Evento("desanimo", ("cursinho",), 4, (
        Opcao("grupo", {"animo": 8, "luta": 2}),
        Opcao("sozinho", {"animo": -4, "saber": 2}),
    )),
    # ---- faculdade
    Evento("estagio_fazendeiro", ("faculdade",), 4, (
        Opcao("aceitar", {"dinheiro": 2500, "luta": -10, "rede": 5, "pratica": 6}),
        Opcao("recusar", {"animo": 3, "luta": 4}),
    ), cond="serie2"),
    Evento("saju", ("faculdade",), 4, (
        Opcao("entrar", {"luta": 7, "pratica": 5, "rede": 5, "saude": -2}),
        Opcao("agora_nao", {"saude": 3}),
    )),
    Evento("processo_civil", ("faculdade",), 3, (
        Opcao("grupo", {"juridico": 5, "rede": 2}),
        Opcao("sozinho", {"juridico": 3, "saude": -3}),
    )),
    Evento("moradia", ("faculdade",), 3, _ok(dinheiro=1500, animo=4), cond="publica_longe"),
    Evento("visita_acampamento", ("faculdade", "oab"), 3, (
        Opcao("voltar", {"animo": 5, "luta": 5, "terra_ameaca": -8, "pratica": 2}, custo=200),
        Opcao("ligar", {"animo": -2}),
    )),
    Evento("piada_turma", ("faculdade",), 2, (
        Opcao("responder", {"luta": 5, "rede": 2, "animo": -3}),
        Opcao("ignorar", {"animo": -5, "saude": -2}),
    )),
    # ---- oab
    Evento("curso_gratis", ("oab",), 3, (
        Opcao("fazer", {"juridico": 4, "pratica": 3, "saude": -2}),
        Opcao("nao", {"animo": 2}),
    )),
    Evento("escritorio_popular", ("oab",), 3, (
        Opcao("trabalhar", {"dinheiro": 1500, "pratica": 5, "saude": -3}),
        Opcao("estudar", {"juridico": 3}),
    )),
)}

# Eventos que o jogo dispara por conta propria (nao entram no sorteio).
EVENTOS_FIXOS: dict[str, Evento] = {ev.id: ev for ev in (
    Evento("despejo", ESCOLA + ("faculdade", "oab"), 0, (
        Opcao("resistir", {"luta": 6, "animo": -3, "saude": -4, "terra_ameaca": -55, "despejos": 1}),
        Opcao("recompor", {"comida": -15, "animo": -6, "terra_ameaca": -60, "despejos": 1}),
    )),
    Evento("aperto", ("faculdade", "oab"), 0, (
        Opcao("trancar", {"dinheiro": 3500, "animo": -5, "pratica": 2}),
        Opcao("apoio", {"dinheiro": 2000, "luta": 2, "animo": -2}),
    )),
)}

TODOS_EVENTOS = {**EVENTOS, **EVENTOS_FIXOS}

CHAVES_EFEITO = (
    "saude", "animo", "comida", "luta", "dinheiro", "terra_ameaca", "exp_prova",
    "juridico", "pratica", "rede", "saber", "despejos",
) + tuple(f"saber_{a}" for a in AREAS)

# Estatisticas que o jogador ve no painel (e nos "chips" de efeito).
ESTATISTICAS = (
    "saude", "animo", "comida", "luta", "dinheiro", "terra_ameaca", "exp_prova",
    "juridico", "pratica", "rede", "saber", "despejos", "divida",
)


# ------------------------------------------------------------------ chaves de texto exigidas

def chaves_exigidas() -> set[str]:
    """Todas as chaves de i18n que o CONTEUDO acima referencia.

    A UI monta chaves a partir de dados (ex: `etapa.<etapa>`); o teste de i18n
    confere que cada uma existe em pt e en, entao esquecer uma vira falha de teste
    e nao um 'ev.xyz.titulo' na tela do jogador.
    """
    ks: set[str] = set()
    ks |= {f"etapa.{e}" for e in ETAPAS}
    ks |= {f"trilha.{p}" for p in TRILHA}
    ks |= {f"area.{a}" for a in AREAS}
    ks |= {f"stat.{s}" for s in ESTATISTICAS}
    for etapa, acoes in ACOES.items():
        for a in acoes:
            ks |= {f"acao.{a}", f"acao.{a}.desc"}
    for r in REGIOES:
        ks |= {f"reg.{r}.nome", f"reg.{r}.desc"}
    for v in VIAS:
        ks |= {f"via.{v}", f"via.{v}.desc"}
    for a in ACOES_CASO:
        ks |= {f"caso.acao.{a}", f"caso.acao.{a}.desc"}
    for e in ETAPAS_CASO:
        ks |= {f"caso.etapa.{e}", f"caso.etapa.{e}.ganhou", f"caso.etapa.{e}.perdeu"}
    for ev in TODOS_EVENTOS.values():
        ks |= {f"ev.{ev.id}.titulo", f"ev.{ev.id}.texto"}
        if len(ev.opcoes) > 1:
            for op in ev.opcoes:
                ks |= {f"ev.{ev.id}.{op.id}", f"ev.{ev.id}.{op.id}.res"}
    return ks
