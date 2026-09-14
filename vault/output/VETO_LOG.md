# VETO_LOG.md — Ironclad Audit, Run 1

- **Veto code:** `HALLUCINATION` (primary), `WEAK_FOUNDATION` (secondary)
- **Failed gates:** Gate 2 — Traceability Matrix; Gate 3 — Confidence Layering
- **Submission audited:** commit `5e40abd` (README.md, AGENTS.md, docs/01–05, SKILLS/README.md, requirements.txt, .gitignore)
- **Raw sources:** 8 pipeline modules + 2 skill definitions at boot commit `502c4c1`, SHA-256 per `vault/raw/state/MANIFEST.json`

Gate 0 (input presence) and Gate 1 (integrity) passed: all 10 raw inputs present and hash-identical to boot state. Gates 2–3 failed. Gate 4 findings recorded as advisory omissions and folded into the forced rewrite.

---

## VETO: HALLUCINATION — failing items

| # | Submission location | Claim | Evidence | Minimum correction required |
|---|---|---|---|---|
| 1 | `docs/03_json_schemas.md` §G | Arudha wizard output contains JSON key `"final_output": {}` | `parse_arudha.py` L123–126: `final_output` is an in-memory attribute; the serialized object is `{arudhas, graha_arudhas, varnadas}` only. No such key exists in any output. | Delete the key; state empty-screen omission as prose. |
| 2 | `docs/03_json_schemas.md` §F | SAV "0–48 theoretical range" | `parse_ashtakavarga.py` L177–184: SAV sums 7 planets (lagna excluded at L180–181) × 0–8 ⇒ max 56. Claim ungrounded and numerically wrong. | Correct to 56 with derivation. |
| 3 | `docs/04_domain_glossary.md` Rasi lord row | `RASI_LORDS` maps "libra/taurus→venus" (taurus duplicated, libra omitted in sequence) | `compile_all.py` L34–38: taurus→venus and libra→venus are distinct entries. | Rewrite mapping 1:1 with code. |
| 4 | `AGENTS.md` §6; `docs/01` §Compile | Strength scores are a "0–100 scale" | `compile_all.py` L387 (`score = 100`), L481 (`return score`): no clamp exists; additive modifiers can exceed 100 or go negative. | Rewrite as "100 baseline, additive, unclamped". |
| 5 | `docs/04_domain_glossary.md` Yoga row | "Dormant 40–69" | `compile_all.py` L502–503: float comparisons `avg >= 70` / `avg >= 40`; integer phrasing not code-anchored. | Restate as threshold conditions. |
| 6 | `docs/05` GUI/Environment Notes | MT bounds `3.0001`/`15.0001` exist "to avoid MT/exaltation overlap disputes" | No code comment or logic states a rationale; the exaltation check runs first, so the stated causal claim is inference presented as fact. | Strip causal claim; state only verifiable mechanics. |

## VETO: WEAK_FOUNDATION — failing item

- Core reference claims consumed by future agents (JSON schemas §F/§G; scoring scale in `AGENTS.md` §6) relied on the 0.0–0.5-confidence claims above without operator warning. Correction: raise every core claim to ≥0.8 via the corrections above.

## Gate 4 — Adversarial Omission Attack (advisory, folded into rewrite)

- O-1: Silent drop of yogas whose givers match no loaded planet; `Md` (maandi) givers can never attach because maandi is a special point, never a planet node (`compile_all.py` L488, L490–525).
- O-2: Step completion only proves the parser did not raise; an empty/malformed clipboard still marks a step done and compiles with lagna defaulting to `aries` (`compile_all.py` L160–165, L217+).
- O-3: MT degree parse requires seconds (missing seconds ⇒ degree `0.0`, `parse_planets.py` L171–176); house-less positions are excluded from the argala matrix (`calculate_argala.py` L36–43).

## Constraints honored

- No rewritten submission text in this log; no speculative fixes; no benefit-of-the-doubt language.

## Disposition

`VETO_LOG.md` issued to the worker agent per orchestrator instruction ("Re-work if needed"). A forced rewrite was performed by the worker in a separate role; the rewritten submission was re-audited (Run 2 — see `AUDIT_REPORT.md`).
