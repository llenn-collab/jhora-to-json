# 06 — Code Audit & Upgrade To-Do List

**Date:** 2026-09-14 (audit, 2026-09-14 18:22 UTC) / 2026-09-15 (Milestones A–D), user-local IST · **Auditor:** LLM agent (Arena) · **Branch base:** `739b928`

This document is the result of a deep, end-to-end audit of every Python module, the
orchestrator, and the documentation. It is the single reference for all future upgrades.
Each finding has a stable ID (`F-xx`) that should be cited in commits and PRs.

## 0. Scope, Method, and Hard Constraints

**Method.** Every pure function was executed against realistic synthetic JHora clipboard
tables (null bytes, mangled headers, `(R)` markers, trailing `- XX` suffixes, all three
yoga parse passes, both aspect modes, all argala axes, the full `compile_and_save` merge
with D1 self-heal, conjunction math, scoring, yoga classification, arudha/argala attach,
and cleanup). The headless verification suite is **`tests/audit_smoke.py`** (in-repo, adopted
per TODO-15; the workspace-root audit-time original `jhora-audit-harness.py` is
retained as an untracked artifact pointer). 560 lines, 126 assertions, 0 failures
at the 2026-09-15 re-verification (it stubs `tkinter` so `compile_all.py` runs
without a display; CI runs the same suite — `.github/workflows/ci.yml`). GUI-interaction behavior (dialogs, focus, buttons) was audited
by code reading only — every such claim below is explicitly marked as such.

**Hard constraints honored by this audit (do NOT "fix" these):**

1. **JHora paste formats are a frozen contract.** The user's manual/auto copy-paste flow
   and the exact JHora clipboard text the parsers accept are *perfected* — no parser may
   change what it accepts or how it interprets the text. Upgrades must be strictly
   *additive* (tolerance for equivalent manual re-entry, pre-parse validation, capture-time
   normalization) and must keep the paste parsers' output byte-identical for real JHora text.
2. **Output JSON shapes are frozen** (see `03_json_schemas.md`).
3. **Compile-time math order is frozen** — conjunction (2.0°) before longitude truncation (G-01).
4. **`export_json` monkeypatch contract is frozen** (G-08).
5. **Per-module duplication is deliberate** (standalone-runnable rule, G-13).
6. **`SKILLS/` is out of scope** per owner instruction (2026-09-14).

## 1. Executive Summary

| Area | State |
|---|---|
| Architecture (6 ingest steps → one orchestrator → merged JSON) | **Sound.** Clear stage boundaries; each module standalone. |
| Clipboard parsers (planets, avastha, yogas, aspects) | **Strong.** Multi-pass fallbacks verified against mangled input; defensive as designed. A few *latent* fragilities (F-02…F-06) sit just outside the shape of real JHora output. |
| Argala engine | **Correct and verified** for all 6 axes, quarter cancellation, reverse counting, ketu's dual role. One latent input-fragility (F-04). |
| Wizards (aspects manual, BAV, arudha) | **Adequate.** Value clamping, screen persistence, skip behavior all work as documented. |
| Orchestrator / `compile_and_save` | **Risk center closed.** F-01 crash + F-11 silent empty steps fixed (Milestone A); the 344-line doctrine function is now module-level pure helpers behind a thin orchestrator (Milestone C, F-14/F-16); doctrine constants named (F-16). |
| Documentation | **Exceptional** for a project this size — 19 verified gotchas, per-stage schemas. Three doc/code mismatches found (F-31). |
| Automated verification | **Live** (F-15 closed): `tests/audit_smoke.py` (126 assertions, 0 failures) + GitHub Actions CI (`py_compile` all modules + smoke suite) — first CI ever. |

**Bottom line:** the pipeline is well designed and its documented behaviors were confirmed
true end-to-end. The improvement headroom is concentrated in three places:
(1) the paste-mode aspect crash in compile, (2) the family of *silent* drops/warnings
(empty pastes, strict regexes, unattachable yogas), and (3) zero automated tests.
A focused P0→P1 pass (TODO below) would move it from "works with the exact JHora build and
a careful user" to "defensive, verifiable, and safe to refactor."

## 2. Verified Behaviors (what the harness proved, 84/84)

- Planet table: name DB (incl. upagrahas, special lagnas), house math from lagna, retrograde
  via body-cell `(R)`, `- Md` suffix stripping, MT/exalted/debilitated, compound
  house-dignity (all six outcomes observed), upachaya prose for malefics/upagrahas in 3/6/10/11.
- No-lagna input ⇒ no `house`/`house_dignity` keys (compile falls back to aries, G-05).
- Argala: dhana cancellation at quarter-sum 5, boundary 7.5° (7°0′ vs 8°0′), reverse
  counting with `(reverse)` labels, ketu eff-9 *gives* vidya / eff-5 *blocks*, benefics-in-3
  block labha only at quarter-sum 5, vipreet (≥3) vs 3rd_house_special (1–2), strength labels.
- Avastha positional contract (Sanskrit age / English alertness / English moods; <2 pairs dropped).
- Yoga 3-pass parsing: tab → header-anchored fixed-width → regex, D-9 varga tokens,
  Naabhasa special case, `_2` duplicate suffixes.
- Aspect paste parser: 64.5 cutoff (65.0 kept), `-` cells, 9-column requirement,
  `house_N_{sign}` vs manual `house_N` key families.
- Compile: D1 self-heal, sign scaffolding + house numbers/lords/occupants, core-only
  occupants, G-01 pre-truncation conjunction (0.46° case), truncation formats
  (`D° M′` / `D°`, leading zeros kept), avastha/aspect/SAV/BAV attach, arudha/varnada
  uppercased-to-sign mapping, G-19 maandi-only yoga silently unattached, shared yoga payload,
  unclamped negative score (−75 observed), empty-occupant removal, lagna-only and
  no-lagna edge compiles.
- **G-10 crash reproduced exactly:** paste-mode float aspects → `AttributeError:
  'float' object has no attribute 'get'` inside `evaluate_planet_strength`.

## 3. Findings by Severity

### P0 — Confirmed crash / data-integrity breakers

**F-01 · Paste-mode aspect data crashes the compile (G-10, verified).**
`compile_and_save` → `evaluate_planet_strength` reads `data.get("strength", 0)` for each
received aspect. Paste mode stores **bare floats**; manual mode stores `{"strength", "relation"}`
objects. Any chart whose step 3 used "Paste from JHora Clipboard" (a first-class flow) crashes
compile with a raw traceback — no JSON written, all six steps lost, app restart required.
*Fix (keeps paste parser & formats 100% untouched):* in `launch_aspects_ui`'s
`hijacked_export`, normalize paste-mode floats to the object shape
(`{"strength": v, "relation": "neutral"}`) before storing into `raw_parsed_data` — or make the
scoring loop type-tolerant (`isinstance(data, dict)`). Capture-time normalization is preferred:
it also unifies the type for `from_ascendant_to_houses` (currently floats land on sign nodes
and would silently mix types if a future feature reads them with `.get`). Wrap
`compile_and_save` body in try/except → `show_error` so *any* future surprise degrades to a
modal instead of a traceback + total session loss.

**F-13 · Missing-module path raises an unhelpful TypeError.**
`ingest_planets/avasthas/yogas` call the imported function directly; if the `ImportError`
guard fired (`clean_and_parse_planets is None`), the user gets
`"Planet Parse Failed.\n'NoneType' object is not callable"` instead of the friendly
"module missing" the UI launchers already show. Add the same `if not X: return
self.show_error(...)` guard to the three ingest methods.

**F-11 · A paste step can complete with *zero* data (G-14, verified by reading; empty-clipboard → `[]`).**
`ingest_planets` on an empty (or non-matching) clipboard parses to `[]`, the step is marked
✓, and compile silently produces a varga with no planets (lagna falls back to aries, argala
all-`none`, yogas unattached, no warning). The standalone CLIs at least print
`"[!] Clipboard is empty."` — the GUI path has nothing. *Fix (pre-parse, format-neutral):*
check `pyperclip.paste().strip()` and the parsed record count in each `ingest_*`; on zero
records show the error modal and **do not** `mark_complete`. Optionally, at compile start,
warn (non-blocking) if the planets bucket is empty.

**F-12 · `compile_and_save` success on an all-empty session.**
Follow-up to F-11: after F-11, an all-empty compile is mostly prevented, but a compile with
e.g. only avasthas should at least *report* what went in (the success modal can list per-bucket
counts: N planets, M yogas, K aspects…). Pure addition to the modal text.

### P1 — Latent silent-wrong-data risks (outside today's exact JHora text, inside plausible input)

**F-02 · Retrograde detection is position-locked to the body cell (verified).**
`is_retrograde` is only true when `(R)` appears **before** the coordinate anchor
(`parts[0]`). A `(R)` after the longitude — a format a user's manual re-entry (or a JHora
build change) could produce — is silently discarded. No error, just a missing flag.
*Resolved 2026-09-15 (owner):* **additive tolerance** — post-coordinate `(R)` is now
detected (`"(R)" in line`); real JHora text output unchanged. Verified: harness T1b (3 probes).

**F-03 · Aspect vs planet row regex — original comparison was WRONG (corrected, audit V-07).**
The original finding claimed `parse_planets` made the apostrophe/space optional; re-checking
the actual `coord_pattern` during the 2026-09-15 decision implementation showed **both** parsers
require `DD SS' SS"` (apostrophe + space before seconds) — the only real difference was the
seconds token (`[\d.]+` vs `\d+(?:\.\d+)?`). The `20'0"` probe row is rejected by **both**
parsers (the harness probe's premise was false and is now corrected). *Resolved 2026-09-15
(owner: align):* the aspect seconds token is now `\d+(?:\.\d+)?` — tolerance exactly aligned
with `parse_planets`; output-identical for real JHora text. Verified: harness T8 (aligned
positive + aligned-rejection probes).

**F-04 · `get_quarter` mis-parses float degree strings (verified).**
`re.search(r"(\d+)°\s*(\d+)'?\s*([\d.]+)", …)` grabs the last digit-run immediately before `°`;
`"28.0° 00' 00.0""` parses as **0°** → quarter 1 → wrong argala cancellation/labels. Latent
today (pipeline always feeds `int°` strings from `reformat_longitude`) but one future code
path that formats a longitude with `f"{deg:.1f}°"` away from a wrong argala matrix. *Fix:*
`(\d+(?:\.\d+)?)°` in `get_quarter` (and, while there, the MT degree parse in
`parse_planets` line ~183 uses the same pattern family).

**F-05 · Yoga fixed-width pass with a header lacking a `Results` column → negative slice (verified).**
`header_bounds["results"]` becomes `-1`; `givers = line[givers:-1]` runs to end-of-line
minus one char (`"Mo           Moon-Sun comb"`), `definition` empty — silently mangled data.
Real JHora headers contain `Results`, so latent. *Fix:* if `header_bounds["results"] < 0`,
skip the fixed-width pass (fall through to the regex pass).

**F-06 · Yoga tab row with <4 non-empty cells is dropped with no fallback (verified).**
The tab branch `continue`s instead of falling through to passes 2/3. Inconsistent with the
fixed-width branch's defensive spirit. *Fix:* fall through instead of `continue` when
`len(cols) < 4`.

**F-07 · Moolatrikona rules for moon & mercury are unreachable (verified).**
Exaltation is *sign-based* in this repo and each of moon (taurus) / mercury (virgo) has its
MT window **inside** its own exaltation sign; the exalted check runs first, so
`check_moolatrikona` for these two planets can never fire — the `3.0001`/`15.0001` exclusive
lower bounds are dead code. Other five planets' MT windows are reachable (sun's verified
firing). *Resolved 2026-09-15 (owner):* **trim** — the moon/mercury `check_moolatrikona` entries
were removed with a doctrine comment; docs 02/04 updated (windows listed as removed and why).
Option (b) (point-based exaltation) remains out of scope.

**F-08 · Scoring precedence: special dignity suppresses house dignity (verified, undocumented).**
In `evaluate_planet_strength` the house-dignity deltas live in the `else` of the
`special_dignity` chain, so a debilitated planet in a worst-enemy sign scores only −40 (no
extra −20) — observed: expected −95, got −75, exactly the missing `Enemy Sign (-20)`.
Probably intentional (no double penalty) but the docs' scoring table lists both factors as
plainly additive. *Fix:* document the precedence in 01/02 and add a one-line code comment;
no behavior change unless the owner disagrees.

**F-09 · Sun never scores on received aspects (by omission).**
`benefics = [jupiter, venus, mercury, moon]`, `malefics = [saturn, mars, rahu, ketu]` — the
sun is in neither, so a strong sun aspect is silently worth 0. *Resolved 2026-09-15
(owner):* **keep 0** — the sun deliberately scores nothing on received aspects; documented
as owner-confirmed doctrine in 02/04.

**F-10 · Unattachable yogas vanish without a trace (G-19, verified).**
Yogas whose givers are only non-planet points (e.g. `Md`/maandi, special lagnas) can never
match `final_payload["planets"]` and are dropped from the final JSON with no warning; the
`"Md": "maandi"` entry in `giver_map` is effectively dead. *Fix:* collect the unmatched yoga
keys during the loop and include them in the success modal (`2 yoga(s) not attached (no core
planet givers): daama_daamini_yoga, …`). Zero schema change.

### P2 — Maintainability & robustness

**F-14 · `compile_and_save` extraction — RESOLVED (Milestone C).**
Was 344 lines at audit time (355 after Milestone A), 5 nested helpers, all doctrine inline.
Now extracted to module-level pure functions taking plain dicts — no Tk, no `self`:
`build_master_payload`, `score_planet`, `classify_yogas`, `scaffold_signs`,
`attach_positions`, `resolve_conjunctions_and_truncate` (G-01 pre-truncation order
preserved inside), `attach_avasthas` / `attach_aspects` / `attach_bav`, `attach_argala`,
`attach_arudhas`, `strip_empty_occupants`. Byte-identical merged JSON verified against
golden hashes (6/6 files) before and after.

**F-15 · ~~No tests, no CI~~ — RESOLVED (Milestone C).**
`tests/audit_smoke.py` is in-repo (headless, dependency `pyperclip` only, tkinter stubbed);
CI (`.github/workflows/ci.yml`) runs `python -m py_compile *.py` + `python tests/audit_smoke.py`
on every push/PR. Every future change now gets the 126-assertion regression gate.

**F-16 · ~~Doctrine magic numbers scattered~~ — RESOLVED (Milestone C, scope as listed).**
`compile_all.py` now carries named module-level constants (values byte-identical):
`CORE_PLANET_NAMES`, `BENEFIC_CASTERS`, `MALEFIC_CASTERS`, `GIVER_MAP`, `BAV_ROW_PLANETS`,
`CONJUNCTION_DEGREES` (2.0), `ASPECT_STRONG_MIN` (60), `STATUS_ACTIVE_MIN` (70),
`STATUS_DORMANT_MIN` (40), `BAV_HIGH_MIN` (5) / `BAV_LOW_MAX` (2), `SAV_HIGH_MIN` (30) /
`SAV_LOW_MAX` (25), `ASPECT_KEY_RE`. `calculate_argala.py` adds `QUARTER_1_MAX/_2/_3`
(7.5/15.0/22.5) to its existing `CORE_PLANETS` / `MALEFICS`. The `64.5` cutoff stays in
`parse_aspects.py` (parser file, out of F-16's named scope); standalone rule preserved.
Inventory noted in `AGENTS.md` §3 (F-31.4).

**F-20 · ~~Shared yoga payload object across planets~~ — RESOLVED (Milestone C).**
`classify_yogas` now deep-copies the payload per planet. Verified: harness T9
("per-planet yoga payloads are separate objects").

**F-21 · ~~Special-point name collision~~ — RESOLVED (Milestone C).**
First occurrence is kept; duplicates produce a `Warnings:` line in the success modal.
Verified: harness T22 (duplicate `gulika` rows → warning, no crash, math on first row).

**F-22 · ~~`int(parts[1])` on aspect keys can raise~~ — RESOLVED (Milestone C).**
`ASPECT_KEY_RE.fullmatch` gate in `attach_aspects`: malformed keys are skipped with a
`Warnings:` entry, no crash. Verified: harness T22 (`house_x_gemini` skipped + warned,
valid `house_4_gemini` still attached).

**F-23 · ~~`pyperclip.paste()` can raise~~ — RESOLVED (Milestone C).**
Per-module try/except around `paste()` in the four standalone `__main__` blocks
(`parse_planets`, `parse_avastha`, `parse_yogas`, `calculate_argala`) — message +
`SystemExit(1)`, no traceback. Standalone rule preserved (inline, no shared helper).
Verified: harness T23 (static AST check on all four).

**F-17 · ~~`show_error` doubles as the success modal~~ — RESOLVED (Milestone C).**
`show_info` added (title "✓ Success"); compile success and the cancelled-save/varga-pending
notices route through it; failures stay on `show_error`. Pure UI, no data change (modal
rendering: code-reading only — headless).

**F-18 · ~~Save-dialog cancel silent~~ — RESOLVED (Milestone C).**
`btn_compile` does re-run (verified by code reading: `mark_complete` disables step buttons
only). A cancelled save now shows "Save cancelled. Press Compile again to retry." via
`show_info`. Verified: harness T21 (cancelled `asksaveasfilename` → notice, no file,
no failure modal).

**F-19 · ~~Half-loaded state after varga-prompt cancel~~ — RESOLVED (Milestone C).**
`load_d1_profile` now sets the label to "🟡 D1 loaded — varga prefix pending: <file>" and
shows a notice; Load stays the recovery path. (Tk `askstring` cancel semantics:
code-reading only — headless.)

### P3 — Documentation corrections & hygiene

**F-31 · Doc/code mismatches — all four corrected (Milestone D; item 1 re-characterized in V-07):**
1. `02` (parse_aspects): "Longitude anchored like `parse_planets`" — corrected to the precise
   statement: both parsers require `DD SS' SS"`; the seconds token is now aligned
   (`\d+(?:\.\d+)?`). See F-03 (as corrected).
2. `02`/`04`: MT windows for moon/mercury — corrected (listed as removed 2026-09-15 with the
   shadowing reason). See F-07.
3. `01`/`02` scoring table: precedence note added (special dignity ⇒ house-dignity deltas
   skipped). See F-08.
4. `AGENTS.md` §3: full doctrine-constant inventory added (core-planet sets, caster lists,
   `GIVER_MAP`, thresholds, `MALEFICS`/`QUARTER_*`, upachaya-malefic list).

**F-32 · ~~`requirements.txt` / README~~ — RESOLVED (Milestone D).**
`pyperclip>=1.8` pin unchanged (fine). README Usage now separates the four CLI parsers
from the three GUI-only wizard modules and points to `tests/audit_smoke.py` + this file.

**F-28 · BAV `enforce_limits` value-clamps — behavior KEPT (as documented), hint added (Milestone D).**
Typing `10` becomes `8` (int 10 > 8 → set "8"). The BAV entry screen's instruction line
now reads "…Values auto-clamp to 0–8." (GUI hint: code-reading only — headless).

## 4. The To-Do List (execution order = listed order)

> Guardrails restated for every item: paste formats frozen (constraint 1), output schema
> frozen (2), math order frozen (3), monkeypatch frozen (4), duplication deliberate (5),
> `SKILLS/` untouched (6). Items marked *(decision)* need owner sign-off before code changes.

### P0 — do first (crash & silent-loss) — **completed 2026-09-15**

- [x] **TODO-01 (F-01):** Normalize paste-mode aspect values to `{"strength", "relation":"neutral"}`
      in `compile_all.py`'s aspects `hijacked_export` (both `planet_to_planet_aspects` and
      `from_ascendant_to_houses`), *or* make `evaluate_planet_strength` type-tolerant.
      Acceptance: harness T10 turns from "crash confirmed" to "compile succeeds, score uses
      the strength value". Paste parser file: **zero diff**.
      *Done: `normalize_aspect_values()` added to `compile_all.py` and applied in the capture
      closure; docs 03 §E + G-10 updated; `parse_aspects.py` untouched (zero diff, hash-verified
      against base commit in `vault/raw/state/MANIFEST.json`). Verified by execution: harness T9, T10.*
- [x] **TODO-02 (F-01):** Wrap `compile_and_save`'s body in try/except → `show_error`
      (traceback to modal). Acceptance: any injected exception shows a modal, no session loss.
      *Done: body moved to `_compile_and_save_impl()`; `compile_and_save` is the thin
      try/except wrapper — the public name and the UI wiring are unchanged. Verified by
      execution: harness T15 (injected failure → modal, no file written, no traceback).
      GUI rendering of the modal itself: code reading only.*
- [x] **TODO-03 (F-13):** Add `if not <parser>: return self.show_error("<Step> module missing.")`
      to `ingest_planets`, `ingest_avasthas`, `ingest_yogas` — matching the launchers' wording.
      *Done: all three ingest methods guarded (argala guard included in `ingest_planets`).
      Verified by execution: harness T16.*
- [x] **TODO-04 (F-11):** In each `ingest_*`: empty clipboard → error modal, no `mark_complete`;
      zero parsed records → same. (Pre-parse only; parsers untouched.)
      *Done: empty-clipboard and zero-rows checks added to all three ingest methods.
      Verified by execution: harness T17 (incl. positive control proving no over-blocking).
      Disclosed residual: a single-row paste (e.g. lagna-only) still completes the step —
      only zero rows is blocked; it is operator-visible via the F-12 "Rows ingested" count
      and the G-05 aries fallback is documented.*
- [x] **TODO-05 (F-12):** Success modal lists per-bucket counts (planets, avasthas, aspects,
      yogas, SAV, arudhas) so a sparse compile is visible at a glance.
      *Done: "Rows ingested: …" line appended to the success notice. Verified by
      execution: harness T9 (success-notice check).*

### P1 — latent data risks — **completed 2026-09-15**

- [x] **TODO-06 (F-04):** `get_quarter` regex → `(\d+(?:\.\d+)?)°` (and mirror in
      `parse_planets` MT degree parse). Acceptance: `get_quarter("28.0° 00' 00.0\"") == 4`;
      all existing harness T5 results unchanged.
- [x] **TODO-07 (F-05):** Yoga fixed-width pass: if `header_bounds["results"] < 0`, skip to
      the regex pass instead of slicing with −1.
- [x] **TODO-08 (F-06):** Yoga tab pass: `<4` non-empty cols → fall through to pass 2/3
      instead of dropping the line.
- [x] **TODO-09 (F-10):** Collect yoga keys that matched no core planet; append
      "N yoga(s) not attached: …" to the success modal.
- [x] **TODO-10 (F-02) (decision):** Owner call — add post-coordinate `(R)` tolerance to
      `parse_planets` (additive) or keep the strict body-cell contract. Until decided: document
      the requirement in the GUI hint text of step 1.
- [x] **TODO-11 (F-03) (decision):** Owner call — loosen the aspect row coordinate regex to the
      planet parser's tolerance (additive, output-identical for real JHora text) or document the
      exact required format in the aspects GUI hint.
- [x] **TODO-12 (F-08):** Document the scoring precedence (special dignity ⇒ house-dignity
      deltas skipped) in `01`/`02` + one code comment. *(decision only if owner wants additive
      scoring — that would change output values.)*
- [x] **TODO-13 (F-07):** Doc fix for unreachable moon/mercury MT windows; *(decision)* whether
      to trim the dead `check_moolatrikona` entries or keep them for doctrine completeness.
- [x] **TODO-14 (F-09) (decision):** Owner confirms sun-aspect scoring (0 today) vs adding
      `sun` to a caster list.
      *Done: both patterns fixed (`float` degree); `QUARTER_*` constants named. Verified by
      execution: harness T14 (acceptance case == 4, int case unchanged, T5 green) + T20
      (parse_planets MT boundary behavior through the full parser).*
      *Done: pass 2 now gated on `results > 0`; fall-through to pass 3. Verified: harness
      T14 (header without `Results` → clean regex-pass values).*
      *Done: tab branch no longer `continue`s on short rows. Verified: harness T14
      (3-col tab row now parsed).*
      *Done: `classify_yogas` returns the unattached keys; success notice lists them.
      Verified: harness T9 (maandi-only yoga named in the notice).*
      *Decided 2026-09-15 (owner): **additive tolerance** — `is_retrograde = "(R)" in line`.
      Real JHora output unchanged; docs 02 updated. Verified: harness T1b
      (post-coords detected, body-cell intact, no false positives).*
      *Decided 2026-09-15 (owner): **align** — seconds token now `\d+(?:\.\d+)?` exactly as in
      `parse_planets.coord_pattern` (audit V-07 corrected the original finding: both parsers
      require apostrophe + space; only the seconds token differed). Output-identical for real
      JHora text. Verified: harness T8 (aligned positive + aligned-rejection probes).*
      *Done: precedence documented in 01 + 02 scoring table; code comment in `score_planet`.
      No behavior change (owner kept scoring as-is — the additive variant was not requested).*
      *Decided 2026-09-15 (owner): **trim** — the two entries removed from
      `check_moolatrikona` with a doctrine comment; 02/04 updated. Verified: harness T20
      (window math for surviving planets intact) + T1/T4 green.*
      *Decided 2026-09-15 (owner): **keep 0** — documented as owner-confirmed doctrine in
      02/04; code comment in `score_planet`. No behavior change.*

### P2 — maintainability — **completed 2026-09-15**

- [x] **TODO-15 (F-15):** Adopt `jhora-audit-harness.py` as `tests/audit_smoke.py` (in-repo),
      run under plain `python`; add CI: `py_compile` all modules + smoke suite. First CI ever.
- [x] **TODO-16 (F-14):** Extract `compile_and_save` internals into module-level pure helpers
      (scoring first — it's the most valuable to test). Byte-identical output verified by the
      smoke suite before/after.
- [x] **TODO-17 (F-16):** Named module-level constants for all doctrine numbers in
      `compile_all.py` / `calculate_argala.py` (values unchanged; standalone rule preserved).
- [x] **TODO-18 (F-20):** Per-planet `deepcopy` of yoga payloads.
- [x] **TODO-19 (F-21/F-22):** Conjunction-pass name-collision guard; aspect-key shape
      validation with skip-and-warn.
- [x] **TODO-20 (F-23):** Catch `PyperclipException` in the four standalone `__main__` blocks.
- [x] **TODO-21 (F-17):** `show_info` modal variant; use for success.
- [x] **TODO-22 (F-18):** Notice on save-cancel ("press Compile again").
- [x] **TODO-23 (F-19):** Correct label + notice when the varga prompt is cancelled (G-17).
      *Done: `tests/audit_smoke.py` (REPO path derived from `__file__` — runs from anywhere);
      `.github/workflows/ci.yml` (ubuntu-latest, py 3.11, `py_compile` + suite). The
      workspace-root original is retained as an untracked pointer artifact.*
      *Done: 12 module-level functions (see F-14); `_compile_and_save_impl` is a thin
      orchestrator. Byte-identical output verified: all 6 golden merged-JSON hashes
      unchanged before/after the extraction (plus full suite green).*
      *Done: see F-16 for the full inventory (values byte-identical; standalone rule
      preserved; no shared module introduced).*
      *Done: `classify_yogas` copies per planet. Verified: harness T9
      (separate objects, equal content).*
      *Done: first-occurrence-kept + warning (F-21); `ASPECT_KEY_RE` gate + warning (F-22);
      warnings surface in the success modal. Verified: harness T22.*
      *Done: per-module inline try/except (standalone rule kept). Verified: harness T23
      (AST check on all four modules).*
      *Done: "✓ Success" titled modal; used by compile success, save-cancel, and
      varga-pending notices. (Rendering: code-reading only — headless.)*
      *Done: verified by execution: harness T21.*
      *Done: label → "🟡 D1 loaded — varga prefix pending: <file>" + notice. (Tk
      `askstring` path: code-reading only — headless.)*

### P3 — docs — **completed 2026-09-15**

- [x] **TODO-24 (F-31):** Apply the four doc corrections listed in §3-P3 (02 aspect regex note,
      MT shadowing, scoring precedence, AGENTS §3 constant inventory).
- [x] **TODO-25 (F-32):** README: point to `06`; note wizard modules have no CLI path.
- [x] **TODO-26 (F-28):** One-line GUI hint about BAV auto-clamp (optional).

## 5. Suggested Milestones

1. **Milestone A (1 focused session) — completed 2026-09-15:** TODO-01…05 → no more
   crash or silent-empty paths; harness T10 green.
2. **Milestone B (1 session) — completed 2026-09-15:** TODO-06…14 → parser edge hardening
   (all additive) + all four owner decisions recorded above. Audit correction V-07
   (F-03's comparison was wrong) issued during decision implementation and closed.
3. **Milestone C (1–2 sessions) — completed 2026-09-15:** TODO-15…23 → tests + CI live,
   `compile_and_save` split, constants named; golden-JSON byte-identity verified.
4. **Milestone D (small) — completed 2026-09-15:** TODO-24…26 → docs match code.

**Out of scope (explicit):** anything that changes what the clipboard parsers accept from real
JHora text or how the manual-entry flow works (constraint 1); output schema changes
(constraint 2); `SKILLS/` (constraint 6); geocoding/ephemeris features (never in scope —
JHora remains the calculation engine, see `01`).
      *Done: all four (see F-31); item 1 written per the V-07-corrected finding.*
      *Done: Usage section separates CLI parsers from GUI-only wizards; points to
      `tests/audit_smoke.py` + `docs/06`.*
      *Done: BAV entry screen instructions now say "Values auto-clamp to 0–8."
      (GUI hint: code-reading only — headless.)*
