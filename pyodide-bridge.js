/**
 * Ponte JS -> Pyodide -> lonatoga.bridge
 *
 * Carrega o CPython (WebAssembly) no navegador, monta o pacote `lonatoga` no
 * filesystem virtual e expoe a simulacao como metodos JS comuns. Todas as
 * regras do jogo rodam em Python; app.js so desenha o que a ponte devolve.
 *
 * Os testes em Node injetam `loadPyodide` e `lerModulo` (ver scripts/), por isso
 * nada aqui depende de `window`.
 */

export const PYODIDE_VERSION = "0.28.0";
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

// Todo arquivo .py do pacote tem que estar aqui. tests/test_web_bundle.py falha
// se esquecer um (sem isso o navegador da 404 em tempo de execucao).
export const MODULOS = [
  "__init__.py",
  "bridge.py",
  "i18n/__init__.py", "i18n/pt.py", "i18n/en.py",
  "sim/__init__.py", "sim/rng.py", "sim/util.py", "sim/content.py",
  "sim/ano.py", "sim/enem.py", "sim/caso.py", "sim/engine.py",
];

const DIRETORIOS = ["/jogo", "/jogo/lonatoga", "/jogo/lonatoga/i18n", "/jogo/lonatoga/sim"];

/** pyodide.toPy() converte `null` num sentinela JsNull, nao em None; `undefined`
 * converte certo. O estado do jogo nao usa null, mas um save de fora poderia. */
function semNull(valor) {
  if (valor === null) return undefined;
  if (Array.isArray(valor)) return valor.map(semNull);
  if (valor && typeof valor === "object") {
    const out = {};
    for (const [k, v] of Object.entries(valor)) out[k] = semNull(v);
    return out;
  }
  return valor;
}

export class Engine {
  /**
   * @param {object} [opts]
   * @param {Function} [opts.loadPyodide] carrega o interpretador (padrao: script do CDN)
   * @param {Function} [opts.lerModulo]   async (caminhoRelativo) => texto do .py
   * @param {string}   [opts.indexURL]    onde ficam os arquivos do Pyodide
   */
  constructor(opts = {}) {
    this.opts = opts;
    this.pyodide = null;
    this.bridge = null;
  }

  /** Carrega tudo. onProgresso(chave, pct) recebe 'baixando' | 'montando' | 'pronto'. */
  async iniciar(onProgresso = () => {}) {
    onProgresso("baixando", 5);
    let carregar = this.opts.loadPyodide || globalThis.loadPyodide;
    if (!carregar) {
      await this._carregarScript(`${PYODIDE_CDN}pyodide.js`);
      carregar = globalThis.loadPyodide;
    }
    this.pyodide = await carregar({ indexURL: this.opts.indexURL || PYODIDE_CDN });

    onProgresso("montando", 75);
    await this._montarCodigo();
    this.bridge = this.pyodide.pyimport("lonatoga.bridge");
    onProgresso("pronto", 100);
  }

  _carregarScript(src) {
    return new Promise((ok, erro) => {
      const s = document.createElement("script");
      s.src = src;
      s.onload = ok;
      s.onerror = () => erro(new Error(`falhou ao carregar ${src}`));
      document.head.appendChild(s);
    });
  }

  async _montarCodigo() {
    const FS = this.pyodide.FS;
    for (const dir of DIRETORIOS) {
      try { FS.mkdir(dir); } catch { /* ja existe */ }
    }
    const ler = this.opts.lerModulo || (async (rel) => {
      const resp = await fetch(`./py/lonatoga/${rel}`);
      if (!resp.ok) throw new Error(`nao achei ${rel}`);
      return resp.text();
    });
    const arquivos = await Promise.all(MODULOS.map(async (rel) => [rel, await ler(rel)]));
    for (const [rel, codigo] of arquivos) FS.writeFile(`/jogo/lonatoga/${rel}`, codigo);
    this.pyodide.runPython('import sys\nif "/jogo" not in sys.path:\n    sys.path.insert(0, "/jogo")');
  }

  /** Chama uma funcao da bridge e devolve JS puro. */
  _call(nome, ...args) {
    const fn = this.bridge[nome];
    const py = fn(...args.map((a) => this.pyodide.toPy(semNull(a))));
    if (py && typeof py.toJs === "function") {
      const js = py.toJs({ dict_converter: Object.fromEntries });
      py.destroy();
      return js;
    }
    return py;
  }

  textos(lang) { return this._call("textos", lang); }
  regioes() { return this._call("regioes"); }
  novoJogo(seed, regiao, nome, genero) { return this._call("novo_jogo", seed, regiao, nome, genero); }
  restaurar(estado) { return this._call("restaurar", estado); }
  painel(estado) { return this._call("painel", estado); }
  previsao(estado, plano) { return this._call("previsao", estado, plano); }
  jogarAno(estado, plano) { return this._call("jogar_ano", estado, plano); }
  responder(estado, resposta) { return this._call("responder", estado, resposta ?? {}); }
}
