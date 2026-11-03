#!/usr/bin/env node
/*
 * Screenshot do jogo no Chrome headless. Sem dependencias.
 *
 *   node scripts/shot.mjs <night|bandeira> <saida.png> [save.json] [largura] [altura]
 *
 * Sobe um servidor temporario com a pasta do projeto e, se vier um save.json,
 * injeta esse estado no localStorage antes do jogo carregar (o index.html em disco
 * nunca e alterado). Gere saves com `python3 tools/make_saves.py <pasta>`.
 * O Pyodide vem do CDN, entao precisa de internet. CHROME=/caminho se o Chrome
 * nao estiver no lugar padrao do macOS.
 */
import { createServer } from "node:http";
import { readFileSync, existsSync, statSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname, resolve, extname } from "node:path";
import { fileURLToPath } from "node:url";
import { execFile } from "node:child_process";

const [tema, saida, savePath, w = "1100", h = "1000"] = process.argv.slice(2);
if (!["night", "bandeira"].includes(tema) || !saida) {
  console.error("uso: node scripts/shot.mjs <night|bandeira> <saida.png> [save.json] [largura] [altura]");
  process.exit(2);
}
const raiz = join(dirname(fileURLToPath(import.meta.url)), "..");
const chrome = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const tipos = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".py": "text/plain", ".json": "application/json" };

let html = readFileSync(join(raiz, "index.html"), "utf8");
if (savePath) {
  const save = readFileSync(resolve(savePath), "utf8");
  const inj = `<script>try{localStorage.setItem("lonatoga-save",${JSON.stringify(save)});}catch(e){}</script>`;
  html = html.replace('<script type="module"', `${inj}\n<script type="module"`);
}

const servidor = createServer((req, res) => {
  const url = new URL(req.url, "http://x");
  let rel = decodeURIComponent(url.pathname);
  if (rel === "/" || rel === "/index.html") { res.writeHead(200, { "content-type": "text/html" }); return res.end(html); }
  const arq = join(raiz, rel);
  if (!arq.startsWith(raiz) || !existsSync(arq) || !statSync(arq).isFile()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { "content-type": tipos[extname(arq)] || "application/octet-stream", "cache-control": "no-store" });
  res.end(readFileSync(arq));
});
await new Promise((ok) => servidor.listen(0, "127.0.0.1", ok));
const porta = servidor.address().port;
const perfil = mkdtempSync(join(tmpdir(), "lonatoga-chrome-"));
const args = ["--headless=new", "--disable-gpu", "--hide-scrollbars", `--user-data-dir=${perfil}`,
  `--window-size=${w},${h}`, "--virtual-time-budget=60000", `--screenshot=${resolve(saida)}`,
  `http://127.0.0.1:${porta}/?theme=${tema}`];
execFile(chrome, args, { timeout: 120000 }, (err) => {
  servidor.close();
  if (err) { console.error("chrome falhou:", err.message); process.exit(1); }
  console.log("wrote " + resolve(saida));
});
