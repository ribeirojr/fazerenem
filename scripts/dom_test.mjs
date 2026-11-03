/**
 * Joga um jogo inteiro pela interface (app.js) num DOM simulado (jsdom), com o
 * Pyodide de verdade por tras. E o mais perto do navegador que da sem abrir um.
 *
 *   node scripts/dom_test.mjs [seed]
 *
 * Confere, a cada passo e nos DOIS idiomas, que nenhuma chave de texto "vaza"
 * pra tela (ex: 'rel.titulo' no lugar do texto), que nao ha erro de JS e que o
 * jogo chega a um final. Sai com codigo 1 se algo falhar.
 */
import { JSDOM } from "jsdom";
import { loadPyodide } from "pyodide";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), "..");
const seed = process.argv[2] || "5";

const dom = new JSDOM(readFileSync(join(RAIZ, "index.html"), "utf8"), {
  url: `http://localhost:8765/?theme=night&seed=${seed}`,
  pretendToBeVisual: true,
});
const { window } = dom;
for (const k of ["document", "Element", "HTMLElement", "Node", "location", "localStorage", "getComputedStyle"]) {
  try { Object.defineProperty(globalThis, k, { value: window[k], configurable: true, writable: true }); } catch { /* somente leitura */ }
}
Object.defineProperty(globalThis, "window", { value: window, configurable: true, writable: true });
window.confirm = () => true;
globalThis.__LONATOGA_TESTE__ = true;

const erros = [];
window.addEventListener("error", (e) => erros.push(e.message));
const consoleErro = console.error;
console.error = (...a) => { erros.push(a.join(" ")); consoleErro(...a); };

// ---- motor real
const require = createRequire(import.meta.url);
const pyDir = dirname(require.resolve("pyodide/package.json"));
const { Engine } = await import(pathToFileURL(join(RAIZ, "pyodide-bridge.js")).href);
const eng = new Engine({
  loadPyodide,
  indexURL: pyDir + "/",
  lerModulo: async (rel) => readFileSync(join(RAIZ, "py", "lonatoga", rel), "utf8"),
});
const mod = await import(pathToFileURL(join(RAIZ, "app.js")).href);
const app = await mod.boot({ engine: eng });

const $ = (s) => window.document.querySelector(s);
const $$ = (s) => [...window.document.querySelectorAll(s)];
const falhas = [];
const falha = (msg) => { falhas.push(msg); console.log("  FALHA:", msg); };

// ---- vigia de chaves vazando
const VAZOU = /\b[a-z]{2,}(?:\.[a-z0-9_]+)+\b/g;
function escanear(rotulo) {
  const texto = window.document.body.textContent;
  const achados = [...new Set(texto.match(VAZOU) || [])].filter((x) => !/^(www|https?)\./.test(x));
  if (achados.length) falha(`${rotulo}: chave de texto na tela: ${achados.join(", ")}`);
  if (/undefined|NaN|\[object/.test(texto)) falha(`${rotulo}: 'undefined/NaN/[object]' na tela`);
}
function escanearNosDoisIdiomas(rotulo) {
  escanear(`${rotulo}/${window.document.documentElement.lang}`);
  $('[data-act="tema"]').click();
  escanear(`${rotulo}/${window.document.documentElement.lang}`);
  $('[data-act="tema"]').click();
}

// ---- 1. tela inicial
console.log("=== 1. tela inicial ===");
if ($("#carregando")) falha("a tela de carregamento nao saiu");
if ($$(".landc").length !== 4) falha(`esperava 4 regioes, achei ${$$(".landc").length}`);
escanearNosDoisIdiomas("inicio");
const tituloNight = $("header.top .tag").textContent;
$('[data-act="tema"]').click();
if (window.document.documentElement.dataset.theme !== "bandeira" || window.document.documentElement.lang !== "pt-BR") falha("o Modo Bandeira nao ligou o portugues");
if ($("header.top .tag").textContent === tituloNight) falha("o texto nao mudou de idioma");
$('[data-act="tema"]').click();
console.log("  titulo (night):", tituloNight);

$$(".landc")[1].click(); // Sul do Para
const campoNome = $("#nome");
campoNome.value = "Teste <b>x</b>";
campoNome.dispatchEvent(new window.Event("input", { bubbles: true }));
$('[data-act="comecar"]').click();
if (!$(".trail")) falha("nao entrou no jogo");
if ($("#app").innerHTML.includes("<b>x</b>")) falha("nome do jogador nao foi escapado (XSS)");

// ---- 2. jogar ate o fim
console.log("\n=== 2. jogando um jogo inteiro ===");
let passos = 0;
const vistos = new Set();
const modais = {};
while (passos++ < 600) {
  const ov = $("#ov");
  const aberto = ov && !ov.hidden;
  if (aberto) {
    const botoes = $$("#modal button:not([disabled])");
    const rotulo = ($("#modal h2")?.textContent || "").slice(0, 40);
    modais[rotulo.replace(/\d+/g, "N")] = (modais[rotulo.replace(/\d+/g, "N")] || 0) + 1;
    if (passos % 5 === 0) escanearNosDoisIdiomas(`modal ${passos}`); else escanear(`modal ${passos}`);
    const act = (a) => botoes.find((b) => b.dataset.act === a);
    const fim = act("novo-sem-confirmar");
    if (fim) {
      console.log("  final:", $("#modal h2").textContent, "|", $("#modal .deed b")?.textContent || "(sem titulo)");
      vistos.add("fim");
      break;
    }
    (act("opcao") || act("treineiro") || act("vias-ok") || act("continuar") || botoes[0]).click();
    continue;
  }
  if (passos % 3 === 0) escanearNosDoisIdiomas(`jogo ${passos}`); else escanear(`jogo ${passos}`);
  const casoAcoes = $$('[data-act="caso-acao"]:not([disabled])');
  if (casoAcoes.length) {
    casoAcoes.slice(0, 2).forEach((b) => b.click());
    $('[data-act="caso-jogar"]').click();
    vistos.add("caso");
    continue;
  }
  const jogar = $('[data-act="jogar"]');
  if (!jogar || jogar.disabled) { falha(`sem botao de jogar utilizavel no passo ${passos}`); break; }
  // exercita os botoes de + e -: tira 1 de descanso e poe de volta
  const menos = $('[data-act="menos"][data-a="descanso"]');
  const mais = $('[data-act="mais"][data-a="descanso"]');
  if (menos && !menos.disabled && mais) { menos.click(); $('[data-act="mais"][data-a="descanso"]').click(); }
  $('[data-act="jogar"]').click();
}
if (!vistos.has("fim")) falha("o jogo nao chegou a um final");

// ---- 3. conferencias finais
console.log("\n=== 3. conferencias ===");
const salvo = JSON.parse(window.localStorage.getItem("lonatoga-save") || "null");
if (!salvo || !salvo.fim || !salvo.fim.tipo) falha("o save nao guardou o final");
else console.log("  save ok, final:", salvo.fim.tipo, "idade", salvo.fim.idade);
const restaurado = eng.restaurar(JSON.parse(JSON.stringify(salvo)));
if (JSON.stringify(restaurado) !== JSON.stringify(salvo)) falha("restaurar mudou o save (ida e volta nao e identica)");
for (const k of ["relatorio", "evento", "Enem", "caso"]) {
  if (![...Object.keys(modais)].some((m) => m.toLowerCase().includes(k.toLowerCase()) || k === "relatorio" || k === "evento")) {
    /* nomes de janela variam por idioma; so listamos abaixo */
  }
}
console.log("  tipos de janela vistos:", Object.keys(modais).length, "| passos:", passos);
console.log("  teve tela do caso:", vistos.has("caso"));
// ---- 4. um final de vitoria (o caminho acima usa escolhas ingenuas e costuma perder)
console.log("\n=== 4. vitoria ===");
{
  const e = JSON.parse(JSON.stringify(salvo));
  Object.assign(e, { fim: {}, fila: [], etapa: "advocacia", juridico: 95, pratica: 80, rede: 80, luta: 80 });
  e.caso = { idx: 2, defesa: 130, acusacao: 5, vitorias: 2, usos: {}, improdutiva: 14 };
  app.carregar(e);
  escanearNosDoisIdiomas("caso");
  if (!$('[data-act="caso-jogar"]')) falha("sem painel do caso");
  $$('[data-act="caso-acao"]:not([disabled])').slice(0, 2).forEach((b) => b.click());
  $('[data-act="caso-jogar"]').click();
  for (let i = 0; i < 6 && !$(".deed"); i++) {
    escanearNosDoisIdiomas(`vitoria ${i}`);
    ($$("#modal button:not([disabled])")[0] || { click() {} }).click();
  }
  if (!$(".deed")) falha("o titulo da terra nao apareceu");
  else {
    console.log("  titulo:", $(".deed b").textContent, "|", $("#modal h2").textContent);
    escanearNosDoisIdiomas("titulo");
    if (!$$(".trail li.feito").length || $$(".trail li.atual").length) falha("a trilha nao fechou na vitoria");
  }
}

if (erros.length) falha(`erros de JS: ${erros.slice(0, 3).join(" | ")}`);

if (falhas.length) {
  console.log(`\n${falhas.length} falha(s)`);
  process.exit(1);
}
console.log("\nOK");
