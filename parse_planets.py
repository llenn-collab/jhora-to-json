import re
import json
import pyperclip

NAME_DATABASE = {
    "planets": {
        "Lagna": "lagna",
        "Sun": "sun", "Moon": "moon", "Mars": "mars",
        "Mercury": "mercury", "Jupiter": "jupiter", "Venus": "venus",
        "Saturn": "saturn", "Rahu": "rahu", "Ketu": "ketu",
        "Maandi": "maandi", "Md": "maandi",
        "Gulika": "gulika", "Gk": "gulika",
        "Dhooma": "dhooma", "Vyatipata": "vyatipata", 
        "Parivesha": "parivesha", "Indra Chapa": "indra_chapa", 
        "Upaketu": "upaketu", "Kaala": "kaala", 
        "Mrityu": "mrityu", "Artha Prahara": "artha_prahara", 
        "Yama Ghantaka": "yama_ghantaka",
        "Bhava Lagna": "bhava_lagna", "Hora Lagna": "hora_lagna",
        "Ghati Lagna": "ghati_lagna", "Bhrigu Bindu": "bhrigu_bindu",
        "HL": "hora_lagna", "GL": "ghati_lagna",
        "SL": "sree_lagna", "PrL": "pranapada_lagna"
    },
    "rasis": {
        "Le": "leo", "Sc": "scorpio", "Aq": "aquarius", "Pi": "pisces",
        "Li": "libra", "Vi": "virgo", "Ar": "aries", "Cp": "capricorn",
        "Ge": "gemini", "Ta": "taurus", "Sg": "sagittarius", "Cn": "cancer"
    }
}

ZODIAC_ORDER = [
    "aries", "taurus", "gemini", "cancer",
    "leo", "virgo", "libra", "scorpio",
    "sagittarius", "capricorn", "aquarius", "pisces"
]

RASI_LORDS = {
    "aries": "mars", "taurus": "venus", "gemini": "mercury", "cancer": "moon",
    "leo": "sun", "virgo": "mercury", "libra": "venus", "scorpio": "mars",
    "sagittarius": "jupiter", "capricorn": "saturn", "aquarius": "saturn", "pisces": "jupiter"
}

NATURAL_FRIENDSHIP = {
    "sun": {"friends": ["moon", "mars", "jupiter"], "enemies": ["venus", "saturn"], "neutral": ["mercury"]},
    "moon": {"friends": ["sun", "mercury"], "enemies": [], "neutral": ["mars", "jupiter", "venus", "saturn"]},
    "mars": {"friends": ["sun", "moon", "jupiter"], "enemies": ["mercury"], "neutral": ["venus", "saturn"]},
    "mercury": {"friends": ["sun", "venus"], "enemies": ["moon"], "neutral": ["mars", "jupiter", "saturn"]},
    "jupiter": {"friends": ["sun", "moon", "mars"], "enemies": ["mercury", "venus"], "neutral": ["saturn"]},
    "venus": {"friends": ["mercury", "saturn"], "enemies": ["sun", "moon"], "neutral": ["mars", "jupiter"]},
    "saturn": {"friends": ["mercury", "venus"], "enemies": ["sun", "moon", "mars"], "neutral": ["jupiter"]}
}

DIGNITIES = {
    "sun": {"exalted": "aries", "debilitated": "libra"},
    "moon": {"exalted": "taurus", "debilitated": "scorpio"},
    "mars": {"exalted": "capricorn", "debilitated": "cancer"},
    "mercury": {"exalted": "virgo", "debilitated": "pisces"},
    "jupiter": {"exalted": "cancer", "debilitated": "capricorn"},
    "venus": {"exalted": "pisces", "debilitated": "virgo"},
    "saturn": {"exalted": "libra", "debilitated": "aries"},
    "rahu": {"exalted": "taurus", "debilitated": "scorpio"},
    "ketu": {"exalted": "scorpio", "debilitated": "taurus"}
}

def check_moolatrikona(planet, rasi, degree):
    mt_rules = {
        "sun": ("leo", 0, 20),
        "moon": ("taurus", 3.0001, 20),
        "mars": ("aries", 0, 12),
        "mercury": ("virgo", 15.0001, 20),
        "jupiter": ("sagittarius", 0, 10),
        "venus": ("libra", 0, 15),
        "saturn": ("aquarius", 0, 20)
    }
    if planet in mt_rules:
        mt_rasi, start, end = mt_rules[planet]
        if rasi == mt_rasi and start <= degree <= end:
            return True
    return False

def reformat_longitude(long_str):
    match = re.match(r"(\d+)\s+[A-Za-z]{2}\s+(.*)", long_str)
    if match:
        return f"{match.group(1)}° {match.group(2)}"
    return long_str

def clean_and_parse_planets(raw_text):
    parsed_records = []
    raw_text = raw_text.replace('\x00', '')
    
    # Strictly target the coordinates to slice through any mangled JHora headers.
    coord_pattern = r"(\d+\s+[A-Za-z]{2}\s+\d+'\s+\d+(?:\.\d+)?\")"

    lines = raw_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        # Skip headers or empty lines entirely
        if not line or line.startswith("Body") or "Longitude" in line:
            continue

        parts = re.split(coord_pattern, line)

        # Ensure we found both a body and a coordinate block
        if len(parts) >= 2:
            raw_body_section = parts[0].strip()
            longitude_raw = parts[1].strip()

            is_retrograde = "(R)" in raw_body_section
            clean_body = re.sub(r"\s*-\s*[A-Za-z]{2,3}$", "", raw_body_section)
            clean_body = clean_body.replace("(R)", "").strip()

            # Ensure bodies gracefully fallback to snake_case if they aren't explicitly in the DB
            body_mapped = NAME_DATABASE["planets"].get(clean_body, clean_body.lower().replace(" ", "_"))

            # Extract the Rasi abbreviation directly from the secure longitude string
            rasi_match = re.search(r"\d+\s+([A-Za-z]{2})\s+", longitude_raw)
            rasi_raw = rasi_match.group(1) if rasi_match else ""
            rasi_mapped = NAME_DATABASE["rasis"].get(rasi_raw, rasi_raw.lower())
            
            longitude_formatted = reformat_longitude(longitude_raw)

            record = {
                "body": body_mapped,
                "longitude": longitude_formatted,
                "rasi": rasi_mapped
            }

            if is_retrograde:
                record["is_retrograde"] = True

            parsed_records.append(record)

    lagna_rasi = next((r["rasi"] for r in parsed_records if r.get("body") == "lagna"), None)
    core_planet_keys = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"]

    UPACHAYA_HOUSES = [3, 6, 10, 11]
    MALEFICS_AND_UPAGRAHAS = [
        "sun", "mars", "saturn", "rahu", "ketu",
        "maandi", "gulika", "dhooma", "vyatipata", "parivesha",
        "indra_chapa", "upaketu", "kaala", "mrityu", "artha_prahara", "yama_ghantaka"
    ]

    if lagna_rasi and lagna_rasi in ZODIAC_ORDER:
        lagna_idx = ZODIAC_ORDER.index(lagna_rasi)

        for record in parsed_records:
            rasi = record.get("rasi")
            body = record.get("body")

            if rasi in ZODIAC_ORDER:
                rasi_idx = ZODIAC_ORDER.index(rasi)
                house_num = (rasi_idx - lagna_idx) % 12 + 1
                record["house"] = house_num
                
                # Upachaya Turnaround Engine for Malefics and Upagrahas
                if body in MALEFICS_AND_UPAGRAHAS and house_num in UPACHAYA_HOUSES:
                    suffix = "rd" if house_num == 3 else "th"
                    entity_type = "malefic planet" if body in ["sun", "mars", "saturn", "rahu", "ketu"] else "upagraha"
                    
                    record["upachaya_effect"] = (
                        f"Placed in the {house_num}{suffix} Upachaya house, the fierce energy of this "
                        f"{entity_type} undergoes a positive turnaround. It grants resilience, competitive drive, "
                        f"and material growth that increases steadily over time to overcome obstacles."
                    )

                if body in core_planet_keys or body == "lagna":
                    house_lord_base = RASI_LORDS.get(rasi)
                    if house_lord_base:
                        record["house_lord"] = house_lord_base

    planet_houses = {r.get("body"): r.get("house") for r in parsed_records if "house" in r}

    for record in parsed_records:
        body = record.get("body")
        rasi = record.get("rasi")
        longitude = record.get("longitude")

        if body not in core_planet_keys:
            continue

        deg = 0.0
        if longitude:
            deg_match = re.search(r"(\d+)°\s*(\d+)'\s*([\d.]+)", longitude)
            if deg_match:
                deg = int(deg_match.group(1)) + (int(deg_match.group(2)) / 60.0) + (float(deg_match.group(3)) / 3600.0)

        dignity_data = DIGNITIES.get(body, {})
        if rasi == dignity_data.get("exalted"):
            record["special_dignity"] = "exalted"
        elif rasi == dignity_data.get("debilitated"):
            record["special_dignity"] = "debilitated"
        elif check_moolatrikona(body, rasi, deg):
            record["special_dignity"] = "moolatrikona"

        lord = record.get("house_lord")
        if lord == body:
            record["house_dignity"] = "own_house"
        elif lord in planet_houses and body in NATURAL_FRIENDSHIP:
            lord_house = planet_houses[lord]
            my_house = record["house"]

            distance = (lord_house - my_house) % 12 + 1
            is_temp_friend = distance in [2, 3, 4, 10, 11, 12]

            nat_relations = NATURAL_FRIENDSHIP[body]
            if lord in nat_relations.get("friends", []): nat_val = 1
            elif lord in nat_relations.get("enemies", []): nat_val = -1
            else: nat_val = 0

            temp_val = 1 if is_temp_friend else -1
            total_val = nat_val + temp_val

            if total_val == 2: record["house_dignity"] = "good_friend_house"
            elif total_val == 1: record["house_dignity"] = "friend_house"
            elif total_val == 0: record["house_dignity"] = "neutral_house"
            elif total_val == -1: record["house_dignity"] = "enemy_house"
            elif total_val == -2: record["house_dignity"] = "worst_enemy_house"

    return {"planetary_positions": parsed_records}

if __name__ == "__main__":
    clipboard_data = pyperclip.paste()
    if not clipboard_data.strip():
        print("[!] Clipboard is empty. Copy JHora data first.")
    else:
        result_json = clean_and_parse_planets(clipboard_data)
        print(json.dumps(result_json, indent=4))