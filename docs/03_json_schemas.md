# 03 — JSON Schemas (Every Stage)

All shapes are quoted exactly from the code. `V` = the varga prefix entered at load time (e.g. `D9`). Planet and sign names are always lowercase. Optional keys are marked `?`.

---

## A. `clean_and_parse_planets` output

```jsonc
{
  "planetary_positions": [
    {
      "body": "sun",                  // snake_case canonical name (also "lagna", "maandi", "gulika", "dhooma", "bhava_lagna", …)
      "longitude": "13° 14' 5.3\"",   // sign abbreviation stripped; "D° M' S\"" format
      "rasi": "virgo",                // lowercase sign name
      "is_retrograde": true,          // ? present only when "(R)" was in the source row
      "house": 5,                     // ? only when a valid lagna row exists
      "house_lord": "mercury",        // ? core planets + lagna only
      "special_dignity": "moolatrikona", // ? "exalted" | "debilitated" | "moolatrikona" (core planets only)
      "house_dignity": "good_friend_house", // ? core planets only: own_house | good_friend_house | friend_house | neutral_house | enemy_house | worst_enemy_house
      "upachaya_effect": "Placed in the 3rd Upachaya house, …" // ? malefics/upagrahas in houses 3,6,10,11
    }
  ]
}
```

## B. `compute_argala_matrix` output

```jsonc
{
  "argala_analysis": {
    "house_1": {                       // keys house_1 … house_12 (the TARGET house)
      "is_reverse_counted": false,     // true when rahu/ketu occupies the target house
      "working_argala": {
        "4H": {                        // keys are SOURCE houses, "{n}H" format
          "planets": ["mars", "ketu"],
          "type": "subha"              // dhana | subha | vidya | labha | vipreet_argala | 3rd_house_special
                                       // label gets " (reverse)" appended when is_reverse_counted
        }
      },
      "argala_strength_by_count": "medium" // none (0) | limited (1) | medium (2) | excellent (3+)
    }
  }
}
```

## C. `clean_and_parse_avastha` output

```jsonc
{
  "avasthas": [
    {
      "body": "sun",
      "age": "Baala",                 // Sanskrit word, kept untranslated
      "alertness": "Awake",           // English
      "moods": ["Hunger", "Thirst"]   // English, possibly empty list
    }
  ]
}
```

## D. `clean_and_parse_yogas` output

```jsonc
{
  "yogas": {
    "sunapha_yoga": {
      "active": true,                 // initial value; compile may flip to false
      "yoga_givers": "Mo",            // JHora abbreviations (Su Mo Ma Me Ju Ve Sa Ra Ke)
      "definition": "Combinations for wealth …"
    },
    "daama_daamini_yoga_2": { ... }   // duplicate names get _2, _3, … suffixes
  }
}
```

## E. Aspect strengths — two mode-dependent variants

**Paste mode** (`clean_and_parse_aspects`) — values are **bare floats**:

```jsonc
{
  "aspect_strengths": {
    "from_ascendant_to_houses": {
      "house_1_virgo": { "mars": 75.3, "saturn": 64.8 }   // keys "house_N_{sign}"; only values ≥ 64.5 kept
    },
    "planet_to_planet_aspects": {
      "sun_receives_aspects": { "saturn": 80.1 }          // keys "{planet}_receives_aspects"
    }
  }
}
```

**Manual mode** (`AspectsApp.compile_manual_data`) — values are **objects with a relation tag**:

```jsonc
{
  "aspect_strengths": {
    "from_ascendant_to_houses": {
      "house_3": { "mars": {"strength": 75.0, "relation": "enemy"} }  // keys "house_N" (NO sign)
    },
    "planet_to_planet_aspects": {
      "sun_receives_aspects": { "saturn": {"strength": 80.0, "relation": "neutral"} }
    }
  }
}
```

`relation ∈ {neutral, enemy, friend, worst_enemy, good_friend, own_house}`. Mode mixing is a real hazard — see gotcha G-10.

## F. Ashtakavarga wizard output

```jsonc
{
  "bhinnashtakavarga": {
    "sun":    {"aries": 4, "taurus": 5, …},   // 8 bodies: sun…saturn AND lagna; values 0–8
    "lagna":  {"aries": 3, …}                 // lagna is tracked here but EXCLUDED from SAV sums
  },
  "samudayashtakavarga": {
    "aries": 33, "taurus": 28, …              // per sign; theoretical max 56 (7 planets × 8 points, lagna excluded)
  }
}
```

## G. Arudha wizard output

```jsonc
{
  "arudhas":        {"AL": 1, "A4": 10, …},   // values are house numbers 1–12; "None" entries omitted
  "graha_arudhas":  {"sun": 7, "mars": 2, …},
  "varnadas":       {"V1": 1, "V2": 4, …}
  // screens whose entries are all "None" are omitted entirely
}
```

## H. D1 master JSON (input, merge base)

Expected top-level shape (authored/compiled previously; the code tolerates planet nodes at the root and re-nests them at compile time):

```jsonc
{
  "planets": {
    "sun":    { "D1_placement": {"longitude": "…", "sign": "leo", "house": 5, "dignity": "…"}, … },
    "moon":   { … }
  },
  "signs": {
    "aries":  { "D1_house_number": 1, "D1_house_lord": "mars", … },
    "taurus": { … }
  }
}
```

Anything already inside a planet/sign node is preserved; compile only adds/merges `{V}_*` keys (via `deep_merge`, which overwrites non-dict values).

## I. Final compiled output — `Master_Merged_{V}.json`

Top level: exactly `{"planets": {...}, "signs": {...}}` (D1 content + varga additions).

### Planet node additions

```jsonc
{
  "sun": {
    // …D1 keys preserved…
    "D9_placement": {
      "longitude": "13° 14'",          // truncated to D° M' AFTER conjunction math
      "sign": "virgo",
      "house": 5,
      "dignity": "friend_house",       // from house_dignity, default "neutral_house"
      "special_dignity": "moolatrikona", // ? only when present
      "upachaya_effect": "…",          // ? only when present
      "is_retrograde": true            // ? only when true
    },
    "D9_avastha_alertness": "Awake",   // always set when an avastha row matched
    "D9_avastha_age": "Baala",         // ? when present
    "D9_avastha_moods": ["Hunger"],    // ? when non-empty
    "D9_aspects_received": {           // ? from planet_to_planet_aspects (manual-mode objects or paste-mode floats, as captured)
      "saturn": {"strength": 80.0, "relation": "neutral"}
    },
    "D9_yogas": {                      // ? only for planets named as yoga givers
      "sunapha_yoga": {
        "active": true,
        "yoga_givers": "Mo",
        "definition": "…",
        "status": "Active",            // Active (avg ≥70) | Dormant (≥40) | Asleep (<40)
        "technical_analysis": "Combined Strength Score: 82.5/100. Sun: […] | Moon: […]" // one shared payload object attached to EVERY involved planet
      }
    }
  }
}
```

### Sign node additions

```jsonc
{
  "virgo": {
    // …D1 keys preserved…
    "D9_house_number": 5,              // 1–12, counted from the varga's lagna
    "D9_house_lord": "mercury",
    "D9_occupants": ["sun", "mercury"], // ? REMOVED when empty
    "D9_special_points": [             // ? non-core bodies (maandi, gulika, upagrahas, special lagnas, bhrigu_bindu, …)
      {
        "name": "gulika",
        "longitude": "12°",            // truncated to whole degrees AFTER conjunction math
        "upachaya_effect": "…",        // ? when present
        "conjuncting_planets": ["sun", "mars"] // ? bodies within 2.0° (planets and/or other special points); only when at least one
      }
    ],
    "D9_aspects_received": { "mars": 75.3 }, // ? from ascendant→house aspects; key "house_N_{sign}" supplies the sign,
                                             //   manual-mode key "house_N" is mapped via house number → sign
    "D9_sav": 33,                      // SAV of this sign
    "D9_bav": {                        // 8 entries max: sun…saturn + lagna
      "sun": 4, "moon": 2, "mars": 5, "mercury": 6, "jupiter": 3, "venus": 7, "saturn": 1, "lagna": 3
    },
    "D9_effective_argala": {           // ? working_argala for the house this sign corresponds to
      "4H": {"planets": ["mars"], "type": "subha"}
    },
    "D9_arudhas": ["AL", "A10"],       // ? uppercase labels; one list per wizard category:
    "D9_graha_arudhas": ["SUN"],       //   {V}_arudhas, {V}_graha_arudhas, {V}_varnadas
    "D9_varnadas": ["V5"]
  }
}
```

### Key-derivation rules (for consumers)

- House ↔ sign: sign at `ZODIAC_ORDER[(lagna_idx + house − 1) % 12]`.
- `{V}_house_lord` = `RASI_LORDS[sign]` (classical lords; no nodes).
- `{V}_effective_argala` lands on the sign that owns the argala **target** house; the `"{n}H"` keys inside refer to **source** houses of the intervening planets.
- Arudha label `X` at house `h` lands on the sign owning house `h`, uppercased.

## J. Values that are consumed downstream only as text

- `upachaya_effect` (parser-generated prose), `technical_analysis` (score breakdown prose), `definition` (yoga definitions) — natural-language fields meant for an LLM consumer; do not treat them as enums.
