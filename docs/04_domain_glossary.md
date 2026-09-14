# 04 — Jyotish Domain Glossary (for LLM Consumers)

Terms the code uses, with the exact meaning attached to them in this repository. Where the code encodes a specific school's convention, the convention is stated as binding here.

## Chart Basics

| Term | Meaning in this repo |
|---|---|
| **Varga** | A divisional chart (e.g. D1 birth chart, D9 navamsa). The user supplies a prefix token (`D9`) that becomes the key namespace `{V}_*` in the merged JSON. |
| **D1 (Rasi chart)** | The birth chart. Its compiled JSON is the merge base ("D1 master profile") for all other vargas. |
| **Rasi** | One of the 12 signs, always lowercase (`aries`…`pisces`), ordered by `ZODIAC_ORDER`. |
| **Lagna (Ascendant)** | The rising sign; row `Lagna` in the JHora planet table. Anchor for house numbering: lagna's sign = house 1. |
| **House (bhava)** | Whole-sign house counted from the lagna of the *current* varga: `house = (sign_idx − lagna_idx) % 12 + 1`. |
| **Rasi lord (dispositor)** | Classical sign lord (`RASI_LORDS`: aries→mars, taurus→venus, gemini/virgo→mercury, cancer→moon, leo→sun, libra→venus, scorpio→mars, sagittarius/pisces→jupiter, capricorn/aquarius→saturn). Called "landlord" in code comments. |

## Planets & Points

| Term | Meaning |
|---|---|
| **Core planets** | The 9 grahas: `sun, moon, mars, mercury, jupiter, venus, saturn, rahu, ketu`. Only these get placements, dignities, avasthas, aspect receivers, yoga attachments, strength scores. |
| **Benefics / malefics** | Scoring lists: benefics = `jupiter, venus, mercury, moon`; malefics = `saturn, mars, rahu, ketu`. The **sun is in neither list** for aspect scoring (owner-confirmed 2026-09-15, F-09). For upachaya purposes malefics = `sun, mars, saturn, rahu, ketu`. |
| **Rahu / Ketu** | Lunar nodes. Exaltation convention bound in this repo: rahu exalted in taurus / debilitated in scorpio; ketu the mirror (scorpio / taurus). Counting the target house as reversed for argala when either occupies it. |
| **Retrograde `(R)`** | Marked `is_retrograde: true` on placement; no score effect. |
| **Upagrahas (shadow sub-planets)** | `dhooma, vyatipata, parivesha, indra_chapa, upaketu, kaala, mrityu, artha_prahara, yama_ghantaka` plus `maandi, gulika` (`Md`, `Gk`). Treated as special points, eligible for upachaya turnaround text. |
| **Special lagnas / special points** | `bhava_lagna, hora_lagna (HL), ghati_lagna (GL), sree_lagna (SL), pranapada_lagna (PrL), bhrigu_bindu` — parsed like planets but stored under `{V}_special_points`. |
| **Special points (`{V}_special_points`)** | Any parsed body that is not a core planet and not lagna. Stored per sign with degree-only longitude and optional `conjuncting_planets`. |

## Dignity System

| Term | Meaning |
|---|---|
| **Exaltation / debilitation** | Fixed sign per planet (`DIGNITIES`). Worth +20 / −40 in scoring. |
| **Moolatrikona (MT)** | Degree window within a sign where a planet is "root of the trine" — counted equal to exalted (+20). Windows: sun leo 0–20°, mars aries 0–12°, jupiter sagittarius 0–10°, venus libra 0–15°, saturn aquarius 0–20°. (Moon taurus 3–20° and mercury virgo 15–20° were removed 2026-09-15, F-07: unreachable under sign-based exaltation, which runs first.) |
| **House dignity** | Compound relationship between planet and its sign lord: natural friendship (fixed per the 7 true planets) combined with temporary friendship (lord in houses 2/3/4/10/11/12 relative to the planet ⇒ temporary friend). Sum maps to `good_friend_house / friend_house / neutral_house / enemy_house / worst_enemy_house`; same-sign = `own_house`. Default when unknown: `neutral_house`. |

## Houses

| Term | Meaning |
|---|---|
| **Kendra / Trikona** | Angles (1,4,7,10) and trines (1,5,9). In scoring, houses 1,4,5,7,9,10 all get +10. |
| **Upachaya** | "Growing" houses **3, 6, 10, 11**. Malefics and upagrahas here receive an `upachaya_effect` flag: their harsh energy is treated as turning constructive over time. Upachaya also **reverses afflictions**: nodal conjunction, special-point conjunction, malefic aspects, and dispositor-in-dusthana penalties are upgraded/neutralized when the afflicting body carries `upachaya_effect`. |
| **Dusthana** | Houses 6, 8, 12 — decline houses; −30 in scoring, except house 6 with upachaya_effect (+15). |
| **Argala** | "Intervention" — planetary influence on a house from (normally) its 2nd (dhana), 4th (subha), 5th/9th (vidya), 11th (labha). |
| **Virodhargala** | Counter-intervention that cancels argala: from 12th vs 2nd, 10th vs 4th, 9th↔5th, and benefics in 3rd vs 11th. Cancellation rule used here: an argala is blocked when argala-planet quarter + virodhargala-planet quarter = 5. |
| **Vipreet argala** | 3+ malefics in the (effective) 3rd — treated as a *positive* intervention on the 11th-relative axis. 1–2 malefics there get `3rd_house_special`. |

## State & Averages

| Term | Meaning |
|---|---|
| **Avastha** | Planet state, three fields: `age` (Sanskrit: Baala/Madya/Vriddha — infant/adult/old), `alertness` (jaagrita/awake, swapna/dreaming, sushupta/asleep), `moods` (e.g. hunger, thirst). Alertness is scored +10/−20/−40. |
| **Ashtakavarga** | Point-based strength system. **BAV (Bhinnashtakavarga)**: per-planet 0–8 points per sign, 8 bodies tracked (incl. lagna). **SAV (Samudayashtakavarga)**: per-sign totals (lagna excluded). Scored +10 (BAV ≥5, SAV ≥30) / −10 (BAV ≤2, SAV <25). |
| **Yoga** | A named planetary combination. Parsed with its `yoga_givers` (abbreviations like `Su`, `Mo`) and `definition`. At compile, the average strength score of its givers classifies it: **Active (avg ≥70) · Dormant (avg ≥40, <70) · Asleep (avg <40)**; `active` stays true only for Active. |
| **Aspect strength (%)** | JHora's aspect values (~0–100%). Parser keeps only ≥64.5; scoring acts only at ≥60. |

## Arudha Family

| Term | Meaning |
|---|---|
| **Arudha pada (bhavapada)** | The "manifest image" point of a house, e.g. `AL` = Arudha Lagna (public image), `A2`…`A12`. Wizard maps each to a house. |
| **Graha arudha** | Arudha of a planet (one per the 9 planets). |
| **Varnada lagna (V1–V12)** | Varnada-indicated points per house, entered per house in the wizard. |

All three are stored as **uppercase labels in lists on the sign that owns the chosen house** (`{V}_arudhas`, `{V}_graha_arudhas`, `{V}_varnadas`).
