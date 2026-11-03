/**
 * Da Lona a Toga: a interface.
 *
 * Este arquivo SO desenha o que a simulacao Python devolve (py/lonatoga/).
 * Nenhuma regra do jogo mora aqui: nada de contas de nota, corte ou dinheiro.
 * Todo texto visivel passa por t() (exceto a tela de carregamento, que roda
 * antes do Python subir; ver CARGA).
 */
import { Engine } from "./pyodide-bridge.js";

const KEY_SAVE = "lonatoga-save";
const KEY_THEME = "lonatoga-theme";

// O modo decide o idioma, de proposito (mesma regra do Lona Preta).
const THEMES = {
  night: { lang: "en", meta: "#131415" },
  bandeira: { lang: "pt", meta: "#f3f6ea" },
};

// Unico texto fora do t(): ainda nao existe Python pra fornecer os textos.
const CARGA = {
  en: { baixando: "Downloading Python…", montando: "Putting the game together…", pronto: "Ready!",
        nota: "Loading real Python in your browser: the same simulation the tests run." },
  pt: { baixando: "Baixando o Python…", montando: "Montando o jogo…", pronto: "Pronto!",
        nota: "Carregando o Python de verdade no navegador: a mesma simulação dos testes." },
};

const AREAS = ["linguagens", "humanas", "natureza", "matematica", "redacao"];
const VIAS = ["ampla", "cota", "prouni", "fies"];
const TRILHA_ICONES = {
  lona: '<path d="M3 20 12 5l9 15z"/><path d="M12 5v15"/>',
  fundamental: '<path d="M4 20l1-4 11-11 3 3-11 11z"/><path d="M14 7l3 3"/>',
  medio: '<path d="M3 5h7a2 2 0 0 1 2 2v12a2 2 0 0 0-2-2H3z"/><path d="M21 5h-7a2 2 0 0 0-2 2v12a2 2 0 0 1 2-2h7z"/>',
  enem: '<rect x="5" y="3" width="14" height="18" rx="2"/><circle cx="9" cy="9" r="1.2"/><circle cx="9" cy="13" r="1.2"/><circle cx="9" cy="17" r="1.2"/><path d="M13 9h3M13 13h3M13 17h3"/>',
  faculdade: '<path d="M3 9l9-5 9 5z"/><path d="M5 10v8M9.5 10v8M14.5 10v8M19 10v8M3 20h18"/>',
  oab: '<path d="M12 4v16M7 20h10M5 8h14"/><path d="M5 8l-3 7a3.5 3.5 0 0 0 6 0zM19 8l-3 7a3.5 3.5 0 0 0 6 0z"/>',
  terra: '<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
};

// ------------------------------------------------------------------ estado da UI

let eng = null;
let T = {};
let theme = "night";
let lang = "en";
let regioes = [];
let est = null;           // estado do jogo (JSON da simulacao)
let pan = null;           // painel calculado pela simulacao
let plano = null;         // plano do ano que o jogador esta montando
let prev = null;          // previsao do plano
let planoT = -1;          // ano do jogo ao qual o plano pertence
let inicio = { regiao: "pontal", genero: "f", nome: "" };
let viasSel = new Set(["ampla", "cota", "prouni"]);
let casoSel = [];
let aviso = "";

// ------------------------------------------------------------------ utilidades

const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* sem armazenamento: segue sem salvar */ } },
  del(k) { try { localStorage.removeItem(k); } catch { /* idem */ } },
};

const esc = (s) => String(s).replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/** Traduz uma chave. {vars} vem de v; {adv}, {o}... vem de g.<genero>.<nome>. */
export function t(key, v = {}) {
  let s = T[key];
  if (v.n === 1 && T[`${key}_1`] !== undefined) s = T[`${key}_1`];
  if (s === undefined) return key;
  const g = est ? est.genero : "f";
  return s.replace(/\{(\w+)\}/g, (m, k) => {
    if (k in v) return esc(v[k]);
    const gk = T[`g.${g}.${k}`];
    return gk !== undefined ? gk : m;
  });
}

const num = (n) => Math.round(n).toLocaleString(lang === "pt" ? "pt-BR" : "en-US");
const brl = (n) => `${n < 0 ? "−" : ""}R$${num(Math.abs(n))}`;
const sgn = (n, f = (x) => String(Math.round(x * 10) / 10)) => `${n > 0 ? "+" : n < 0 ? "−" : ""}${f(Math.abs(n))}`;
const $ = (s) => document.querySelector(s);

function tentar(chave, vars) {
  return T[chave] !== undefined ? t(chave, vars) : "";
}

// ------------------------------------------------------------------ tema e idioma

function escolherTema() {
  const q = new URLSearchParams(location.search).get("theme");
  const salvo = store.get(KEY_THEME);
  let nome = q in THEMES ? q : salvo in THEMES ? salvo : null;
  if (!nome) {
    const claro = typeof matchMedia === "function" && matchMedia("(prefers-color-scheme: light)").matches;
    nome = claro ? "bandeira" : "night";
  }
  aplicarTema(nome);
}

function aplicarTema(nome) {
  theme = nome;
  lang = THEMES[nome].lang;
  document.documentElement.dataset.theme = nome;
  document.documentElement.lang = lang === "pt" ? "pt-BR" : "en";
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute("content", THEMES[nome].meta);
  if (eng && eng.bridge) T = eng.textos(lang);
}

function alternarTema() {
  const novo = theme === "night" ? "bandeira" : "night";
  store.set(KEY_THEME, novo);
  aplicarTema(novo);
  render();
}

// ------------------------------------------------------------------ jogo

function salvar() { if (est) store.set(KEY_SAVE, JSON.stringify(est)); }

function preparar() {
  pan = eng.painel(est);
  if (pan.pode_jogar && planoT !== est.t) {
    planoT = est.t;
    casoSel = [];
    plano = pan.acoes.length
      ? { acoes: Object.fromEntries(pan.acoes.map((a) => [a.id, a.padrao])), foco: pan.foco }
      : null;
  }
  prev = plano && pan.pode_jogar ? eng.previsao(est, plano) : null;
}

function aplicar(novo) {
  if (novo && novo.erro) {
    aviso = novo.erro;
  } else {
    est = novo;
    aviso = "";
    salvar();
  }
  preparar();
  render();
}

function comecar() {
  const q = new URLSearchParams(location.search).get("seed");
  const seed = q && /^\d+$/.test(q) ? Number(q) : Math.floor(Math.random() * 1e9);
  est = eng.novoJogo(seed, inicio.regiao, inicio.nome, inicio.genero);
  planoT = -1;
  salvar();
  preparar();
  render();
}

function novoJogo() {
  if (!window.confirm(t("ui.confirmar_novo"))) return;
  store.del(KEY_SAVE);
  est = null; pan = null; plano = null; prev = null; planoT = -1;
  render();
}

// ------------------------------------------------------------------ pecas de HTML

function barra(valor, { max = 100, marca = null, ruim = false } = {}) {
  const w = Math.max(0, Math.min(100, (valor / max) * 100));
  const m = marca !== null && marca > 0 ? `<u style="left:${Math.min(100, (marca / max) * 100)}%"></u>` : "";
  return `<div class="track${ruim ? " low" : ""}"><i style="width:${w}%"></i>${m}</div>`;
}

function medidor(rotulo, valor, opts = {}) {
  const ruim = opts.invertido ? valor > 70 : valor < 30;
  return `<div class="meter"><span>${rotulo}</span>${barra(valor, { ...opts, ruim })}<b>${Math.round(valor)}</b></div>`;
}

function icone(id) {
  return `<svg viewBox="0 0 24 24" aria-hidden="true">${TRILHA_ICONES[id]}</svg>`;
}

function trilha() {
  return `<ol class="trail" aria-label="${t("trilha.alt")}">${pan.trilha.map((p) =>
    `<li class="${p.estado}"${p.estado === "atual" ? ' aria-current="step"' : ""}>${icone(p.id)}<span>${t(`trilha.${p.id}`)}</span></li>`).join("")}</ol>`;
}

const lona = '<path d="M36 108 74 72l38 36z" fill="var(--art-lona)" stroke="var(--art-lona-2)" stroke-width="2"/><path d="M74 72v36M55 90l19 18M93 90 74 108" stroke="var(--art-lona-2)" stroke-width="1.5"/><path d="M66 108v-16h16v16z" fill="var(--art-door)"/>';
const colunas = (x) => `<path d="M${x} 74h96l-48-22z" fill="var(--art-roof)"/>` + [0, 24, 48, 72].map((d) => `<rect x="${x + 6 + d}" y="76" width="9" height="30" fill="var(--art-wall)"/>`).join("") + `<rect x="${x - 2}" y="106" width="100" height="5" fill="var(--art-wall)"/>`;

function cena(etapa, vitoria) {
  const escola = ["fundamental", "medio", "cursinho"].includes(etapa);
  let lado = "";
  let casa = lona;
  if (escola) {
    lado = '<rect x="250" y="76" width="86" height="30" fill="var(--art-wall)"/><path d="M244 76h98l-49-24z" fill="var(--art-roof)"/><rect x="287" y="88" width="12" height="18" fill="var(--art-door)"/><rect x="262" y="84" width="10" height="10" fill="var(--art-glass)"/><rect x="314" y="84" width="10" height="10" fill="var(--art-glass)"/>';
  } else if (etapa === "faculdade" || etapa === "oab" || etapa === "advocacia") {
    lado = colunas(244);
  }
  if (vitoria) {
    casa = '<rect x="46" y="82" width="62" height="26" fill="var(--art-wall)"/><path d="M40 82h74l-37-26z" fill="var(--art-roof)"/><rect x="72" y="92" width="12" height="16" fill="var(--art-door)"/><path d="M128 56v52" stroke="var(--art-wall)" stroke-width="2"/><path d="M128 56h22v12h-22z" fill="var(--art-leaf)"/>';
    lado += [0, 1, 2, 3].map((i) => `<path d="M${180 + i * 12} 118q6-10 12 0" fill="none" stroke="var(--art-leaf)" stroke-width="3"/>`).join("");
  }
  return `<svg class="cena" viewBox="0 0 400 140" role="img" aria-label="${t("cena.alt")}">
    <defs><linearGradient id="ceu" x1="0" y1="0" x2="0" y2="1"><stop offset="0" style="stop-color:var(--art-sky-a)"/><stop offset="1" style="stop-color:var(--art-sky-b)"/></linearGradient></defs>
    <rect width="400" height="140" fill="url(#ceu)"/>
    <circle cx="340" cy="34" r="15" fill="var(--art-sun)"/>
    <path d="M0 98q80-30 160-6t160-4q50 4 80 8v44H0z" fill="var(--art-hill)"/>
    <rect y="106" width="400" height="34" fill="var(--soil)"/>
    ${lado}${casa}
  </svg>`;
}

function chipsEfeitos(ef, custo = 0) {
  const itens = Object.entries(ef).map(([k, v]) => {
    const nome = k.startsWith("saber_") ? t(`area.${k.slice(6)}`) : t(`stat.${k}`);
    const bom = k === "terra_ameaca" || k === "despejos" ? v < 0 : v > 0;
    const valor = k === "dinheiro" ? `${v > 0 ? "+" : "−"}${brl(Math.abs(v))}` : `${sgn(v)} ${nome}`;
    return `<span class="eff ${bom ? "bom" : "ruim"}">${k === "dinheiro" ? `${valor} ${nome}` : valor}</span>`;
  });
  if (custo) itens.push(`<span class="eff ruim">${t("ui.custa")} ${brl(custo)}</span>`);
  return itens.length ? `<div class="effs">${itens.join("")}</div>` : "";
}

// ------------------------------------------------------------------ tela inicial

function telaInicio() {
  const cartoes = regioes.map((r) => `
    <button class="landc${inicio.regiao === r.key ? " on" : ""}" data-act="regiao" data-r="${r.key}" aria-pressed="${inicio.regiao === r.key}">
      <strong>${t(`reg.${r.key}.nome`)}</strong>
      <span class="calm">${t(`reg.${r.key}.desc`)}</span>
    </button>`).join("");
  const how = [1, 2, 3, 4, 5, 6].map((i) => `<li>${t(`howto.${i}`)}</li>`).join("");
  return `
  ${cabecalho(false)}
  <section class="panel intro">
    ${cena("fundamental", false)}
    <p>${t("start.intro")}</p>
    <label class="field"><span class="label">${t("start.nome")}</span>
      <input id="nome" type="text" maxlength="24" value="${esc(inicio.nome)}" placeholder="${t("start.nome_dica")}" autocomplete="off"></label>
    <div class="field"><span class="label">${t("start.genero")}</span>
      <div class="tabs">
        <button class="btn${inicio.genero === "f" ? " on" : ""}" data-act="genero" data-g="f" aria-pressed="${inicio.genero === "f"}">${t("start.menina")}</button>
        <button class="btn${inicio.genero === "m" ? " on" : ""}" data-act="genero" data-g="m" aria-pressed="${inicio.genero === "m"}">${t("start.menino")}</button>
      </div></div>
    <div class="field"><span class="label">${t("start.regiao")}</span><div class="lands">${cartoes}</div></div>
    <button class="btn go big" data-act="comecar">${t("start.comecar")}</button>
    <details><summary>${t("howto.titulo")}</summary><ul>${how}</ul></details>
  </section>`;
}

function cabecalho(emJogo) {
  const alvo = theme === "night" ? t("theme.to_bandeira") : t("theme.to_night");
  return `<header class="top">
    <div><h1>Da Lona <span>à Toga</span></h1><p class="tag">${t("app.tag")}</p></div>
    <div class="status">
      ${emJogo ? `<button class="btn tbtn" data-act="novo">${t("ui.novo_jogo")}</button>` : ""}
      <button class="btn tbtn" data-act="tema" aria-label="${t("theme.alt")}">${alvo}</button>
    </div></header>`;
}

// ------------------------------------------------------------------ tela do jogo

function chips() {
  const serie = pan.series_total ? t("chip.serie", { n: est.serie, total: pan.series_total }) : "";
  const tent = est.etapa === "cursinho" ? t("chip.tentativa", { n: est.serie }) : "";
  const info = [serie, tent].filter(Boolean).join(" · ");
  return `<div class="status chips">
    <div class="chip"><b>${t("chip.idade", { n: pan.idade })}</b> ${pan.ano}</div>
    <div class="chip"><b>${t(`etapa.${pan.etapa}`)}</b>${info ? ` ${info}` : ""}</div>
    <div class="chip"><span>${t("stat.dinheiro")}</span> <b>${brl(est.dinheiro)}</b></div>
    ${est.divida > 0 ? `<div class="chip debt"><span>${t("stat.divida")}</span> <b>${brl(est.divida)}</b></div>` : ""}
  </div>`;
}

function painelPlano() {
  const linhas = pan.acoes.map((a) => {
    const v = plano.acoes[a.id] ?? 0;
    const bloq = a.max === 0;
    return `<div class="row act${bloq ? " off" : ""}">
      <div class="actname"><b>${t(`acao.${a.id}`)}</b><small>${bloq ? t(a.bloqueio) : t(`acao.${a.id}.desc`)}</small></div>
      <div class="ctl">
        <button class="btn" data-act="menos" data-a="${a.id}" aria-label="${t("ui.menos")} ${t(`acao.${a.id}`)}"${v <= 0 || bloq ? " disabled" : ""}>−</button>
        <span class="n">${v}</span>
        <button class="btn" data-act="mais" data-a="${a.id}" aria-label="${t("ui.mais")} ${t(`acao.${a.id}`)}"${bloq || v >= a.max || prev.restante <= 0 ? " disabled" : ""}>+</button>
      </div></div>`;
  }).join("");
  const foco = pan.areas.length && (plano.acoes.estudo ?? 0) > 0 ? `
    <div class="focus"><span class="label">${t("plano.foco")}</span>
      <div class="tabs wrap">${pan.areas.map((a) =>
        `<button class="btn${plano.foco === a ? " on" : ""}" data-act="foco" data-a="${a}" aria-pressed="${plano.foco === a}">${t(`area.${a}`)}</button>`).join("")}</div></div>` : "";
  const avisos = prev.avisos.map((w) => `<li class="aviso ${w.nivel}">${t(w.k, w.v)}</li>`).join("");
  return `
  <section class="panel">
    <div class="landhead"><h2>${t("plano.titulo")}</h2>
      <div class="budget${prev.restante < 0 ? " over" : ""}"><b>${prev.restante}</b> ${t("plano.restante")} <small>/ ${pan.orcamento}</small></div></div>
    <p class="calm">${t(`plano.dica.${pan.etapa}`)}</p>
    <div class="acts">${linhas}</div>
    ${foco}
    ${avisos ? `<ul class="avisos">${avisos}</ul>` : ""}
    <div class="calm eco">${t("plano.dinheiro", { fundo: brl(prev.fundo), custo: brl(prev.custo) })}</div>
    <button class="btn go big" data-act="jogar"${prev.valido ? "" : " disabled"}>${t("plano.jogar", { n: pan.idade })}</button>
  </section>`;
}

function painelCaso() {
  const c = pan.caso;
  const passos = c.etapas.map((e, i) =>
    `<li class="${i < c.idx ? "feito" : i === c.idx ? "atual" : "futuro"}">${t(`caso.etapa.${e}`)}</li>`).join("");
  const cartoes = Object.entries(c.acoes).map(([id, a]) => {
    const on = casoSel.includes(id);
    const sem = a.custo > Math.max(est.dinheiro, 0);
    const bloqueada = sem || (!on && casoSel.length >= c.max_acoes);
    const efs = [];
    if (a.defesa) efs.push(`<span class="eff bom">${sgn(a.defesa)} ${t("caso.defesa")}</span>`);
    if (a.acusacao) efs.push(`<span class="eff bom">${sgn(a.acusacao)} ${t("caso.acusacao")}</span>`);
    if (a.custo) efs.push(`<span class="eff ruim">${t("ui.custa")} ${brl(a.custo)}</span>`);
    return `<button class="landc${on ? " on" : ""}" data-act="caso-acao" data-a="${id}" aria-pressed="${on}"${bloqueada ? " disabled" : ""}>
      <strong>${t(`caso.acao.${id}`)}</strong><span class="calm">${t(`caso.acao.${id}.desc`)}</span><div class="effs">${efs.join("")}</div></button>`;
  }).join("");
  return `
  <section class="panel case">
    <div class="landhead"><h2>${t("caso.titulo")}</h2><span class="calm">${t("caso.sub", { n: c.vitorias })}</span></div>
    <p class="calm">${t("caso.intro")}</p>
    <ol class="steps">${passos}</ol>
    <h3>${t(`caso.etapa.${c.etapa}`)}</h3>
    <div class="meter wide"><span>${t("caso.defesa")}</span>${barra(c.defesa, { max: 120 })}<b>${Math.round(c.defesa)}</b></div>
    <div class="meter wide owner"><span>${t("caso.acusacao")}</span>${barra(c.acusacao, { max: 120 })}<b>${Math.round(c.acusacao)}</b></div>
    <p class="calm">${t("caso.escolha", { n: c.max_acoes })}</p>
    <div class="lands">${cartoes}</div>
    <button class="btn go big" data-act="caso-jogar">${t("caso.jogar")}</button>
  </section>`;
}

function painelSaber() {
  const escola = pan.areas.length > 0;
  const barras = escola
    ? AREAS.map((a) => medidor(t(`area.${a}`), est.saber[a], { marca: pan.esperado })).join("")
    : ["juridico", "pratica", "rede"].map((k) => medidor(t(`stat.${k}`), est[k])).join("");
  const nota = escola && pan.esperado ? `<p class="calm">${t("saber.marca", { n: Math.round(pan.esperado) })}</p>` : "";
  return `
  <section class="panel"><div class="label">${t("saber.titulo")}</div>${barras}${nota}</section>`;
}

function painelVida() {
  return `
  <section class="panel"><div class="label">${t("vida.titulo")}</div>
    ${medidor(t("stat.saude"), est.saude)}
    ${medidor(t("stat.animo"), est.animo)}
    ${pan.mostra_comida ? medidor(t("stat.comida"), est.comida) : ""}
    ${medidor(t("stat.luta"), est.luta)}
    ${medidor(t("stat.terra_ameaca"), est.terra_ameaca, { invertido: true })}
    <p class="calm">${t("vida.terra")}</p>
  </section>`;
}

function textoLog(item) {
  const v = { ...item.v };
  if (v.regiao) v.regiao = t(`reg.${v.regiao}.nome`);
  if (v.via) v.via = t(`via.${v.via}`);
  if (item.k === "log.caso_ganhou" || item.k === "log.caso_perdeu") v.etapa = t(`caso.etapa.${v.etapa}`);
  else if (v.etapa) v.etapa = t(`etapa.${v.etapa}`);
  if (v.motivo) v.motivo = t(`rel.motivo.${v.motivo}`);
  if (v.v !== undefined) v.v = brl(v.v);
  if (item.k === "log.evento") {
    v.titulo = t(`ev.${v.ev}.titulo`);
    const op = tentar(`ev.${v.ev}.${v.op}`);
    if (!op) return t("log.evento_ok", v);
    v.escolha = op;
  }
  return t(item.k, v);
}

function painelDiario() {
  const itens = est.log.slice(0, 10).map((l) =>
    `<li><span class="m">${l.idade}</span>${textoLog(l)}</li>`).join("");
  return `<section class="panel"><div class="label">${t("log.titulo")}</div><ul class="log">${itens}</ul></section>`;
}

function telaJogo() {
  const vit = est.fim && est.fim.tipo === "vitoria";
  return `
  ${cabecalho(true)}
  ${chips()}
  ${trilha()}
  <div class="cols">
    <div class="col">
      <section class="panel scene">${cena(est.etapa, vit)}</section>
      ${pan.pode_jogar ? (pan.caso ? painelCaso() : painelPlano()) : `<section class="panel"><p class="calm">${t("ui.aguardando")}</p></section>`}
    </div>
    <div class="col">${painelVida()}${painelSaber()}${painelDiario()}</div>
  </div>`;
}

// ------------------------------------------------------------------ janelas (fila de telas)

function linhaDiff(rotulo, a, b, fmt = (x) => String(Math.round(x))) {
  const d = b - a;
  const cls = Math.abs(d) < 0.05 ? "" : d > 0 ? "bom" : "ruim";
  return `<div class="row"><span>${rotulo}</span><span class="diff">${fmt(a)} → <b>${fmt(b)}</b> <i class="${cls}">${Math.abs(d) < 0.05 ? "" : sgn(d, fmt)}</i></span></div>`;
}

function modalRelatorio(h) {
  const antes = h.antes, depois = h.depois;
  let veredito;
  if (h.etapa === "oab") veredito = "";
  else if (h.aprovado) veredito = `<p class="verdict ok">${t("rel.aprovado")}</p>`;
  else veredito = `<p class="verdict no">${t(`rel.reprovou.${h.motivo}`)}</p>`;
  const boletim = h.tem_boletim ? `
    <div class="boletim"><div class="nota${h.aprovado ? "" : " no"}">${h.boletim.toFixed(1)}</div>
    <div><b>${t("rel.boletim")}</b><br><small>${t("rel.esperado", { n: Math.round(h.esperado) })} · ${t("rel.media", { n: h.media })}</small></div></div>` : "";
  const fac = h.etapa === "faculdade" ? `<p class="calm">${t("rel.fac", { n: Math.round(h.media), min: Math.round(h.esperado) })}</p>` : "";
  const areas = h.tem_boletim || h.etapa === "cursinho"
    ? AREAS.map((a) => linhaDiff(t(`area.${a}`), antes[a], depois[a], (x) => x.toFixed(1))).join("")
    : ["juridico", "pratica", "rede"].map((k) => linhaDiff(t(`stat.${k}`), antes[k], depois[k], (x) => x.toFixed(1))).join("");
  const dinheiro = h.fundo === h.renda
    ? t("rel.dinheiro2", { renda: brl(h.renda), custo: brl(h.custo) })
    : t("rel.dinheiro", { renda: brl(h.renda), fundo: brl(h.fundo), custo: brl(h.custo) });
  const falta = h.falta_dinheiro ? `<p class="aviso atencao">${t("rel.falta_dinheiro")}</p>` : "";
  return `
    <h2>${t("rel.titulo", { n: h.idade, ano: h.ano })}</h2>
    ${boletim}${veredito}${fac}
    <div class="grid2">
      <div><div class="label">${t("rel.vida")}</div>
        ${linhaDiff(t("stat.saude"), antes.saude, depois.saude)}
        ${linhaDiff(t("stat.animo"), antes.animo, depois.animo)}
        ${pan.mostra_comida ? linhaDiff(t("stat.comida"), antes.comida, depois.comida) : ""}
        ${linhaDiff(t("stat.luta"), antes.luta, depois.luta)}
        ${linhaDiff(t("stat.terra_ameaca"), antes.terra_ameaca, depois.terra_ameaca)}</div>
      <div><div class="label">${t("rel.saberes")}</div>${areas}</div>
    </div>
    <p class="calm">${dinheiro}</p>${falta}
    <button class="btn go" data-act="continuar">${t("ui.continuar")}</button>`;
}

function modalEvento(h) {
  const unico = h.opcoes.length === 1;
  const corpo = `<h2>${t(`ev.${h.id}.titulo`)}</h2><p>${t(`ev.${h.id}.texto`)}</p>`;
  if (unico) {
    return `${corpo}${chipsEfeitos(h.opcoes[0].efeitos)}<button class="btn go" data-act="opcao" data-o="ok">${t("ui.continuar")}</button>`;
  }
  const botoes = h.opcoes.map((o) => {
    const sem = o.custo > Math.max(est.dinheiro, 0);
    return `<button class="landc" data-act="opcao" data-o="${o.id}"${sem ? " disabled" : ""}>
      <strong>${t(`ev.${h.id}.${o.id}`)}</strong>${chipsEfeitos(o.efeitos, o.custo)}</button>`;
  }).join("");
  return `${corpo}<div class="lands">${botoes}</div>`;
}

function modalEventoRes(h) {
  return `<h2>${t(`ev.${h.id}.titulo`)}</h2><p>${t(`ev.${h.id}.${h.opcao}.res`)}</p>${chipsEfeitos(h.efeitos, h.custo)}
    <button class="btn go" data-act="continuar">${t("ui.continuar")}</button>`;
}

function notasProva(p) {
  const areas = ["linguagens", "humanas", "natureza", "matematica"].map((a) =>
    `<div class="row"><span>${t(`area.${a}`)}</span><b>${p.areas[a]}</b></div>`).join("");
  const comps = p.comps.map((c, i) => `<span class="comp">C${i + 1}<b>${c}</b></span>`).join("");
  return `${areas}
    <div class="row"><span>${t("area.redacao")}</span><b>${p.redacao}</b></div>
    <div class="comps">${comps}</div>
    ${p.zerou ? `<p class="aviso perigo">${t("enem.zerou")}</p>` : ""}
    <div class="row total"><span>${t("enem.media")}</span><b>${p.media.toFixed(1)}</b></div>`;
}

function modalTreineiro(h) {
  const sem = est.dinheiro < h.taxa;
  return `<h2>${t("trein.titulo")}</h2><p>${t("trein.texto", { taxa: brl(h.taxa) })}</p>
    <p class="calm">${t("trein.aviso")}</p>
    <div class="bar">
      <button class="btn go" data-act="treineiro" data-s="1"${sem ? " disabled" : ""}>${t("trein.sim", { taxa: brl(h.taxa) })}</button>
      <button class="btn" data-act="treineiro" data-s="0">${t("trein.nao")}</button>
    </div>${sem ? `<p class="aviso atencao">${t("trein.sem_dinheiro")}</p>` : ""}`;
}

function modalTreinoRes(h) {
  return `<h2>${t("treino.titulo")}</h2><p>${t("treino.texto")}</p>${notasProva(h.prova)}
    <p>${t("treino.diag", { area: t(`area.${h.prova.fraca}`) })}</p>
    ${chipsEfeitos({ exp_prova: h.ganho })}
    <button class="btn go" data-act="continuar">${t("ui.continuar")}</button>`;
}

function modalEnem(h) {
  const pdm = h.resgate ? `<p class="aviso ok">${t("enem.pdm", { v: brl(h.resgate) })}</p>` : "";
  return `<h2>${t("enem.titulo", { n: h.tentativa })}</h2><p>${t("enem.texto")}</p>${notasProva(h.prova)}${pdm}
    <button class="btn go" data-act="continuar">${t("ui.continuar")}</button>`;
}

function modalVias(h) {
  const itens = VIAS.map((v) => {
    const on = viasSel.has(v);
    const ref = v === "fies" ? t("vias.fies_min", { n: h.minimo }) : t("vias.ref", { n: h.ref[v] });
    const minimo = v === "prouni" || v === "fies"
      ? `<span class="eff ${h.min_ok ? "bom" : "ruim"}">${h.min_ok ? t("vias.min_ok") : t("vias.min_no", { n: h.minimo })}</span>` : "";
    return `<button class="landc${on ? " on" : ""}" data-act="via" data-v="${v}" aria-pressed="${on}">
      <strong>${t(`via.${v}`)}</strong><span class="calm">${t(`via.${v}.desc`)}</span>
      <div class="effs"><span class="eff">${ref}</span>${minimo}</div></button>`;
  }).join("");
  return `<h2>${t("vias.titulo")}</h2><p>${t("vias.texto", { n: h.prova.media.toFixed(1) })}</p>
    <div class="lands">${itens}</div>
    <p class="calm">${t("vias.dica")}</p>
    <button class="btn go" data-act="vias-ok">${t("vias.confirmar")}</button>`;
}

function modalAdmissao(h) {
  const r = h.res;
  const linhas = r.escolhidas.map((v) => {
    const d = r.detalhe[v];
    const estado = d.ok ? (r.via === v ? t("adm.escolhida") : t("adm.passou_mas")) : t(`adm.nao.${d.motivo}`);
    const corte = v === "fies" ? "" : ` · ${t("adm.corte", { n: d.corte })}`;
    return `<div class="row"><span>${t(`via.${v}`)}${corte}</span><b class="${d.ok ? "bom" : "ruim"}">${estado}</b></div>`;
  }).join("");
  const topo = r.via
    ? `<p class="verdict ok">${t("adm.passou", { via: t(`via.${r.via}`) })}</p><p>${t(`adm.texto.${r.via}`)}</p>`
    : `<p class="verdict no">${t(r.escolhidas.length ? "adm.nenhuma" : "adm.sem_inscricao")}</p><p>${t("adm.volta")}</p>`;
  return `<h2>${t("adm.titulo")}</h2><div class="row total"><span>${t("enem.media")}</span><b>${h.prova.media.toFixed(1)}</b></div>${linhas}${topo}
    <button class="btn go" data-act="continuar">${t("ui.continuar")}</button>`;
}

function modalOab(h) {
  const l1 = h.fase1_antes ? t("oab.f1_antes")
    : h.fase1 === null ? "" : t(h.fase1 ? "oab.f1_ok" : "oab.f1_no");
  const l2 = h.fase2 === null ? t("oab.f2_nao") : t(h.fase2 ? "oab.f2_ok" : "oab.f2_no");
  const fim = h.passou ? `<p class="verdict ok">${t("oab.passou")}</p>` : `<p class="verdict no">${t("oab.nao")}</p><p>${t("oab.dica")}</p>`;
  return `<h2>${t("oab.titulo", { n: h.tentativa })}</h2>${l1 ? `<p>${l1}</p>` : ""}<p>${l2}</p>${fim}
    <button class="btn go" data-act="continuar">${t("ui.continuar")}</button>`;
}

function modalCaso(h) {
  const usadas = h.usadas.length ? h.usadas.map((a) => t(`caso.acao.${a}`)).join(" + ") : t("caso.nenhuma");
  return `<h2>${t(`caso.etapa.${h.etapa}`)}</h2>
    <p class="calm">${t("caso.usou", { acoes: usadas })}</p>
    <p class="verdict ${h.ganhou ? "ok" : "no"}">${t(`caso.etapa.${h.etapa}.${h.ganhou ? "ganhou" : "perdeu"}`)}</p>
    <div class="meter wide"><span>${t("caso.defesa")}</span>${barra(h.defesa, { max: 120 })}<b>${Math.round(h.defesa)}</b></div>
    <div class="meter wide owner"><span>${t("caso.acusacao")}</span>${barra(h.acusacao, { max: 120 })}<b>${Math.round(h.acusacao)}</b></div>
    <button class="btn go" data-act="continuar">${t("ui.continuar")}</button>`;
}

function modalFim() {
  const f = est.fim;
  const pares = [
    ["fim.idade", f.idade], ["fim.anos", f.anos], ["fim.familia", f.familia],
    ["fim.despejos", f.despejos], ["fim.luta", f.luta], ["fim.reprovacoes", f.reprovacoes],
    ["fim.enem", f.enem_tentativas], ["fim.oab", f.oab_tentativas],
  ];
  if (f.divida > 0) pares.push(["fim.divida", brl(f.divida)]);
  const grade = pares.map(([k, v]) => `<div class="stat"><b>${v}</b><span>${t(k)}</span></div>`).join("");
  const titulo = t(`fim.${f.tipo}.titulo`);
  const texto = t(`fim.${f.tipo}.texto`, { nome: est.nome, regiao: t(`reg.${f.regiao}.nome`), via: f.via ? t(`via.${f.via}`) : "" });
  const titulo_terra = f.tipo === "vitoria" ? `<div class="deed" role="img" aria-label="${t("fim.titulo_alt")}">
    <b>${t("fim.deed.titulo")}</b><span>${t("fim.deed.texto", { regiao: t(`reg.${f.regiao}.nome`), nome: est.nome })}</span></div>` : "";
  return `<h2>${titulo}</h2>${titulo_terra}<p>${texto}</p>
    <div class="statgrid">${grade}</div>
    <div class="row total"><span>${t("fim.pontos")}</span><b>${num(f.pontos)}</b></div>
    <button class="btn go" data-act="novo-sem-confirmar">${t("fim.de_novo")}</button>`;
}

function modalHtml() {
  if (!est) return "";
  const h = est.fila[0];
  if (!h) return est.fim && est.fim.tipo ? modalFim() : "";
  switch (h.tipo) {
    case "relatorio": return modalRelatorio(h);
    case "evento": return modalEvento(h);
    case "evento_res": return modalEventoRes(h);
    case "treineiro": return modalTreineiro(h);
    case "treino_res": return modalTreinoRes(h);
    case "enem": return modalEnem(h);
    case "vias": return modalVias(h);
    case "admissao": return modalAdmissao(h);
    case "oab": return modalOab(h);
    case "caso": return modalCaso(h);
    default: return `<button class="btn go" data-act="continuar">${t("ui.continuar")}</button>`;
  }
}

// ------------------------------------------------------------------ desenhar

function render() {
  const app = $("#app");
  if (!app) return;
  if (!est) {
    app.innerHTML = telaInicio();
    $("#ov").hidden = true;
    return;
  }
  app.innerHTML = telaJogo() + (aviso ? `<p class="toast" role="alert">${esc(aviso)}</p>` : "");
  const m = modalHtml();
  const ov = $("#ov");
  ov.hidden = !m;
  $("#modal").innerHTML = m;
  if (m) {
    const primeiro = $("#modal button:not([disabled])");
    if (primeiro) primeiro.focus({ preventScroll: true });
  }
}

// ------------------------------------------------------------------ cliques

function mudar(acao, delta) {
  const a = pan.acoes.find((x) => x.id === acao);
  if (!a) return;
  const v = Math.max(0, Math.min(a.max, (plano.acoes[acao] ?? 0) + delta));
  plano.acoes[acao] = v;
  prev = eng.previsao(est, plano);
  render();
}

function tratar(ev) {
  const el = ev.target.closest("[data-act]");
  if (!el || el.disabled) return;
  const d = el.dataset;
  switch (d.act) {
    case "tema": alternarTema(); break;
    case "novo": novoJogo(); break;
    case "novo-sem-confirmar":
      store.del(KEY_SAVE); est = null; pan = null; plano = null; prev = null; planoT = -1; render(); break;
    case "regiao": inicio.regiao = d.r; render(); break;
    case "genero": inicio.genero = d.g; render(); break;
    case "comecar": comecar(); break;
    case "mais": mudar(d.a, +1); break;
    case "menos": mudar(d.a, -1); break;
    case "foco": plano.foco = d.a; prev = eng.previsao(est, plano); render(); break;
    case "jogar": aplicar(eng.jogarAno(est, plano)); break;
    case "caso-acao":
      casoSel = casoSel.includes(d.a) ? casoSel.filter((x) => x !== d.a) : [...casoSel, d.a];
      render(); break;
    case "caso-jogar": { const sel = casoSel; casoSel = []; aplicar(eng.jogarAno(est, { casos: sel })); break; }
    case "continuar": aplicar(eng.responder(est, {})); break;
    case "opcao": aplicar(eng.responder(est, { opcao: d.o })); break;
    case "treineiro": aplicar(eng.responder(est, { inscrever: d.s === "1" })); break;
    case "via": viasSel.has(d.v) ? viasSel.delete(d.v) : viasSel.add(d.v); render(); break;
    case "vias-ok": aplicar(eng.responder(est, { vias: [...viasSel] })); break;
    default: break;
  }
}

function digitando(ev) {
  if (ev.target && ev.target.id === "nome") inicio.nome = ev.target.value;
}

// ------------------------------------------------------------------ carga

function mostrarCarga(etapa, pct) {
  const caixa = $("#carregando");
  if (!caixa) return;
  const L = CARGA[lang];
  const txt = caixa.querySelector(".carga-txt");
  const nota = caixa.querySelector(".carga-nota");
  const barraDentro = caixa.querySelector(".barra-dentro");
  if (txt) txt.textContent = L[etapa];
  if (nota) nota.textContent = L.nota;
  if (barraDentro) barraDentro.style.width = `${pct}%`;
}

/** Sobe o jogo. `opts.engine` deixa os testes injetarem um motor ja carregado. */
export async function boot(opts = {}) {
  escolherTema();
  mostrarCarga("baixando", 5);
  eng = opts.engine || new Engine(opts.engineOpts || {});
  if (!eng.bridge) await eng.iniciar(mostrarCarga);
  T = eng.textos(lang);
  regioes = eng.regioes();
  const salvo = store.get(KEY_SAVE);
  if (salvo) {
    try { est = eng.restaurar(JSON.parse(salvo)); } catch { est = null; }
  }
  document.addEventListener("click", tratar);
  document.addEventListener("input", digitando);
  const c = $("#carregando");
  if (c) c.remove();
  if (est) preparar();
  render();
  return {
    get estado() { return est; },
    get painel() { return pan; },
    /** Para testes: entra direto num estado de jogo ja pronto. */
    carregar(estado) { est = eng.restaurar(estado); planoT = -1; aviso = ""; preparar(); render(); },
  };
}

if (!globalThis.__LONATOGA_TESTE__) boot();
