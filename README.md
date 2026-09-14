# jhora-to-json

Convert **JHora** (Jagannatha Hora — Vedic astrology / Jyotish software) clipboard output and manual screen entry into one structured **master JSON file per divisional chart (varga)**, enriched with computed Jyotish analytics: argala matrices, dignity/avastha strength scoring, and yoga activation status.

## Pipeline at a Glance

```
JHora app ──(copy to clipboard / manual GUI entry)──┐
                                                    ▼
                              compile_all.py  (MasterCompilerApp, Tk GUI)
                              ┌────────────────────────────────────┐
                              │ Load D1 master JSON + varga prefix  │
                              │ 1. parse_planets → calculate_argala │
                              │ 2. parse_avastha                    │
                              │ 3. parse_aspects  (paste or grid)   │
                              │ 4. parse_yogas                      │
                              │ 5. parse_ashtakavarga (wizard)      │
                              │ 6. parse_arudha (wizard)            │
                              │ → Compile Master JSON               │
                              └────────────────────────────────────┘
                                                    ▼
                                  Master_Merged_{varga}.json
```

## Repository Map

| Path | Role |
|---|---|
| `compile_all.py` | Orchestrator. Tk GUI that runs the 6-step ingestion workflow and writes the merged master JSON. |
| `parse_planets.py` | Clipboard parser → planetary positions, houses, dignities, upachaya flags. |
| `calculate_argala.py` | Computes working argala / virodhargala per house from parsed positions. |
| `parse_avastha.py` | Clipboard parser → avasthas (age / alertness / moods per planet). |
| `parse_yogas.py` | Clipboard parser → yoga table (givers, definition) with 3-pass fallback parsing. |
| `parse_aspects.py` | Aspect-strength ingestion: clipboard paste **or** manual grid GUI. |
| `parse_ashtakavarga.py` | Manual-entry wizard for Bhinnashtakavarga (BAV); derives Samudayashtakavarga (SAV). |
| `parse_arudha.py` | Manual-entry wizard for Arudha padas, Graha arudhas, Varnada lagnas. |
| `AGENTS.md` | Operating manual for LLM agents working in this repository. Start there. |
| `docs/` | LLM-oriented reference: pipeline, module APIs, JSON schemas, domain glossary, invariants/gotchas. |
| `SKILLS/` | Agent behavior skills (`SILENT-EXECUTOR`, `AUDIT`). See `SKILLS/README.md`. |

## Requirements

- Python 3.8+
- `tkinter` (stdlib; on Debian/Ubuntu: `sudo apt install python3-tk`)
- `pyperclip` (`pip install -r requirements.txt`) — required by the clipboard parsers and `compile_all.py`

## Usage

```bash
pip install -r requirements.txt
python compile_all.py
```

Every module also runs standalone and parses whatever is currently in the clipboard:

```bash
python parse_planets.py
python parse_avastha.py
python parse_yogas.py
python calculate_argala.py   # parses clipboard, then computes the argala matrix
python parse_aspects.py      # launches the standalone aspects GUI
```

## Documentation Index (reading order)

1. `AGENTS.md` — entry point for LLM agents
2. `docs/01_overview_and_pipeline.md` — end-to-end data flow
3. `docs/02_module_reference.md` — per-file API reference
4. `docs/03_json_schemas.md` — every JSON shape at every stage
5. `docs/04_domain_glossary.md` — Jyotish domain terms
6. `docs/05_invariants_and_gotchas.md` — behavior contracts and traps (read before editing code)
