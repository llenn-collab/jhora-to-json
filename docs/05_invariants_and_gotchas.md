# 05 — Invariants & Gotchas (Read Before Editing)

Behavioral contracts and traps, each verified against the code. IDs (G-01…) are referenced from `AGENTS.md`.

## Data-Flow Invariants

**G-01 — Conjunction math must run before longitude truncation.**
In `compile_and_save`, special-point conjunctions (orb ≤ 2.0°, inclusive) are computed from full `D° M' S"` precision. Only afterwards are longitudes truncated (planets → `D° M'`, special points → `D°`). Reordering silently destroys every conjunction within the truncated digits. Note the orb is checked against special points↔planets **and** special points↔special points, but never planet↔planet.

**G-02 — Score order matters for yoga classification.**
`evaluate_planet_strength` runs for all 9 core planets *before* the yoga loop; yogas average pre-computed scores. The 100-point baseline applies to planets with no placement or no data (`return 100, ""`), so missing planets inflate yoga scores rather than erroring.

**G-03 — Planet strength scores are never persisted.**
The numeric score exists only inside yoga `technical_analysis` strings. If downstream analysis needs per-planet scores, that is a schema addition, not a retrieval.

**G-04 — Empty occupant lists are removed, other empties are not.**
At the end of compile, `{V}_occupants` is deleted when empty, but e.g. `{V}_bav` (zeros), `{V}_sav`, `{V}_house_number`, `{V}_house_lord` always remain. Consumers must treat "no occupants key" as "empty house".

**G-05 — House↔sign mapping has two independent paths.**
Sign nodes get their house from the *lagna of the parsed varga* (falls back to `aries` when no lagna row was parsed). Argala and arudha/varnada data map house→sign via `get_sign_for_house`, the same lagna anchor. Ascendant-aspect paste-mode keys (`house_N_{sign}`) carry their own sign; manual-mode keys (`house_N`) use the derived one. If the pasted varga chart and the D1 master disagree about the lagna, signs will contain mixed-provenance data with no error.

**G-06 — `deep_merge` overwrites non-dict values.**
`{V}_placement` merges into existing planet nodes recursively, but any scalar/list collision is silently replaced by the varga value. D1 keys with the same name as a varga key would be overwritten (they don't collide today because varga keys are prefixed).

## Parser Traps

**G-07 — All clipboard parsers strip `\x00` and skip header rows.** JHora paste text contains null bytes and mangled/truncated headers. Removing `raw_text.replace('\x00', '')` or a header skip re-introduces real-world failures. `parse_planets` also tolerates trailing body-cell suffixes (`- Su`, `(R)`).

**G-08 — The `export_json` monkeypatch is load-bearing.**
`compile_all.py` sets `app.export_json = hijacked_export` on `AspectsApp`, `AshtakavargaApp`, and `ArudhaApp` instances so data is captured instead of written to disk. This only works because every internal call path reaches `export_json` via `self.export_json()` (dynamic attribute lookup at call time). If any sub-app ever binds `export_json` into a widget callback **created before the patch is applied** and calls it directly, that path would open a save dialog and break the master flow. Current safe paths: `do_paste → self.export_json()`, `next_screen → self.export_json()`, `compile_manual_data` hook, and the ashtakavarga Next button (`command=self.next_screen` → dynamic lookup). Keep it that way.

**G-09 — Three-pass yoga parsing is order-sensitive.**
Tab pass → header-anchored fixed-width slicing → regex fallback. The header line must be seen before the fixed-width pass activates (`header_bounds['varga'] > 0` required). The `Naabhasa yoga - throughout life` special case exists because that row lacks double-space column separation. Duplicate yoga keys are suffixed `_2`, `_3`, … — do not deduplicate or rename.

**G-10 — Aspect value types differ between modes (latent incompatibility).**
Paste mode stores **bare floats**; manual mode stores **`{"strength": float, "relation": str}` objects**. `compile_and_save`'s scoring reads `data.get("strength", 0)` — that call **raises `AttributeError` on paste-mode floats**. The pipeline is effectively manual-mode-first; paste-mode aspect data reaching compile is a crash path, not a graceful fallback. Known quirk, preserved as-is until the owner decides the target schema.

**G-11 — Aspect thresholds are magic numbers with different roles.**
`64.5` (parser retention cutoff, paste mode), `60` (scoring threshold in compile), `2.0` (conjunction orb, degrees), `70/40` (yoga Active/Dormant/Asleep), `5/2` (BAV high/low), `30/25` (SAV high/low), quarter-sum `= 5` (argala cancellation). None are configurable; changing one changes doctrine.

**G-12 — Avastha record fields are positional.**
Pair 0 = age (Sanskrit), pair 1 = alertness (English), pairs 2+ = moods (English). Rows with <2 pairs are silently dropped. The alertness scoring keywords are matched as substrings (`"jaagrita"/"awake"`, `"swapna"/"dreaming"`, `"sushupta"/"asleep"`), so capitalization doesn't matter but spelling does.

## Structural Conventions

**G-13 — Cross-module duplication is deliberate.**
`ZODIAC_ORDER`/`ZODIAC`, `RASI_LORDS`, `NAME_DATABASE` (with *different* mapping directions: `parse_yogas` maps full name → abbreviation, others map → snake_case), and the core-planet list are re-declared per module so every file runs standalone. `compile_all` guards every import with `try/except ImportError` and degrades per-step. Don't consolidate without an explicit mandate.

**G-14 — GUI completion gating is all-or-nothing.**
Compile unlocks only when all 6 step buttons are disabled-with-✓ (`mark_complete`). Completed steps cannot be re-run in the same session (button is disabled); a mistake means restarting the app. Step completion only proves the parser did not raise — an empty or malformed clipboard still marks the step done and compiles (lagna falls back to `aries`). `AshtakavargaApp` clamps entries to integers 0–8; lagna's BAV is captured but excluded from SAV.

**G-15 — D1 self-healing re-nesting.**
At compile, if core planet names appear as top-level keys of the D1 master, they are *moved* (`.pop`) under `planets`. This mutates the in-memory D1 copy only; the source file is untouched.

**G-16 — Varga prefix is free-form user text.**
Whatever string is entered at load time (`D9`, `Navamsa`, anything) is interpolated into every key (`{V}_placement`…). Empty input aborts loading (buttons stay disabled, D1 stays in memory). There is no validation/whitelisting.

**G-17 — Cancelling the varga prompt leaves a half-loaded state.**
`load_d1_profile` loads the JSON, then asks for the prefix; cancelling returns before enabling buttons or updating the label, leaving `d1_master_data` set but the UI unusable until Load is clicked again.

**G-18 — Success/errors share one modal.**
`show_error` displays both failures and the final success message. Its window is always-on-top like the main window.

**G-19 — Unmatched yogas are silently dropped.**
The compile loop attaches a yoga to planets only when at least one parsed giver abbreviation maps to a name that exists in `final_payload["planets"]`. Matching considers the 9 core planets only — e.g. a yoga whose sole giver is `Md` (maandi) can never attach, because maandi is stored as a special point, never a planet node. Such yogas stay in the raw parsed data but never reach `Master_Merged_*.json`, with no warning.

## GUI / Environment Notes (for automation)

- All windows force themselves topmost and steal focus (`attributes('-topmost', True)` then unset, `focus_force()`) — wizard-style UX by design.
- `compile_all.py` requires `pyperclip`; the CLI parsers print to stdout and are scriptable (seed the clipboard, run, parse stdout).
- `parse_aspects.py`, `parse_ashtakavarga.py`, `parse_arudha.py` have no pure-function CLI path for their wizard data (aspect *paste* parsing is importable as `clean_and_parse_aspects`).
- `parse_planets.py`'s `check_moolatrikona` windows use exclusive lower bounds for moon (`3.0001`) and mercury (`15.0001`) and inclusive upper bounds. Because the exaltation check runs first in `clean_and_parse_planets`, a degree covered by both windows classifies as exalted, not MT. The MT test degree is parsed from the longitude **with seconds required**; when seconds are missing the degree defaults to `0.0`.

## Conventions Bound by This Repo (school-specific choices)

- Rahu exalted/taurus, debilitated/scorpio; ketu mirrored. (Other schools invert this — here it is fixed.)
- Whole-sign houses only; no bhava-chalit.
- Upachaya houses: 3, 6, 10, 11. Dusthana: 6, 8, 12.
- Argala counting includes the quarter-precision cancellation rule and Rahu/Ketu reverse counting (`eff_rel = 14 − fwd_rel`); Ketu's special vidya-axis role (Ketu in the effective 9th *gives* vidya argala; Ketu in the effective 5th *blocks* it) is encoded in the 5/9 swap.
