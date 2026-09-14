import re
import json
import pyperclip

NAME_DATABASE = {
    "planets": {
        "Sun": "sun",
        "Moon": "moon",
        "Mars": "mars",
        "Mercury": "mercury",
        "Jupiter": "jupiter",
        "Venus": "venus",
        "Saturn": "saturn",
        "Rahu": "rahu",
        "Ketu": "ketu"
    }
}

def clean_and_parse_avastha(raw_text):
    parsed_records = []

    # Obliterate null bytes from clipboard buffer
    raw_text = raw_text.replace('\x00', '')

    lines = raw_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()

        # Skip headers entirely to avoid choking on mangled Varga string truncations
        if not line or line.startswith("Planet") or "Alertness" in line:
            continue

        # 1. Extract the base planet name
        planet_match = re.match(r"^([A-Za-z]+)", line)
        if not planet_match:
            continue

        raw_planet = planet_match.group(1)
        planets_db = NAME_DATABASE.get("planets", {})
        body_mapped = planets_db.get(raw_planet, raw_planet.lower())

        # 2. Extract all 'Sanskrit (English)' blocks natively
        # This regex perfectly grabs every word followed by parenthesis, safely navigating commas
        pairs = re.findall(r"([A-Za-z]+)\s*\(([^)]+)\)", line)

        if len(pairs) >= 2:
            # Rule: Age strictly Sanskrit (Index 0 of the first pair)
            age_sanskrit = pairs[0][0]

            # Rule: Alertness strictly English (Index 1 of the second pair)
            alertness_english = pairs[1][1]

            # Rule: Mood strictly English (Index 1 of all remaining pairs)
            moods_english = [p[1] for p in pairs[2:]]

            record = {
                "body": body_mapped,
                "age": age_sanskrit,
                "alertness": alertness_english,
                "moods": moods_english
            }

            parsed_records.append(record)

    return {"avasthas": parsed_records}

if __name__ == "__main__":
    # F-23: no clipboard mechanism (e.g. headless) is a message, not a traceback.
    try:
        clipboard_data = pyperclip.paste()
    except pyperclip.PyperclipException as e:
        print(f"[!] No clipboard mechanism available: {e}")
        raise SystemExit(1)

    if not clipboard_data.strip():
        print("[!] Clipboard is empty. Copy JHora Avastha data first.")
    else:
        result_json = clean_and_parse_avastha(clipboard_data)
        print(json.dumps(result_json, indent=4))