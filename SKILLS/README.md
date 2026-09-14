# SKILLS — Agent Behavior Skills

Markdown skill definitions only. **Nothing in the Python pipeline imports or references these files.**

| Skill | File | Purpose | When to apply |
|---|---|---|---|
| `silent-executor` | `SILENT-EXECUTOR/skill.md` | Output-style contract: execute the user's explicit instruction, return only the requested deliverable — no commentary, opinions, alternatives, or process narration. | When the user requests tool-like output or says "just do it". |
| `ironclad-post-mortem-integrity-auditor` | `AUDIT/skill.md` | Adversarial post-hoc auditor: verifies input hashes against a manifest, claim traceability, confidence layering, and omission risk; issues `PASS` or a `VETO_*` code. Never rewrites work. | Only after a worker agent halts, an orchestrator explicitly requests an audit, and the `vault/` layout it expects exists (`vault/raw/`, `vault/raw/state/MANIFEST.json`, `vault/output/SUBMISSION/`). That layout belongs to a different assignment-submission pipeline; it is not present in this repository. |

Ordering rule: `AUDIT` runs after work halts and requires an explicit orchestrator request; it is never part of normal execution. `SILENT-EXECUTOR` governs response style during execution and is subordinate to safety/platform constraints (stated in its own Safety Override section).
