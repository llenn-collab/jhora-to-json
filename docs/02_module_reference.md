# 02 — Module Reference

Reference for every Python file. Signatures, constants, return shapes, and side effects are quoted exactly. JSON shapes are detailed in `03_json_schemas.md`.

---

## `parse_planets.py` — Clipboard parser: planetary positions

**Imports:** `re`, `json`, `pyperclip`.

**Module constants**

| Constant | Content |
|---|---|
| `NAME_DATABASE["planets"]` | ~30 display-name → snake_case mappings: 9 planets, `Lagna`, upagrahas (`Maandi`/`Md`, `Gulika`/`Gk`, `Dhooma`, `Vyatipata`, `Parivesha`, `Indra Chapa`, `Upaketu`, `Kaala`, `Mrityu`, `Artha Prahara`, `Yama Ghantaka`), special lagnas (`Bhava/Hora/Ghati Lagna`, `HL`, `GL`, `SL`, `PrL`), `Bhrigu Bindu`. Unknown names fall back to `lower().replace(" ", "_")`. |
| `NAME_DATABASE["rasis"]` | 2-letter abbreviations (`Ar`, `Ta`, … `Pi`) → lowercase sign names. |
| `ZODIAC_ORDER` | `["aries", …, "pisces"]` — the canonical sign ordering. |
| `RASI_LORDS` | sign → lord (lowercase planet name). |
| `NATURAL_FRIENDSHIP` | per planet: `friends`, `enemies`, `neutral` lists. Covers the 7 true planets only (no rahu/ketu). |
| `DIGNITIES` | per planet: `exalted` sign, `debilitated` sign. Includes rahu (taurus/scorpio) and ketu (scorpio/taurus). |

**Functions**

- `check_moolatrikona(planet, rasi, degree) -> bool` — degree-window test. Windows (sign, start°, end°): sun leo 0–20, moon taurus 3.0001–20, mars aries 0–12, mercury virgo 15.0001–20, jupiter sagittarius 0–10, venus libra 0–15, saturn aquarius 0–20. Inclusive bounds.
- `reformat_longitude(long_str) -> str` — `"13 Vi 14' 5.3\""` → `"13° 14' 5.3\""` (the sign abbreviation is stripped from the longitude string; the sign lives in the `rasi` field).
- `clean_and_parse_planets(raw_text) -> {"planetary_positions": [record, …]}` — the main parser.

**Parsing algorithm**

1. Strip `\x00` bytes; split lines; skip empty lines and headers (`Body…`, any line containing `Longitude`).
2. Split each line on the coordinate regex `(\d+\s+[A-Za-z]{2}\s+\d+'\s+\d+(?:\.\d+)?\")` — the coordinate block is the anchor; anything before it is the body cell.
3. From the body cell: detect `(R)` → `is_retrograde: true`; strip trailing `- XX` suffix and `(R)`; map through `NAME_DATABASE["planets"]`.
4. From the coordinate: extract sign abbreviation → `rasi`; reformat longitude to `"D° M' S\""`.
5. If a `lagna` record exists with a valid sign: for every record compute `house = (rasi_idx - lagna_idx) % 12 + 1`; set `house_lord` for core planets + lagna; apply the **upachaya engine** — malefic planets / upagrahas in houses 3, 6, 10, 11 get an `upachaya_effect` prose string (entity type "malefic planet" vs "upagraha" chosen by membership).
6. For core planets only: determine `special_dignity` (`exalted` / `debilitated` / `moolatrikona`, checked in that order) and `house_dignity` — `own_house` if sign lord is self, otherwise compound natural + temporary friendship: temporary friend when `(lord_house - my_house) % 12 + 1 ∈ {2,3,4,10,11,12}`; natural value +1/0/−1, temporary ±1; sum `2 → good_friend_house`, `1 → friend_house`, `0 → neutral_house`, `−1 → enemy_house`, `−2 → worst_enemy_house`. Rahu/Ketu never receive `house_dignity` (not in `NATURAL_FRIENDSHIP`).

**Record shape (per body):** `body`, `longitude`, `rasi`, optional `is_retrograde`, and (when lagna present) `house`; core planets additionally `house_lord`, optional `special_dignity`, `house_dignity`, `upachaya_effect`.

**`__main__`:** reads clipboard, prints the JSON (or `[!] Clipboard is empty…`).

---

## `calculate_argala.py` — Argala (intervention) matrix

**Imports:** `json`, `re`, `pyperclip`; optional `clean_and_parse_planets` (guarded with `try/except ImportError`).

**Constants:** `CORE_PLANETS` (9 planets), `MALEFICS = {sun, mars, saturn, rahu, ketu}`.

**Functions**

- `get_quarter(longitude_str) -> int` — parses `"D° M' S.""` and returns the sign quarter 1–4 (0–7.5°, 7.5–15°, 15–22.5°, 22.5–30°). Returns 1 on parse failure.
- `compute_argala_matrix(planetary_data) -> {"argala_analysis": {…}}` — input is the *output of `clean_and_parse_planets`*.

**Algorithm per target house (1–12):**

1. Occupancy map: core planets with a house → `{quarter, is_malefic, longitude}` per house.
2. `is_reverse = rahu or ketu occupies the target house`. If reverse, every source house relationship is inverted: `eff_rel = 14 − fwd_rel` (so 2nd becomes 12th, 5th becomes 9th, 11th becomes 3rd, …); conjunction (rel 1) unchanged.
3. Axis resolution with cancellation — an argala is **blocked** when some virodhargala planet's quarter sums with the argala planet's quarter to exactly 5 (1↔4, 2↔3):

| Argala type | Argala source (eff. rel) | Virodhargala (eff. rel) |
|---|---|---|
| `dhana` | 2nd | 12th |
| `subha` | 4th | 10th |
| `vidya` | 5th (non-ketu) + 9th (ketu only) | 9th (non-ketu) + 5th (ketu only) |
| `labha` | 11th | benefics in 3rd |
| `vipreet_argala` | malefics in 3rd, **only if ≥ 3 malefics** | — |
| `3rd_house_special` | 1–2 malefics in 3rd | — |

4. Survivors are grouped by **source house** into `{"{src}H": {"planets": [names], "type": label}}`; `label` gets `" (reverse)"` appended when `is_reverse`. Duplicates prevented.
5. Strength by count of surviving argala planets: 0 → `none`, 1 → `limited`, 2 → `medium`, ≥3 → `excellent`.

**Output per house:** `{"house_N": {"is_reverse_counted": bool, "working_argala": {…}, "argala_strength_by_count": str}}`.

**`__main__`:** clipboard → `clean_and_parse_planets` → matrix → print.

---

## `parse_avastha.py` — Clipboard parser: avasthas

**Constants:** `NAME_DATABASE["planets"]` — the 9 planets only (avastha table covers just these).

**`clean_and_parse_avastha(raw_text) -> {"avasthas": [record, …]}`**

1. Strip `\x00`; skip empty/header lines (`Planet…`, any line containing `Alertness`).
2. Base planet name = leading `[A-Za-z]+` of the line, mapped via DB (fallback lowercase).
3. Extract all `Word (Parenthesized)` pairs via regex. **Positional contract:** pair 0 → `age` (Sanskrit word kept as-is); pair 1 → `alertness` (English from parentheses); pairs 2+ → `moods` list (English). Lines with fewer than 2 pairs are skipped.
4. Record: `{"body", "age", "alertness", "moods"}`.

**`__main__`:** clipboard → parse → print.

---

## `parse_yogas.py` — Clipboard parser: yoga givers table

**Constants:** `NAME_DATABASE["planets"]` maps full names to JHora abbreviations (`Sun → Su`, `Moon → Mo`, … `Ketu → Ke`) — note this direction is the reverse of the other modules.

**Functions**

- `format_yoga_key(raw_name) -> str` — `"Yogada (HL)"` → `"yogada_hl_yoga"`; strips `()`, collapses whitespace/`/`/`-` to `_`, lowercases, appends `_yoga` if missing.
- `clean_and_parse_yogas(raw_text) -> {"yogas": {key: record}}`

**Three-pass parsing** (per line, after null-byte strip and header skip):

1. **Tab pass** — if the line contains tabs and ≥4 non-empty columns: `name=givers=results` from columns 0/2/3.
2. **Fixed-width pass** — when the header line (containing `Yoga`, `Varga`, `Yoga givers`) was seen, its column offsets (`varga`, `givers`, `results`, `def`) are recorded and used to slice every subsequent line (padded against overrun). This ignores whatever the `Varga` column contains.
3. **Regex pass** — anchors on the varga column pattern (`Rasi` or `D-\d+` possibly with `(…)` and `x D-…`), then splits the remainder on 2+ spaces. Special-cases the `Naabhasa yoga - throughout life` prefix that lacks double spacing. Final fallback: 2+ space split requiring ≥4 columns.

**Record:** `{"active": True, "yoga_givers": str, "definition": str}`. Duplicate keys get numeric suffixes (`_2`, `_3`, …).

**`__main__`:** clipboard → parse → print.

---

## `parse_aspects.py` — Aspect strengths (parser + GUI)

**Constants:** `NAME_DATABASE` (9 planets; 12 rasis), `ASPECTING_COLUMNS` (9 casters), `RECEIVERS` (9 planets + `house_1`…`house_12`), `CASTERS` (9), `RELATIONS` (`neutral, enemy, friend, worst_enemy, good_friend, own_house`), `COLORS`, `FONTS`.

**`clean_and_parse_aspects(raw_text) -> {"aspect_strengths": {"from_ascendant_to_houses": {…}, "planet_to_planet_aspects": {…}}}`**

- Row regex: `<row name> <longitude> <aspect values…>`. Longitude anchored like `parse_planets`.
- Values are matched positionally against `ASPECTING_COLUMNS`; `-` means no aspect; `%` stripped; **only strengths ≥ 64.5 are kept**; values stored as **bare floats** keyed by caster.
- Row routing: `lagna`/`N from lagna` rows → `from_ascendant_to_houses["house_N_{sign}"]`; planet rows → `planet_to_planet_aspects["{planet}_receives_aspects"]`.

**`class AspectsApp(root)`** — Tk Toplevel app, two modes:

- **Paste mode** (`do_paste`): clipboard → `clean_and_parse_aspects` → `self.final_output` → `self.export_json()`.
- **Manual mode** (`show_manual`): scrollable 21-row × 9-column grid. Typing a strength and pressing Enter pops a relation-choice menu (`popup_relation` → `set_relation`, turning the cell text green). `compile_manual_data` builds the same output shape but each cell is `{"strength": float, "relation": str}`.
- `export_json()`: (manual mode re-compiles first) then file-dialog save — **normally monkeypatched away when run under `compile_all.py`**.
- Mouse-wheel scrolling is bound recursively (`bind_scroll_recursive`, `on_mousewheel`) to support macOS trackpads and Linux Button-4/5.

**`__main__`:** standalone `AspectsApp` in a `tk.Tk` root.

---

## `parse_ashtakavarga.py` — BAV/SAV manual-entry wizard

**Constants:** `PLANETS = [sun, moon, mars, mercury, jupiter, venus, saturn, lagna]` (8 — includes lagna), `ZODIAC` (12 signs), `COLORS`, `FONTS`.

**`class AshtakavargaApp(root)`** — sequential wizard:

- State: `current_idx` (0–8), `bav_data = {planet: {sign: 0}}` for all 8 bodies, one `StringVar` per sign row.
- `enforce_limits` (trace on every var): digits only, clamped to ≤ 8.
- `on_enter`: Enter moves focus down; on the last row it advances the screen.
- `save_current_data` / `load_screen`: sync `StringVar`s ↔ `bav_data` per planet screen.
- `calculate_sav() -> {sign: int}`: column sums over all planets **excluding lagna** (explicit code comment: lagna BAV tracked but excluded from SAV).
- Screen 9 (index 8) = SAV preview; button becomes "Export JSON" → `export_json()` writes `{"bhinnashtakavarga": bav_data, "samudayashtakavarga": sav}` after a file dialog (monkeypatched away under `compile_all.py`).

**`__main__`:** standalone wizard.

---

## `parse_arudha.py` — Arudha/varnada manual-entry wizard

**Constants:** `SCREENS` (3 screens: `arudhas` = `AL, A2…A12`; `graha_arudhas` = 9 planet names; `varnadas` = `V1…V12`), `HOUSE_OPTIONS = ["None", "1"…"12"]`, `COLORS`, `FONTS`.

**`class ArudhaApp(root)`** — 3-screen wizard:

- One `StringVar` (default `"None"`) per item, pre-created for all screens; values persist across Back/Next.
- `skip_screen`: resets the current screen's vars to `"None"`, then advances.
- Last screen's Next becomes "Export JSON"; Skip button hidden.
- `export_json`: builds `{screen_id: {item: int(house)}}`, omitting `"None"` entries and empty screens, then file-dialog save (monkeypatched away under `compile_all.py`).

**`__main__`:** standalone wizard.

---

## `compile_all.py` — Orchestrator GUI

**Imports:** `tkinter`, `messagebox`, `filedialog`, `pyperclip`, `json`, `os`, `re`, `copy`; all seven pipeline modules under `try/except ImportError` guards (missing module ⇒ its GUI step shows "module missing" instead of crashing the app).

**Constants:** `COLORS` (dark slate theme), `ZODIAC_ORDER`, `RASI_LORDS` (duplicates of `parse_planets` versions).

**`deep_merge(dict1, dict2) -> dict1`** — recursive dict merge; nested dicts merge recursively, everything else (lists, scalars) is overwritten.

**`class MasterCompilerApp(root)`** — fixed-window (500×750) always-on-top GUI:

- State: `d1_master_data` (loaded JSON), `varga_name` (prefix string), `raw_parsed_data` (dict with 7 buckets: `planets, argala, avasthas, aspects, yogas, ashtakavarga, arudhas`).
- `steps`: the 6 buttons — planets(+argala), avasthas, aspects UI, yogas, ashtakavarga UI, arudha UI. Each disables itself on completion via `mark_complete` (appends `✓`); the Compile button unlocks only when **all six** are done.
- `load_d1_profile`: file dialog → JSON load → `simpledialog` varga prefix → enables step buttons. Cancel at the prefix prompt aborts (buttons stay disabled).
- Ingestion methods (`ingest_planets`, `ingest_avasthas`, `ingest_yogas`) read the clipboard and fill `raw_parsed_data`; UI-launchers (`launch_aspects_ui`, `launch_bav_ui`, `launch_arudha_ui`) build a `Toplevel`, instantiate the sub-app, and **replace its `export_json` with a closure** that copies results into `raw_parsed_data` and closes the window.
- `compile_and_save`: the full merge/analytics pass (see `01_overview_and_pipeline.md`) and the nested helpers `get_sign_for_house(house_num)` and `evaluate_planet_strength(p_name) -> (score:int, reasons:str)`.
- `show_error(msg)`: reusable modal notice (also used for the success message).

**`evaluate_planet_strength` scoring table** (base 100; reasons string like `"[Awake (+10), …]"`):

| Factor | Condition | Δ |
|---|---|---|
| Avastha alertness | jaagrita/awake · swapna/dreaming · sushupta/asleep | +10 · −20 · −40 |
| Special dignity | exalted or moolatrikona · debilitated | +20 · −40 |
| House dignity | own_house · good_friend/friend_house · worst_enemy/enemy_house | +10 · +5 · −20 |
| House | 1,4,5,7,9,10 · 6,8,12 · 6 with upachaya_effect · 3,11 with upachaya_effect | +10 · −30 · +15 · +15 |
| Dispositor | exalted/MT/own_house · debilitated · in 6/8/12 without upachaya_effect | +10 · −20 · −10 |
| BAV (sign) | ≥5 · ≤2 | +10 · −10 |
| SAV (sign) | ≥30 · <25 | +10 · −10 |
| Rahu/Ketu co-occupant | node has upachaya_effect · otherwise | +10 · −20 |
| Special point conjunct | SP has upachaya_effect · otherwise | +10 · −20 |
| Aspect received (strength ≥60) | benefic caster (ju/ve/me/mo) · malefic caster (sa/ma/ra/ke) · malefic caster with upachaya_effect | +15 · −15 · +5 |

Missing planet / missing placement ⇒ neutral `(100, "")`. The sun is in neither benefic nor malefic aspect lists ⇒ its aspects score nothing.

**`__main__`:** `tk.Tk()` + `MasterCompilerApp` + `mainloop`.
