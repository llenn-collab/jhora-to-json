# 01 — Overview & Pipeline

## Purpose

`jhora-to-json` turns human-transcribed JHora (Jagannatha Hora) chart data — pasted from the clipboard or typed into small Tk wizards — into one merged, analytics-enriched JSON document per divisional chart (varga). The output is designed to be the machine-readable "chart state" that a downstream LLM analysis pipeline reads.

Two categories of ingestion exist:

- **Clipboard parsers** (pure functions, no GUI): parse JHora table text pasted by the user.
- **Manual-entry wizards** (Tk GUIs): used where JHora's clipboard copy is unreliable or the data is small (ashtakavarga points, arudha house assignments, optional manual aspect matrix).

## End-to-End Flow

```
                         ┌──────────────────────────────┐
                         │ User: JHora app (external)   │
                         │ copies tables to clipboard   │
                         └──────────────┬───────────────┘
                                        │ pyperclip.paste()
                                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ compile_all.py — MasterCompilerApp (Tk GUI)                             │
│                                                                         │
│ Step 0  Load D1 Master JSON (file dialog)  → self.d1_master_data        │
│         Prompt varga prefix (e.g. "D9")    → self.varga_name            │
│                                                                         │
│ Step 1  parse_planets.clean_and_parse_planets(clipboard)                │
│             → {"planetary_positions": [...]}         (positions/houses/ │
│                                                       dignities/upachaya)│
│         calculate_argala.compute_argala_matrix(positions)               │
│             → {"argala_analysis": {house_N: ...}}                       │
│                                                                         │
│ Step 2  parse_avastha.clean_and_parse_avastha(clipboard)                │
│             → {"avasthas": [{body, age, alertness, moods}]}             │
│                                                                         │
│ Step 3  parse_aspects.AspectsApp (Toplevel)                             │
│         mode "paste": clean_and_parse_aspects(clipboard)                │
│         mode "manual": 21×9 grid with relation tagging                  │
│         export_json is monkeypatched → data captured, no file written   │
│             → {"aspect_strengths": {...}}                               │
│                                                                         │
│ Step 4  parse_yogas.clean_and_parse_yogas(clipboard)                    │
│             → {"yogas": {yoga_key: {yoga_givers, definition, active}}}  │
│                                                                         │
│ Step 5  parse_ashtakavarga.AshtakavargaApp (Toplevel wizard)            │
│         8 planets × 12 signs, values 0–8; SAV = column sums (no lagna)  │
│         export_json monkeypatched → captured, no file written           │
│             → {"bhinnashtakavarga": ..., "samudayashtakavarga": ...}    │
│                                                                         │
│ Step 6  parse_arudha.ArudhaApp (Toplevel wizard)                        │
│         3 screens: arudhas, graha_arudhas, varnadas → house 1–12/None   │
│         export_json monkeypatched → captured, no file written           │
│             → {"arudhas": {AL: h, ...}, "graha_arudhas": {...},         │
│                 "varnadas": {...}}                                      │
│                                                                         │
│ Compile Master JSON (unlocks only after steps 1–6 all complete)         │
│  ├─ self-heal D1 planet nesting                                         │
│  ├─ build signs block: house numbers, lords, occupants, special points  │
│  ├─ special-point conjunctions (≤2.0°) THEN longitude truncation        │
│  ├─ attach avasthas, aspects, SAV/BAV                                   │
│  ├─ score each core planet vs a 100 baseline (evaluate_planet_strength) │
│  ├─ classify yogas Active/Dormant/Asleep from giver scores              │
│  ├─ attach effective argala, arudhas, varnadas                          │
│  └─ drop empty {varga}_occupants                                        │
└──────────────────────────────────────┬──────────────────────────────────┘
                                       ▼
                      Master_Merged_{varga}.json (save dialog)
```

## Stage-by-Stage Contract

### Step 0 — D1 Master + varga prefix

- The **D1 master JSON** is a previously compiled (or hand-authored) birth-chart document with top-level `planets` and `signs` objects. It is the merge base: all varga data is added *on top of it* under `{varga}_*`-prefixed keys.
- A top-level `planets` object is self-healed at compile time: if planet nodes sit at the JSON root instead of under `planets`, they are re-nested.
- If the user cancels the varga-prefix prompt, the D1 file stays loaded in memory but the UI remains disabled; the user must click Load again.

### Step 1 — Planets + Argala (single button, two operations)

`clean_and_parse_planets` normalizes JHora's body table:

- Extracts rows by anchoring on the longitude coordinate pattern (`"<deg> <SignAbbr> <min>' <sec>\"`), which survives mangled headers.
- Maps display names to canonical `snake_case` (`NAME_DATABASE["planets"]`, ~30 entries including upagrahas and special lagnas).
- Computes each body's **house** from the lagna's sign, **upachaya flags** for malefics/upagrahas in houses 3/6/10/11 (with generated explanatory text), **special dignity** (exalted / debilitated / degree-based moolatrikona), and **house dignity** via the classical natural-friendship × temporary-friendship compound rule.
- `compute_argala_matrix` then evaluates, for each of the 12 houses, which planets exert **working argala** after virodhargala cancellation (quarter-pair rule: quarters summing to 5 cancel) and Rahu/Ketu reverse counting.

### Step 2 — Avasthas

`clean_and_parse_avastha` pulls every `Sanskrit (English)` pair from each planet row. Fixed positional contract: pair 0 = age (Sanskrit kept), pair 1 = alertness (English kept), pairs 2+ = moods (English kept).

### Step 3 — Aspects

Two mutually exclusive modes:

- **paste**: `clean_and_parse_aspects` keeps only aspect strengths **≥ 64.5%**; values are stored as bare floats.
- **manual**: grid of receivers (9 planets + 12 houses) × 9 casters; each non-empty cell stores `{"strength": float, "relation": string}`.

Both produce the same two top-level buckets: `from_ascendant_to_houses` and `planet_to_planet_aspects`. The sub-app's file export is intercepted; `compile_all.py` captures `app.final_output` instead. (See gotcha G-10 about value-type differences between modes.)

### Step 4 — Yogas

`clean_and_parse_yogas` parses the "Varga Yoga givers" table with a 3-pass strategy: tab-separated → header-anchored fixed-width slicing → regex fallback. Yoga names become `snake_case` keys suffixed `_yoga`; duplicates get `_2`, `_3`, … Each yoga initially carries `active: true`, `yoga_givers`, `definition`; compile-time scoring may downgrade `active` to `false` and adds `status` + `technical_analysis`.

### Step 5 — Ashtakavarga

Manual wizard: one screen per planet (`sun … saturn`, plus `lagna`), 12 sign entries clamped to 0–8. `calculate_sav` sums BAV columns across planets **excluding lagna**. Both BAV (per planet per sign) and SAV (per sign) are captured.

### Step 6 — Arudhas

Manual wizard: three screens (`arudhas` = AL/A2–A12, `graha_arudhas` = one per planet, `varnadas` = V1–V12). Each item gets a house number 1–12 or stays `"None"` (excluded from output).

### Compile — Merge + Analytics

`compile_and_save` builds the final document:

1. **Self-heal** D1 nesting (root-level planet keys → `planets`).
2. **Sign scaffolding**: every sign gets `{varga}_house_number`, `{varga}_house_lord`, `{varga}_occupants` (occupants removed later if empty). House numbering starts from the varga's lagna sign (defaults to `aries` if no lagna row was parsed).
3. **Planet placement merge**: core planets get `{varga}_placement` (longitude, sign, house, dignity, optional special_dignity / upachaya_effect / is_retrograde) deep-merged into the D1 planet node; non-core bodies become `{varga}_special_points` entries on their sign.
4. **Conjunction pass**: special points are checked against all planet and special-point longitudes within **2.0°** (computed on full precision), then all longitudes are truncated (planets → `D° M'`, special points → `D°`).
5. **Avastha attach**: `{varga}_avastha_alertness` always; `{varga}_avastha_age`, `{varga}_avastha_moods` when present.
6. **Aspect attach**: planet receivers → `{varga}_aspects_received` on planet nodes; ascendant→house receivers → same key on sign nodes (sign taken from the key if present, else derived from house number).
7. **Ashtakavarga attach**: `{varga}_sav` (int) and `{varga}_bav` (dict over the 8 tracked bodies) per sign.
8. **Strength scoring**: `evaluate_planet_strength` scores each core planet additively from a 100 baseline (**unclamped** — values above 100 or below 0 are possible) using avastha, dignity, house, dispositor, BAV/SAV, nodal/special-point afflictions, and aspects. Scores exist only in memory.
9. **Yoga activation**: yoga givers are matched by abbreviation (`Su/Mo/Ma/Me/Ju/Ve/Sa/Ra/Ke/Md`, word-boundary regex); the average score of involved planets decides `Active` (≥70) / `Dormant` (≥40) / `Asleep` (<40); each involved planet stores the yoga payload under `{varga}_yogas`.
10. **Argala attach**: `working_argala` per house lands on the corresponding sign as `{varga}_effective_argala`.
11. **Arudha attach**: each arudha/varnada/graha-arudha label is uppercased and appended to the `{varga}_{category}` list of the sign owning its house.
12. **Cleanup**: empty `{varga}_occupants` lists are removed; result written via save dialog as `Master_Merged_{varga}.json`.

## What the Pipeline Deliberately Does *Not* Do

- No geocoding, ephemeris computation, or birth-data handling — JHora is the calculation engine.
- No persistence between runs; each session compiles one varga.
- No per-planet score persistence — scores live only inside yoga `technical_analysis` text.
- No validation that the pasted varga data belongs to the loaded D1 chart (user responsibility).
