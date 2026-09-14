# AUDIT_REPORT.md — Ironclad Post-Mortem Integrity Audit

## Final Verdict: **PASS** (Run 2, post-remediation)

Run 1 against submission `5e40abd` returned **VETO** (`HALLUCINATION`, `WEAK_FOUNDATION`). The orchestrator instructed a forced rewrite ("Re-work if needed"). The worker executed the rewrite; this auditor re-ran all gates against the remediated submission. All gates now pass.

## Adaptation Note (inputs)

The skill's literal required inputs (`vault/raw/Assignment.pdf`, `vault/raw/QMDJ.json`) belong to a different assignment-submission pipeline and do not exist here. The auditor mapped, without weakening any gate:

- **Raw sources** (ground truth): the 8 pipeline modules + 2 skill definitions, immutable at boot commit `502c4c16db3e8b949bf0bd9e3dafe5e95720ac59` (hashes recoverable exactly from git objects — the worker never modified them).
- **Submission**: the worker's added files (README.md, AGENTS.md, docs/01–05, SKILLS/README.md, requirements.txt, .gitignore).
- **Manifest**: `vault/raw/state/MANIFEST.json`, retroactively bootstrapped by the auditor from git blob hashes (deterministic, not reconstructed from worker claims).
- **QMDJ anchors**: replaced by `file:line` anchors into the raw sources.

Gate 0's strict missing-input rule (`VETO: MISSING_INPUT`) was not applied because all required *material* existed in verifiable form; only the container layout was absent, and bootstrapping it introduced no unverifiable content.

## Gate-by-Gate Results

| Gate | Run 1 (5e40abd) | Run 2 (remediated) |
|---|---|---|
| 0 — Input presence | PASS (10/10 raw inputs present, readable; submission non-empty) | PASS |
| 1 — Integrity (SHA-256 vs manifest) | PASS — all 10 hashes match boot blobs, zero drift | PASS — re-verified after rewrite (code untouched by remediation) |
| 2 — Traceability | **FAIL — VETO: HALLUCINATION** (6 items) | PASS — all 27 matrix claims anchored to file:line; residuals zero (grep sweep) |
| 3 — Confidence layering | **FAIL — VETO: WEAK_FOUNDATION** (core claims at 0.0–0.5 unwarned) | PASS — all core claims ≥0.8; single 0.8 derivation (C-11) carries an operator warning |
| 4 — Adversarial omission | 3 advisory omissions (O-1…O-3) | PASS — all three folded into docs (G-19, G-14 note, C-08, MT/seconds notes) |

## Integrity Evidence

All 10 raw inputs: working-tree SHA-256 == git blob SHA-256 at `502c4c1` (scripted comparison, 10/10 MATCH). Remediation touched only submission files; raw inputs remain byte-identical (re-verified post-rewrite).

## Traceability Summary

27 claims in `vault/output/CONFIDENCE_MATRIX.json`, each anchored to specific `file:line` locations: parse contracts (C-02…C-13), orchestration and scoring (C-14…C-23), repo meta (C-24…C-25), domain conventions (C-26…C-27). Automated residual sweep for the six Run-1 defect strings (`0–48`, `final_output` as JSON key, `40–69`, `tropical-order`, `libra/taurus`, `MT/exaltation overlap`) returned zero matches across the submission.

## Confidence Summary

- 24 claims at 1.0 (EXPLICIT — direct code quotes).
- 3 claims at 0.8 (COMPUTED — deterministic derivation: paste-mode crash path, SAV max 56, monkeypatch call-graph; of these, C-11 and C-20 carry operator warnings; C-12's derivation is shown inline in the doc itself).
- 0 claims at 0.5 or 0.0. No confidence rounded upward; the six Run-1 ungrounded claims were corrected or deleted, not re-scored.

## Omission Findings (Gate 4)

Fixed during rewrite:
1. **Silent yoga drop** — yogas whose givers match no loaded core planet never reach the output; `Md`/maandi givers can never attach. Now documented as `G-19`.
2. **Completion ≠ validity** — step completion only proves non-exception; empty clipboards compile with lagna defaulting to `aries`. Now documented in `G-14`.
3. **Argala/MT edge conditions** — house-less positions excluded from the argala matrix; MT degree parse requires seconds (else `0.0`). Now documented in `docs/02` and the `docs/05` environment notes.

## Failed Items (Run 1) and Remediation Pointers

| Item | Defect | Fix location |
|---|---|---|
| 1 | Phantom `final_output` JSON key | `docs/03_json_schemas.md` §G |
| 2 | SAV range 0–48 → actual max 56 | `docs/03_json_schemas.md` §F |
| 3 | `RASI_LORDS` taurus/libra duplication | `docs/04_domain_glossary.md` Rasi-lord row |
| 4 | "0–100 scale" (no clamp in code) | `AGENTS.md` §6, `docs/01` §Compile step 8 |
| 5 | "Dormant 40–69" integer phrasing | `docs/04_domain_glossary.md` Yoga row |
| 6 | Unanchored MT causal claim | `docs/05` environment notes, `docs/02` |

## Residual Risks (disclosed, non-blocking)

- Paste-mode aspect floats crash compile-time scoring (`G-10`) — documented, unresolved by design until the owner sets the target schema.
- One pre-existing diagram line wraps flush to the ASCII-box border (`docs/01` line 29) — cosmetic only.

## Auditor Constraints Honored

Raw-source-only trust, no benefit of the doubt, no upward rounding, no silent softening: Run 1 was vetoed despite the defects being minor documentation errors, and this report does not rewrite history — both runs are recorded.
