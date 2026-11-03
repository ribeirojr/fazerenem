# Da Lona à Toga: notes for working on this repo

Pyodide game (Python simulation in the browser). See README.md for what it is and how it plays.

## Rules that must hold

- **Simulation is pure and deterministic.** `py/lonatoga/sim/` never imports `random` or calls `hash()`; use `rng.stream(seed, t, canal)`.
- **State is a plain JSON dict** and must round-trip through `localStorage` unchanged. New field? Add it to `_estado_base` AND fill it in `migrar()`.
- **The sim returns i18n keys, never text.** Words live only in `py/lonatoga/i18n/pt.py` and `en.py` (same keys in both). Plural suffix `_1`; gender via `{adv}`/`{aprov}`/`{form}` → `g.<m|f>.<name>`. Register keys derived from content in `content.chaves_exigidas()`.
- **New Python file → add it to `MODULOS` in `pyodide-bridge.js`.** `tests/test_web_bundle.py` fails otherwise.
- **No inline text or colours in `app.js`.** Colours are CSS variables (`:root`, `:root[data-theme="bandeira"]`); the scene uses the constant `--art-*` palette. The only text exception is the loading screen in `index.html`.
- **Language and theme are one switch:** Night = dark = English, Modo Bandeira = light = PT-BR. Institution names (Enem, ProUni, Sisu, Fies, OAB, Bolsa Família, Pé-de-Meia, INCRA) stay Portuguese in both.
- JS calls Python only through `py/lonatoga/bridge.py`; errors come back as `{"erro": str}`.

## Test hooks

- `globalThis.__LONATOGA_TESTE__ = true` stops `app.js` from auto-booting; `boot()` returns `{estado, painel, carregar(estado)}`.
- `scripts/dom_test.mjs` plays a full game in jsdom with real Pyodide and scans both languages for leaked keys.
- `tools/make_saves.py` + `scripts/shot.mjs` make screenshots of any game moment.

## Commands

```sh
python3 tools/serve.py                                    # play at http://localhost:8765
uv run --no-project --with pytest python -m pytest -q     # unit + balance tests
node scripts/dom_test.mjs 5                               # UI test (needs npm install)
python3 tools/balance.py 30                               # win rates per bot
```

## Balance

Changing any number in `content.py` or `ano.py` can break `tests/test_balance.py`
(competent bot ≥ 75% wins, idle bot 0%, Sul do Pará harder than Pontal). Re-run
`tools/balance.py 30`, then update the table in README.md.
