# AGENTS.md — Operating Manual for LLM Agents

This file is the entry point for any LLM agent (coding assistant, autonomous agent, refactorer) working in this repository. Read it fully before touching code.

## 1. What This Repository Is

A Python desktop toolkit that converts **JHora** (Jagannatha Hora, a Vedic-astrology application) clipboard output and manual GUI entry into a single merged **master JSON** per divisional chart (varga). The final JSON is consumed downstream by LLM-based Jyotish analysis; every key in it is load-bearing.

- **Entry point:** `compile_all.py` (Tk GUI orchestrator, class `MasterCompilerApp`).
- **Libraries:** the seven `parse_*.py` / `calculate_*.py` files. Each is imported by `compile_all.py` **and** runs standalone via `python <file>.py` (reads the clipboard, prints JSON).
- **External dependency:** `pyperclip` only. `tkinter` is stdlib.
- **No test suite, no CI.** The GUI is the only integration harness.

## 2. Mandatory Reading Order

| # | File | Purpose |
|---|---|---|
| 1 | `docs/01_overview_and_pipeline.md` | End-to-end data flow, step by step |
| 2 | `docs/02_module_reference.md` | Exact functions, classes, signatures, side effects per file |
| 3 | `docs/03_json_schemas.md` | Every JSON shape at every pipeline stage, key by key |
| 4 | `docs/04_domain_glossary.md` | Jyotish (Vedic astrology) domain vocabulary |
| 5 | `docs/05_invariants_and_gotchas.md` | Behavioral contracts, magic numbers, traps. **Read before any edit.** |
| 6 | `docs/06_audit_and_upgrade_todo.md` | Full code audit (2026-09-14) + the master to-do list for all future upgrades. Cite finding IDs (`F-xx`) in commits. |

If a question is answered in `docs/05_invariants_and_gotchas.md`, trust that answer over intuition.

## 3. Canonical Conventions (used everywhere, do not rename)

- Planet names: lowercase `sun, moon, mars, mercury, jupiter, venus, saturn, rahu, ketu` (plus `lagna` and upagraha/special-point names in `snake_case`).
- Sign names: lowercase `aries … pisces`, always in `ZODIAC_ORDER` (standard sign order, defined in `parse_planets.py` and duplicated in `compile_all.py` and `parse_ashtakavarga.py` as `ZODIAC`).
- All JSON keys: `snake_case`. Varga-specific keys are prefixed with the user-supplied varga token (e.g. `D9_placement`, `D9_sav`).
- The 9 "core planets" set is `{sun, moon, mars, mercury, jupiter, venus, saturn, rahu, ketu}` (defined independently in `parse_planets.py` as `core_planet_keys`, `calculate_argala.py` as `CORE_PLANETS`, and `compile_all.py` as `CORE_PLANET_NAMES`). Other deliberate doctrine duplication: `BENEFIC_CASTERS` / `MALEFIC_CASTERS` / `GIVER_MAP` and the scoring thresholds in `compile_all.py`; `MALEFICS` and `QUARTER_*` bounds in `calculate_argala.py`; the 5-planet upachaya-malefic list in `parse_planets.py`. None of these are deduplicated (rule 1).
- Sign→lord mapping `RASI_LORDS` is duplicated in `parse_planets.py` and `compile_all.py`.

## 4. Hard Rules for Code Changes

1. **Keep every module standalone-runnable.** Duplication of `ZODIAC_ORDER`, `RASI_LORDS`, and `NAME_DATABASE` across files is deliberate so each file works alone. Do not "deduplicate" into a shared module unless the task explicitly says so.
2. **Do not change output JSON shapes.** Downstream consumers depend on exact keys (`{varga}_placement`, `{varga}_sav`, `working_argala`, `"_receives_aspects"` suffixes, `"XH"` house keys, etc.). See `docs/03_json_schemas.md`.
3. **Do not reorder the compile-time math.** Special-point conjunction detection (2° orb) runs **before** longitude truncation. Reversing this breaks conjunctions.
4. **Preserve the `export_json` monkeypatch contract.** `compile_all.py` replaces `export_json` on sub-app instances to capture data instead of writing files. Internal call paths must keep resolving `export_json` dynamically through `self`. See gotcha G-08.
5. **Keep the `try/except ImportError` import guards** in `compile_all.py` and `calculate_argala.py`. They let the orchestrator degrade gracefully when a module is missing.
6. **Parsing is defensive by design.** Clipboard text is mangled by JHora (null bytes, mixed tabs/fixed-width columns, truncated headers). The multi-pass fallbacks in `parse_yogas.py` and the coordinate-anchored regex in `parse_planets.py` exist for real failure modes. Do not simplify them without test data.
7. **Tk GUI quirks are intentional:** always-on-top + `focus_force()` (wizard-style UX), value clamping to `0–8` in ashtakavarga, disabled step buttons that unlock only after all 6 steps complete.
8. **No code comments may be removed** where they record a *reason* (e.g. "Fix: Now sums the length of the planets arrays", "Lagna BAV is tracked but strictly excluded from SAV sum") — they are the only surviving rationale for non-obvious behavior.

## 5. Things That Do Not Exist (do not assume them)

- No CLI batch mode for the master compile — `compile_all.py` is GUI-only.
- No clipboard parser for ashtakavarga or arudha data — those are manual-entry wizards by design.
- No persistence/database. In the master flow, I/O is: clipboard reads, one JSON read (D1 master), one JSON write (merged output). Run standalone, the sub-apps additionally save their own JSON via file dialogs.
- No tests, no linting config, no packaging metadata.
- `SKILLS/` contains agent-behavior markdown skills, not code. Nothing imports them.

## 6. Quick Facts for Orienting

- Workflow order in the GUI is fixed: Load D1 → enter varga prefix → 6 steps → Compile. Steps complete in any order, but the Compile button unlocks only when **all 6** are marked done.
- The D1 master JSON supplies the baseline `planets` and `signs` objects; the compile deep-merges `{varga}_*` keys into them.
- Strength scores (additive around a 100 baseline, **unclamped** — values above 100 or below 0 are possible) are computed at compile time to classify yogas (Active/Dormant/Asleep) and are **not** persisted per planet — only inside yoga `technical_analysis` strings.
- Output file default name: `Master_Merged_{varga}.json`.

## 7. If You Must Modify Parsing Behavior

1. Capture a real JHora clipboard sample for the affected table first; every regex is fitted to real JHora text.
2. Re-read gotchas G-01 through G-14 in `docs/05_invariants_and_gotchas.md`.
3. Keep the null-byte stripping (`raw_text.replace('\x00', '')`) at the top of every clipboard parser.
4. Keep header-row skipping (`line.startswith("Body")`, `"Longitude" in line`, `"Alertness" in line`, `"Aspected Body"`, `"Varga Yoga givers"`, `"---"`) — JHora emits mangled headers.
