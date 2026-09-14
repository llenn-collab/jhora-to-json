import json
import re
import pyperclip

# Safely import pipeline dependency
try:
    from parse_planets import clean_and_parse_planets
except ImportError:
    clean_and_parse_planets = None

CORE_PLANETS = {"sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"}
MALEFICS = {"sun", "mars", "saturn", "rahu", "ketu"}

def get_quarter(longitude_str):
    match = re.search(r"(\d+)°\s*(\d+)'\s*([\d.]+)", longitude_str)
    if match:
        deg = int(match.group(1))
        mnt = int(match.group(2))
        sec = float(match.group(3))

        total_deg = deg + (mnt / 60.0) + (sec / 3600.0)

        if total_deg < 7.5: return 1
        elif total_deg < 15.0: return 2
        elif total_deg < 22.5: return 3
        else: return 4
    return 1

def compute_argala_matrix(planetary_data):
    positions = planetary_data.get("planetary_positions", [])
    occupied_houses = {h: {} for h in range(1, 13)}

    for pos in positions:
        body = pos.get("body", "").lower()
        house = pos.get("house")
        longitude = pos.get("longitude", "")

        if body in CORE_PLANETS and house:
            quarter = get_quarter(longitude)
            occupied_houses[house][body] = {
                "quarter": quarter,
                "is_malefic": body in MALEFICS,
                "longitude": longitude
            }

    argala_results = {}

    for target_house in range(1, 13):
        house_key = f"house_{target_house}"
        target_occupants = occupied_houses[target_house]
        is_reverse = "rahu" in target_occupants or "ketu" in target_occupants
        eff_houses = {i: [] for i in range(1, 13)}

        for src_house in range(1, 13):
            planets_in_src = occupied_houses[src_house]
            if not planets_in_src: continue

            fwd_rel = (src_house - target_house) % 12 + 1
            if is_reverse and fwd_rel > 1: eff_rel = 14 - fwd_rel
            else: eff_rel = fwd_rel

            for p_name, p_data in planets_in_src.items():
                p_copy = dict(p_data)
                p_copy["name"] = p_name
                p_copy["source_house"] = src_house
                eff_houses[eff_rel].append(p_copy)

        def resolve_axis(argalas, virodhargalas):
            working_argalas = []
            for a in argalas:
                is_blocked = False
                for v in virodhargalas:
                    if a["quarter"] + v["quarter"] == 5:
                        is_blocked = True
                        break
                if not is_blocked:
                    working_argalas.append(a)
            return working_argalas

        working_argalas_json = {}

        def get_type_label(base_type):
            return f"{base_type} (reverse)" if is_reverse else base_type

        # This structures the JSON natively into the requested "9H": {"planets": [], "type": ...} format
        def add_to_results(planet_list, argala_type):
            for p in planet_list:
                house_key = f"{p['source_house']}H"
                if house_key not in working_argalas_json:
                    working_argalas_json[house_key] = {
                        "planets": [],
                        "type": get_type_label(argala_type)
                    }
                # Prevent any accidental duplicates
                if p["name"] not in working_argalas_json[house_key]["planets"]:
                    working_argalas_json[house_key]["planets"].append(p["name"])

        working_2 = resolve_axis(eff_houses[2], eff_houses[12])
        add_to_results(working_2, "dhana")

        working_4 = resolve_axis(eff_houses[4], eff_houses[10])
        add_to_results(working_4, "subha")

        secondary_argalas = [p for p in eff_houses[5] if p["name"] != "ketu"] + \
                            [p for p in eff_houses[9] if p["name"] == "ketu"]
        secondary_virodhargalas = [p for p in eff_houses[9] if p["name"] != "ketu"] + \
                                  [p for p in eff_houses[5] if p["name"] == "ketu"]

        working_5_9 = resolve_axis(secondary_argalas, secondary_virodhargalas)
        add_to_results(working_5_9, "vidya")

        benefics_in_3 = [p for p in eff_houses[3] if not p["is_malefic"]]
        malefics_in_3 = [p for p in eff_houses[3] if p["is_malefic"]]

        working_11 = resolve_axis(eff_houses[11], benefics_in_3)
        add_to_results(working_11, "labha")

        if len(malefics_in_3) >= 3:
            add_to_results(malefics_in_3, "vipreet_argala")
        elif len(malefics_in_3) > 0:
            add_to_results(malefics_in_3, "3rd_house_special")

        # Fix: Now sums the length of the planets arrays since the keys are houses
        total_argala_planets = sum(len(h_data["planets"]) for h_data in working_argalas_json.values())
        if total_argala_planets == 0: strength_by_count = "none"
        elif total_argala_planets == 1: strength_by_count = "limited"
        elif total_argala_planets == 2: strength_by_count = "medium"
        else: strength_by_count = "excellent"

        argala_results[house_key] = {
            "is_reverse_counted": is_reverse,
            "working_argala": working_argalas_json,
            "argala_strength_by_count": strength_by_count
        }

    return {"argala_analysis": argala_results}

if __name__ == "__main__":
    clipboard_data = pyperclip.paste()
    if not clipboard_data.strip():
        print("[!] Clipboard empty. Copy your raw JHora longitudinal grid first.")
    elif clean_and_parse_planets:
        parsed_planets = clean_and_parse_planets(clipboard_data)
        matrix = compute_argala_matrix(parsed_planets)
        print(json.dumps(matrix, indent=4))
