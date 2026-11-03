# Da Lona à Toga

*From the black tarp to the gown.*

A browser game about a child born in a landless-workers' camp (a **lona preta**, "black tarp") who goes through school, sits the **Enem**, gets into law school, becomes a lawyer and — if the player does it well — wins the **title deed to the land** for the family.

The simulation is Python running in the browser through [Pyodide](https://pyodide.org). There is no server, no build step and no framework: open it over HTTP and play.

It is a sibling of two other projects: it borrows its look, its two-mode language switch and its content rules from **lona-preta**, and its "pure Python simulation + JSON bridge in Pyodide" architecture from **dindin**.

> **Not a documentary.** The numbers are a game, tuned so that a good player usually wins and a careless one never does. They are inspired by real rules (see [What is real, what is simplified](#what-is-real-what-is-simplified)) but are not a model of any real family, school or exam.

## Run it

Pyodide needs `http://`, so `file://` will not work.

```sh
python3 tools/serve.py          # then open http://localhost:8765
python3 tools/serve.py 9000     # another port
```

The server prints a LAN address too, so you can open the game on a phone. It sends `no-store` headers, so a refresh always picks up edits.

Pyodide itself (about 10 MB) comes from the jsDelivr CDN the first time, so you need internet on first load. After that the browser caches it.

**GitHub Pages:** push the folder as it is. `.nojekyll` is already there; no build is needed.

## The two modes

The language and the theme are one switch (same rule as lona-preta):

| Mode | Look | Language |
|---|---|---|
| **Night** (default) | dark | English |
| **Modo Bandeira** | light, with a green/yellow/blue stripe | Português (Brasil) |

The button in the header toggles both. `?theme=night` or `?theme=bandeira` in the URL forces one. Names of real institutions and programmes (Enem, ProUni, Sisu, Fies, OAB, Bolsa Família, Pé-de-Meia, INCRA) stay in Portuguese in both languages.

Progress autosaves to `localStorage` (`lonatoga-save`); the chosen mode is saved in `lonatoga-theme`.

## How it plays

You pick a region and a name. Four regions change how hard the game is:

| Region | School | Land yields | Owner's strength | Federal university |
|---|---|---|---|---|
| Pontal do Paranapanema (SP) | good (1.05) | average | 72 | in town |
| Sul do Pará (PA) | weak (0.88) | rich | **84** | far away |
| Campanha Gaúcha (RS) | **best (1.10)** | poor | **66** | in town |
| Zona da Mata (PE) | below average (0.95) | below average | 78 | far away |

Sul do Pará is the hardest game; Campanha the gentlest.

### The path

The trail across the top of the screen is the whole game:

1. **Lona** — you are born at the camp (age 6).
2. **1º grau** (fundamental, 9 years) and **2º grau** (médio, 3 years).
3. **Enem** — in the last year of high school you can sit the exam as a **treineiro** (practice run: R$ 85, no fee waiver, score does not count) to learn where you stand, then the real one.
   If you miss the doors you want, you can spend a year in a **cursinho** (prep course) and sit again.
4. **Direito** — law school, 5 years, through whichever door the Enem opened.
5. **OAB** — the bar exam, two phases. Passing phase one is remembered.
6. **Terra** — as a lawyer you take the camp's land case to court.

You win by winning the case. The game ends in a **title deed**, a **defeat** (the family is evicted, or the last appeal is lost), or **time** (age 38 and still not there).

### Each year

Every year you spend **time points** (10, or 8 if your health is below 30; some night courses give extra) on actions: school, study, work the plot (**roça**), an odd job (**bico**, from age 14), community work, and rest. In law school the list becomes classes, study, internship, extension work, odd jobs and rest. Rules that matter:

- **Attendance.** You need at least 3 of 4 points in school to count the year (the 75% rule). Skipping school to work pays now and fails you later.
- **Money.** The family earns, eats, and pays for school and transport. Some income reaches your study fund. **Bolsa Família** and **Pé-de-Meia** (R$ 1,800 a year paid monthly + R$ 1,000 released after the Enem + R$ 200 for sitting it) help; a debt or a bad harvest hurts.
- **Body and mind.** Health, morale and food drift each year and cap how much you can study.
- **Land under threat.** Pressure from the owner grows with eviction events. At the maximum, the owner gets an eviction order.
- **Events.** About 60% of years bring a choice (24 events, e.g. a flooded road, a fever, a donation). Each option has costs and effects; some are only available if you have the money or the standing.
- **Report card.** Each school year ends with a grade and a "passed / failed" verdict compared with the pace the school expects.

### The Enem and the doors

The exam has four objective areas (languages, humanities, science, math) scored 300–1000, and an **essay** of five competências scored 0–200 in steps of 40 (a zero in any is possible). Your result is the average of the five.

When the results come out you choose which **vias** (doors) to apply to. If you qualify for several, the game takes the highest-priority one you picked:

| Order | Via | What it is | Cutoff (this game) |
|---|---|---|---|
| 1 | **Ampla** | open competition, public university | ~850 |
| 2 | **Cota** | quota seat (Lei 12.711) | ~760 |
| 3 | **ProUni** | scholarship at a private university | average ≥ 450, essay ≠ 0; ~690 for a full one |
| 4 | **Fies** | student loan; you graduate owing R$ 14,000 a year | no cutoff |

Cutoffs move ±14 points a year. Miss them and you can try again next year, with all that costs in time and age.

### Law school and the OAB

Five years. You can study, go to class, do an internship (**estágio**, pays R$ 1,000 a year and builds practice) and extension work. Knowledge is tracked in three bars: **Direito** (law), **Prática** (practice) and **Rede** (network). The OAB then asks:

- **Phase 1** (written, law-heavy): roughly `juridico × 0.62 + study × 3.4 + noise ≥ 56`.
- **Phase 2** (practice): `prática × 0.45 + jurídico × 0.28 + study × 1.5 + noise ≥ 41`.

### The case

The last stage is a trial with five steps: **liminar → perícia agrária → sentença → 1ª apelação → última apelação**. Two bars are always visible: **your defence** and **the owner's case**. In each step you pick up to two of five actions:

| Action | Effect |
|---|---|
| Petição fundamentada | builds the defence from your law knowledge |
| Perícia / Vistoria do INCRA | proof the land was idle; costs R$ 400; helps the defence and hurts the owner |
| Mobilização e imprensa | the camp behind you; scales with your **luta** (struggle) |
| Proposta de acordo | weakens the owner's case; needs practice to work |
| Parecer do Ministério Público | the prosecutor on your side; needs network |

Repeating an action helps 30% less each time. The early steps set the stage: winning the **liminar** (injunction) lowers the eviction pressure and lifts morale, losing it gives the owner an eviction; winning the **perícia** strengthens your defence. Win the **sentença** and you have the title. Lose it and you go to the **1ª apelação**, then the **última apelação**; win any of them and the land is yours, lose the last one and the family loses it. Each earlier win adds a little to later steps, and appeals get a small boost.

## Balance

`python3 tools/balance.py 30` plays 120 games per bot (4 regions × 30 seeds):

| Bot | Wins | Notes |
|---|---|---|
| **competente** (sensible plan, good choices) | **83%** | mostly through cota and ProUni; ends around age 27 |
| **mediano** (decent but sloppy) | **55%** | much worse in Sul do Pará than in Pontal |
| **largado** (does nothing) | **0%** | all end by running out of time |

Tests lock these in: competent ≥ 75%, idle 0%, Sul do Pará harder than Pontal, and winners are at least 24 years old.

## What is real, what is simplified

The rules come from the public record of the Enem and its related programmes (MEC, INEP). They are **simplified on purpose** to make a playable game:

| In the game | In reality (approx.) |
|---|---|
| 75% attendance | Lei de Diretrizes e Bases (LDB) requires 75% presence |
| Quota seats (cota) | Lei 12.711/2012, extended by Lei 14.723/2023 (income ceiling of 1 minimum wage per capita for the low-income quota) |
| ProUni scholarship at ≥ 450 and a non-zero essay | Programa Universidade para Todos; minimum score and essay ≠ 0 are real rules; the game does not model full vs partial scholarships or course-by-course cutoffs |
| Fies loan | Fundo de Financiamento Estudantil; the debt figure is a game number |
| Pé-de-Meia | Programa Pé-de-Meia (2024): monthly payments, an annual deposit released at graduation, and an Enem incentive; the amounts here are rounded and simplified |
| Treineiro | Students who have not finished high school can sit as practice; the score is not valid for admission. The R$ 85 fee is a game number |
| Essay with five competências of 0–200 | Real Enem essay format |
| Cutoffs 850 / 760 / 690 | **Invented** for balance. Real cutoffs vary by course, institution and year |
| The land case | A game. Real agrarian cases are far slower and depend on the "função social da terra" (Constituição, arts. 184 and 186) |

I did not manage to fetch the Enem's original design documents (the early-2000s INEP texts by its creators) while researching, so the history here comes from MEC/INEP summaries, not from those primary papers. Treat the rules above as inspired by them, not as a faithful reproduction.

## How it is built

```
index.html            loading screen, #app, #modal
styles.css            all styling; theme tokens as CSS variables
app.js                UI (vanilla JS): renders the screen from the JSON state
pyodide-bridge.js     loads Pyodide, mounts the Python package, calls it
py/lonatoga/
  bridge.py           the only entry point JS calls
  sim/                the simulation (pure, deterministic)
    content.py        every table: stages, regions, events, vias, case steps
    ano.py            a year of life: time, money, learning, health
    enem.py           the exam, cutoffs, which via you get
    caso.py           the court case
    engine.py         new game, year loop, events, transitions, save migration
    rng.py            seeded randomness
  i18n/               pt.py, en.py, and the key registry
tools/                serve.py, balance.py, make_saves.py
tests/                pytest
scripts/              dom_test.mjs (full game in jsdom), shot.mjs (screenshots)
```

The rules the code follows:

- **The simulation is pure and deterministic.** Randomness comes from `rng.stream(seed, year, channel)` (blake2b), never from `hash()` or the global `random`. Same save and same choices give the same game.
- **The state is a plain JSON dict.** It round-trips unchanged through `localStorage`. `migrar()` fills fields missing from older saves.
- **The simulation returns i18n *keys*, never text.** All words live in `i18n/pt.py` and `i18n/en.py`; `app.js` turns keys into text, escapes it, and resolves gender placeholders (`{adv}`, `{aprov}`, `{form}`). A test checks both dictionaries have the same keys and that everything the content refers to exists.
- **Python files are listed in `MODULOS`** (`pyodide-bridge.js`). Add a Python file and you must add it there; a test fails otherwise.
- **No colours or text in the JS.** Colours come from CSS variables, with a constant `--art-*` palette for the scene.

## Tests

```sh
uv run --no-project --with pytest python -m pytest -q     # 69 tests: sim, i18n, balance, bundle
npm install                                                # once, for the UI tests
node scripts/dom_test.mjs 5                                # a full game through the UI, both languages
```

`dom_test.mjs` loads the real Pyodide inside jsdom, plays a game to the end, and at every step scans both languages for leaked text keys, `undefined`, `NaN` and unescaped player names.

Screenshots in headless Chrome (needs internet for Pyodide):

```sh
python3 tools/make_saves.py /tmp/saves          # states at key moments
node scripts/shot.mjs bandeira out.png /tmp/saves/caso.json 1100 1500
```

## Credits and context

Inspired by the real history of the Enem (created by INEP/MEC in 1998 and reshaped in 2009 into the national admission exam used by Sisu and ProUni) and by the long Brazilian fight over land and access to education. The land movement in the game is fictional and not meant to represent any real organisation.
