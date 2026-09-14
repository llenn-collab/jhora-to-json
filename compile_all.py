import tkinter as tk
from tkinter import messagebox, filedialog
import pyperclip
import json
import os
import re
import copy

try: from parse_planets import clean_and_parse_planets
except ImportError: clean_and_parse_planets = None
try: from calculate_argala import compute_argala_matrix
except ImportError: compute_argala_matrix = None
try: from parse_avastha import clean_and_parse_avastha
except ImportError: clean_and_parse_avastha = None
try: from parse_yogas import clean_and_parse_yogas
except ImportError: clean_and_parse_yogas = None

try: from parse_aspects import clean_and_parse_aspects, AspectsApp
except ImportError:
    clean_and_parse_aspects = None
    AspectsApp = None

try: from parse_ashtakavarga import AshtakavargaApp
except ImportError: AshtakavargaApp = None
try: from parse_arudha import ArudhaApp
except ImportError: ArudhaApp = None

COLORS = {
    "bg": "#0F172A", "card": "#1E293B", "text": "#F8FAFC",
    "muted": "#94A3B8", "warning": "#F59E0B"
}

ZODIAC_ORDER = ["aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"]
RASI_LORDS = {
    "aries": "mars", "taurus": "venus", "gemini": "mercury", "cancer": "moon",
    "leo": "sun", "virgo": "mercury", "libra": "venus", "scorpio": "mars",
    "sagittarius": "jupiter", "capricorn": "saturn", "aquarius": "saturn", "pisces": "jupiter"
}

def deep_merge(dict1, dict2):
    for key, value in dict2.items():
        if isinstance(value, dict) and key in dict1 and isinstance(dict1[key], dict):
            deep_merge(dict1[key], value)
        else:
            dict1[key] = value
    return dict1

def normalize_aspect_values(aspect_data):
    # F-01: paste mode (clean_and_parse_aspects) stores bare floats; manual mode
    # stores {"strength", "relation"} objects. Unify to the object shape at
    # capture time so scoring (.get("strength")) and the merged JSON see a single
    # type. The paste parser itself is intentionally left untouched.
    for bucket in ("from_ascendant_to_houses", "planet_to_planet_aspects"):
        for receiver, casters in aspect_data.get(bucket, {}).items():
            for caster, value in list(casters.items()):
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    casters[caster] = {"strength": float(value), "relation": "neutral"}
    return aspect_data

# --- Doctrine constants (F-16 / TODO-17) --------------------------------
# Named for reviewability. Values are byte-identical to the inline literals
# the extraction below replaced — do not change without doctrine review.
CORE_PLANET_NAMES = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"]
BENEFIC_CASTERS = ["jupiter", "venus", "mercury", "moon"]
MALEFIC_CASTERS = ["saturn", "mars", "rahu", "ketu"]
GIVER_MAP = {"Su": "sun", "Mo": "moon", "Ma": "mars", "Me": "mercury", "Ju": "jupiter", "Ve": "venus", "Sa": "saturn", "Ra": "rahu", "Ke": "ketu", "Md": "maandi"}
BAV_ROW_PLANETS = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "lagna"]
CONJUNCTION_DEGREES = 2.0
ASPECT_STRONG_MIN = 60
STATUS_ACTIVE_MIN = 70
STATUS_DORMANT_MIN = 40
BAV_HIGH_MIN = 5
BAV_LOW_MAX = 2
SAV_HIGH_MIN = 30
SAV_LOW_MAX = 25
ASPECT_KEY_RE = re.compile(r"house_\d{1,2}(?:_[a-z]+)?")

# --- Pure merge helpers (F-14 / TODO-16) ---------------------------------
# Extracted verbatim from MasterCompilerApp._compile_and_save_impl: plain
# dicts in, plain data out — no Tk, no self. Loop and append order are
# preserved so the merged JSON stays byte-identical.

def get_sign_for_house(lagna_idx, house_num):
    return ZODIAC_ORDER[(lagna_idx + house_num - 1) % 12]

def extract_degrees(long_str):
    if not long_str: return None
    match = re.search(r"(\d+)°\s*(\d+)'(?:\s*([\d.]+)\")?", long_str)
    if match:
        deg = int(match.group(1))
        mnt = int(match.group(2))
        sec = float(match.group(3)) if match.group(3) else 0.0
        return deg + (mnt / 60.0) + (sec / 3600.0)
    return None

def scaffold_signs(signs, varga_name, lagna_idx):
    for i, sign in enumerate(ZODIAC_ORDER):
        if sign not in signs: signs[sign] = {}
        h_num = (i - lagna_idx) % 12 + 1
        signs[sign][f"{varga_name}_house_number"] = h_num
        signs[sign][f"{varga_name}_house_lord"] = RASI_LORDS[sign].lower()
        signs[sign][f"{varga_name}_occupants"] = []

def attach_positions(payload, varga_name, positions, core_planet_names):
    for p_data in positions:
        name = p_data.get("body", "").lower()
        sign = p_data.get("rasi", "").lower()
        if not sign: continue

        if name in core_planet_names:
            payload["signs"][sign][f"{varga_name}_occupants"].append(name)
            if name not in payload["planets"]: payload["planets"][name] = {}

            varga_block = {
                f"{varga_name}_placement": {
                    "longitude": p_data.get("longitude"),
                    "sign": sign,
                    "house": p_data.get("house"),
                    "dignity": p_data.get("house_dignity", "neutral_house")
                }
            }

            # Strict checking of tags to prevent NULL output
            if p_data.get("special_dignity"):
                varga_block[f"{varga_name}_placement"]["special_dignity"] = p_data.get("special_dignity")
            if p_data.get("upachaya_effect"):
                varga_block[f"{varga_name}_placement"]["upachaya_effect"] = p_data.get("upachaya_effect")
            if p_data.get("is_retrograde"):
                varga_block[f"{varga_name}_placement"]["is_retrograde"] = True

            deep_merge(payload["planets"][name], varga_block)
        elif name != "lagna":
            if f"{varga_name}_special_points" not in payload["signs"][sign]:
                payload["signs"][sign][f"{varga_name}_special_points"] = []

            sp_payload = {
                "name": name,
                "longitude": p_data.get("longitude")
            }
            if p_data.get("upachaya_effect"):
                sp_payload["upachaya_effect"] = p_data.get("upachaya_effect")

            payload["signs"][sign][f"{varga_name}_special_points"].append(sp_payload)

def resolve_conjunctions_and_truncate(payload, varga_name, warnings):
    # G-01 FROZEN ORDER: the conjunction math runs on full-precision longitudes
    # BEFORE any string truncation. Do not reorder.
    for sign, sign_data in payload["signs"].items():
        special_points = sign_data.get(f"{varga_name}_special_points", [])
        occupants = sign_data.get(f"{varga_name}_occupants", [])

        if special_points:
            occ_longs = {}
            for occ in occupants:
                varga_block = payload["planets"].get(occ, {}).get(f"{varga_name}_placement", {})
                deg = extract_degrees(varga_block.get("longitude", ""))
                if deg is not None: occ_longs[occ] = deg

            sp_longs = {}
            for sp in special_points:
                deg = extract_degrees(sp.get("longitude", ""))
                if deg is None:
                    continue
                # F-21: a duplicate name used to silently overwrite the first entry.
                if sp["name"] in sp_longs:
                    warnings.append(f"Special point name collision: '{sp['name']}' (duplicate row; first occurrence kept)")
                    continue
                sp_longs[sp["name"]] = deg

            for sp in special_points:
                sp_name = sp["name"]
                sp_deg = sp_longs.get(sp_name)
                if sp_deg is not None:
                    conjuncts = []
                    # Check against Core Planets
                    for occ, occ_deg in occ_longs.items():
                        if abs(sp_deg - occ_deg) <= CONJUNCTION_DEGREES:
                            conjuncts.append(occ)
                    # Check against other Special Points
                    for other_sp, other_deg in sp_longs.items():
                        if sp_name != other_sp and abs(sp_deg - other_deg) <= CONJUNCTION_DEGREES:
                            conjuncts.append(other_sp)

                    if conjuncts:
                        sp["conjuncting_planets"] = conjuncts

        for occ in occupants:
            varga_block = payload["planets"].get(occ, {}).get(f"{varga_name}_placement", {})
            raw_long = varga_block.get("longitude", "")
            if raw_long:
                match = re.search(r"(\d+)°\s*(\d+)'", raw_long)
                if match:
                    varga_block["longitude"] = f"{match.group(1)}° {match.group(2)}'"

        for sp in special_points:
            raw_long = sp.get("longitude", "")
            if raw_long:
                match = re.search(r"(\d+)°", raw_long)
                if match:
                    sp["longitude"] = f"{match.group(1)}°"

def attach_avasthas(payload, varga_name, avasthas, core_planet_names):
    for av in avasthas:
        name = av.get("body", "").lower()
        if name in core_planet_names and name in payload["planets"]:
            payload["planets"][name][f"{varga_name}_avastha_alertness"] = av.get("alertness")
            if av.get("age"):
                payload["planets"][name][f"{varga_name}_avastha_age"] = av.get("age")
            if av.get("moods"):
                payload["planets"][name][f"{varga_name}_avastha_moods"] = av.get("moods")

def attach_aspects(payload, varga_name, aspects, lagna_idx, core_planet_names, warnings):
    p2p_aspects = aspects.get("planet_to_planet_aspects", {})
    for receiver, casters in p2p_aspects.items():
        name = receiver.replace("_receives_aspects", "").lower()
        if name in core_planet_names and name in payload["planets"]:
            payload["planets"][name][f"{varga_name}_aspects_received"] = casters

    asc_aspects = aspects.get("from_ascendant_to_houses", {})
    for key, casters in asc_aspects.items():
        # F-22: a malformed key used to crash the compile with a ValueError.
        if not ASPECT_KEY_RE.fullmatch(key):
            warnings.append(f"Skipped malformed aspect key: '{key}'")
            continue
        parts = key.split("_")
        h_num = int(parts[1])
        sign_name = parts[2].lower() if len(parts) >= 3 else get_sign_for_house(lagna_idx, h_num)
        if sign_name in payload["signs"]:
            payload["signs"][sign_name][f"{varga_name}_aspects_received"] = casters

def attach_bav(payload, varga_name, ashtakavarga):
    sav = ashtakavarga.get("samudayashtakavarga", {})
    bav = ashtakavarga.get("bhinnashtakavarga", {})
    for sign in ZODIAC_ORDER:
        if sign in sav:
            payload["signs"][sign][f"{varga_name}_sav"] = sav[sign]
            payload["signs"][sign][f"{varga_name}_bav"] = {}
            for p in BAV_ROW_PLANETS:
                if p in bav and sign in bav[p]:
                    payload["signs"][sign][f"{varga_name}_bav"][p] = bav[p][sign]

def score_planet(payload, varga_name, p_name, core_planet_names):
    if p_name not in payload["planets"]: return 100, ""

    placement = payload["planets"][p_name].get(f"{varga_name}_placement", {})
    if not placement: return 100, ""

    sign = placement.get("sign")
    house = placement.get("house")
    dignity = placement.get("dignity")
    special_dignity = placement.get("special_dignity")
    has_upachaya = "upachaya_effect" in placement

    score = 100
    reasons = [f"{p_name.capitalize()}"]

    # 1. Avastha Assessment
    avastha = payload["planets"][p_name].get(f"{varga_name}_avastha_alertness", "").lower()
    if "jaagrita" in avastha or "awake" in avastha:
        score += 10; reasons.append("Awake (+10)")
    elif "swapna" in avastha or "dreaming" in avastha:
        score -= 20; reasons.append("Dreaming (-20)")
    elif "sushupta" in avastha or "asleep" in avastha:
        score -= 40; reasons.append("Asleep (-40)")

    # 2. Local Dignity Assessment
    if special_dignity in ["exalted", "moolatrikona"]:
        score += 20; reasons.append(f"{special_dignity.capitalize()} (+20)")
    elif special_dignity == "debilitated":
        score -= 40; reasons.append("Debilitated (-40)")
    else:
        # F-08: special dignity SUPPRESSES the house-dignity deltas (no double
        # penalty) — a debilitated planet in a worst-enemy sign scores -40, not -60.
        if dignity == "own_house": score += 10; reasons.append("Own House (+10)")
        elif dignity in ["good_friend_house", "friend_house"]: score += 5; reasons.append("Friendly Sign (+5)")
        elif dignity in ["worst_enemy_house", "enemy_house"]: score -= 20; reasons.append("Enemy Sign (-20)")

    # 3. House Placement & Upachaya Turnaround
    if house in [1, 4, 5, 7, 9, 10]:
        score += 10; reasons.append(f"In {house}H Kendra/Trikona (+10)")
    elif house in [6, 8, 12]:
        if has_upachaya and house == 6:
            score += 15; reasons.append("In 6H with Upachaya Turnaround (+15)")
        else:
            score -= 30; reasons.append(f"In {house}H Dusthana (-30)")
    elif house in [3, 11] and has_upachaya:
        score += 15; reasons.append(f"In {house}H with Upachaya Turnaround (+15)")

    # 4. Dispositor (Landlord) Strength
    dispositor = payload["signs"].get(sign, {}).get(f"{varga_name}_house_lord")
    if dispositor and dispositor in payload["planets"]:
        disp_placement = payload["planets"][dispositor].get(f"{varga_name}_placement", {})
        disp_house = disp_placement.get("house")
        disp_spec_dig = disp_placement.get("special_dignity")
        disp_dig = disp_placement.get("dignity")

        if disp_spec_dig in ["exalted", "moolatrikona"] or disp_dig == "own_house":
            score += 10; reasons.append(f"Strong Dispositor {dispositor.capitalize()} (+10)")
        elif disp_spec_dig == "debilitated":
            score -= 20; reasons.append(f"Debilitated Dispositor {dispositor.capitalize()} (-20)")

        if disp_house in [6, 8, 12] and not "upachaya_effect" in disp_placement:
            score -= 10; reasons.append(f"Dispositor in Dusthana (-10)")

    # 5. Ashtakavarga Validation
    bav = payload["signs"].get(sign, {}).get(f"{varga_name}_bav", {}).get(p_name)
    sav = payload["signs"].get(sign, {}).get(f"{varga_name}_sav")
    if bav is not None:
        if bav >= BAV_HIGH_MIN: score += 10; reasons.append(f"High BAV {bav} (+10)")
        elif bav <= BAV_LOW_MAX: score -= 10; reasons.append(f"Low BAV {bav} (-10)")
    if sav is not None:
        if sav >= SAV_HIGH_MIN: score += 10; reasons.append(f"High SAV {sav} (+10)")
        elif sav < SAV_LOW_MAX: score -= 10; reasons.append(f"Low SAV {sav} (-10)")

    # 6. Nodal & Shadow Point Afflictions (With Upachaya Resilience check)
    sign_data = payload["signs"].get(sign, {})
    occupants = sign_data.get(f"{varga_name}_occupants", [])
    for node in ["rahu", "ketu"]:
        if node in occupants and node != p_name:
            node_placement = payload["planets"].get(node, {}).get(f"{varga_name}_placement", {})
            if "upachaya_effect" in node_placement:
                score += 10; reasons.append(f"Conjunct {node.capitalize()} (Affliction reversed by Upachaya +10)")
            else:
                score -= 20; reasons.append(f"Conjunct {node.capitalize()} (-20)")

    special_pts = sign_data.get(f"{varga_name}_special_points", [])
    for sp in special_pts:
        if p_name in sp.get("conjuncting_planets", []):
            if "upachaya_effect" in sp:
                score += 10; reasons.append(f"Conjunct {sp['name'].capitalize()} (Affliction reversed by Upachaya +10)")
            else:
                score -= 20; reasons.append(f"Conjunct {sp['name'].capitalize()} (-20)")

    # 7. Aspects Received (Drishti) — F-09: the sun is in neither caster list
    # and deliberately scores 0 on received aspects (owner-confirmed 2026-09-15).
    aspects = payload["planets"][p_name].get(f"{varga_name}_aspects_received", {})
    for caster, data in aspects.items():
        strength = data.get("strength", 0)
        if strength >= ASPECT_STRONG_MIN:
            if caster in BENEFIC_CASTERS:
                score += 15; reasons.append(f"Strong Benefic Aspect from {caster.capitalize()} (+15)")
            elif caster in MALEFIC_CASTERS:
                caster_placement = payload["planets"].get(caster, {}).get(f"{varga_name}_placement", {})
                if "upachaya_effect" in caster_placement:
                    score += 5; reasons.append(f"Aspect from {caster.capitalize()} (Mitigated by Upachaya +5)")
                else:
                    score -= 15; reasons.append(f"Strong Malefic Aspect from {caster.capitalize()} (-15)")

    return score, "[" + ", ".join(reasons[1:]) + "]"

def classify_yogas(payload, varga_name, raw_yogas, planet_evaluations, core_planet_names, giver_map):
    """Attaches classified yogas to their core-planet givers.
    F-20: the payload is deep-copied per planet (no shared reference aliasing).
    TODO-09: yogas with no core-planet givers are returned, not silently dropped."""
    unattached = []
    for yoga_key, yoga_data in raw_yogas.items():
        givers_str = yoga_data.get("yoga_givers", "")
        involved_planets = []

        for abbr, full_name in giver_map.items():
            if full_name in payload["planets"] and re.search(rf'\b{abbr}\b', givers_str):
                involved_planets.append(full_name)

        if not involved_planets:
            unattached.append(yoga_key)
            continue

        # Calculate aggregate yoga strength
        total_score = sum(planet_evaluations[p][0] for p in involved_planets)
        avg_score = total_score / len(involved_planets)

        if avg_score >= STATUS_ACTIVE_MIN: status = "Active"
        elif avg_score >= STATUS_DORMANT_MIN: status = "Dormant"
        else: status = "Asleep"

        analysis_text = f"Combined Strength Score: {avg_score:.1f}/100. "
        analysis_text += " | ".join(f"{p.capitalize()}: {planet_evaluations[p][1]}" for p in involved_planets if planet_evaluations[p][1] != "[]")

        yoga_payload = copy.deepcopy(yoga_data)
        yoga_payload["status"] = status
        yoga_payload["technical_analysis"] = analysis_text
        yoga_payload["active"] = (status == "Active")

        for p in involved_planets:
            if f"{varga_name}_yogas" not in payload["planets"][p]:
                payload["planets"][p][f"{varga_name}_yogas"] = {}
            payload["planets"][p][f"{varga_name}_yogas"][yoga_key] = copy.deepcopy(yoga_payload)

    return unattached

def attach_argala(payload, varga_name, argala_data, lagna_idx):
    for house_str, data in argala_data.items():
        h_num = int(house_str.split("_")[1])
        sign_name = get_sign_for_house(lagna_idx, h_num)
        if sign_name in payload["signs"]:
            working = data.get("working_argala", {})
            if working: payload["signs"][sign_name][f"{varga_name}_effective_argala"] = working

def attach_arudhas(payload, varga_name, arudhas_data, lagna_idx):
    for category, mappings in arudhas_data.items():
        for label, h_num in mappings.items():
            sign_name = get_sign_for_house(lagna_idx, h_num)
            cat_key = f"{varga_name}_{category}"
            if sign_name in payload["signs"]:
                if cat_key not in payload["signs"][sign_name]:
                    payload["signs"][sign_name][cat_key] = []
                payload["signs"][sign_name][cat_key].append(label.upper())

def strip_empty_occupants(payload, varga_name):
    for sign in ZODIAC_ORDER:
        if not payload["signs"][sign].get(f"{varga_name}_occupants"):
            payload["signs"][sign].pop(f"{varga_name}_occupants", None)

def build_master_payload(d1_master_data, raw_parsed_data, varga_name, core_planet_names, warnings):
    """Pure orchestration of the merge doctrine (extracted from the Tk app).
    Mutates d1_master_data exactly as the original self-heal did.
    Returns (final_payload, planet_evaluations, unattached_yoga_keys)."""
    # Self-Healing Routine: Re-nest lost planets if the JSON template had a syntax error
    if "planets" not in d1_master_data:
        d1_master_data["planets"] = {}

    for p_name in core_planet_names:
        if p_name in d1_master_data and p_name not in d1_master_data["planets"]:
            d1_master_data["planets"][p_name] = d1_master_data.pop(p_name)

    final_payload = {
        "planets": copy.deepcopy(d1_master_data.get("planets", {})),
        "signs": copy.deepcopy(d1_master_data.get("signs", {}))
    }

    lagna_sign = "aries"
    for p in raw_parsed_data.get("planets", []):
        if p.get("body", "").lower() == "lagna":
            lagna_sign = p.get("rasi", "aries").lower()
            break
    lagna_idx = ZODIAC_ORDER.index(lagna_sign) if lagna_sign in ZODIAC_ORDER else 0

    scaffold_signs(final_payload["signs"], varga_name, lagna_idx)
    attach_positions(final_payload, varga_name, raw_parsed_data.get("planets", []), core_planet_names)
    resolve_conjunctions_and_truncate(final_payload, varga_name, warnings)
    attach_avasthas(final_payload, varga_name, raw_parsed_data.get("avasthas", []), core_planet_names)
    attach_aspects(final_payload, varga_name, raw_parsed_data.get("aspects", {}), lagna_idx, core_planet_names, warnings)
    attach_bav(final_payload, varga_name, raw_parsed_data.get("ashtakavarga", {}))

    # Evaluate all planets first to establish the baseline matrix
    planet_evaluations = {}
    for p_name in core_planet_names:
        planet_evaluations[p_name] = score_planet(final_payload, varga_name, p_name, core_planet_names)

    unattached_yogas = classify_yogas(final_payload, varga_name, raw_parsed_data.get("yogas", {}), planet_evaluations, core_planet_names, GIVER_MAP)
    attach_argala(final_payload, varga_name, raw_parsed_data.get("argala", {}), lagna_idx)
    attach_arudhas(final_payload, varga_name, raw_parsed_data.get("arudhas", {}), lagna_idx)
    strip_empty_occupants(final_payload, varga_name)

    return final_payload, planet_evaluations, unattached_yogas

class MasterCompilerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JHora Master Varga Compiler")
        self.root.geometry("500x750")
        self.root.configure(bg=COLORS["bg"])
        self.root.resizable(False, False)
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        self.root.focus_force()

        self.d1_master_data = None
        self.varga_name = ""
        self.raw_parsed_data = {
            "planets": {}, "argala": {}, "avasthas": {},
            "aspects": {}, "yogas": {}, "ashtakavarga": {}, "arudhas": {}
        }

        self.steps = [
            {"id": "planets", "label": "1. Paste Planets & Calc Argala", "action": self.ingest_planets},
            {"id": "avastha", "label": "2. Paste Avasthas (Moods)", "action": self.ingest_avasthas},
            {"id": "aspects", "label": "3. Launch Aspects UI", "action": self.launch_aspects_ui},
            {"id": "yogas", "label": "4. Paste Yogas", "action": self.ingest_yogas},
            {"id": "ashtakavarga", "label": "5. Launch Ashtakavarga UI", "action": self.launch_bav_ui},
            {"id": "arudha", "label": "6. Launch Arudha Padas UI", "action": self.launch_arudha_ui}
        ]

        self.step_buttons = {}
        self.create_ui()

    def create_ui(self):
        tk.Label(self.root, text="Varga Chart Compiler", font=("Helvetica", 18, "bold"), bg=COLORS["bg"], fg=COLORS["text"]).pack(pady=(20, 5))

        self.lbl_d1 = tk.Label(self.root, text="🔴 No D1 Master Profile Loaded", font=("Helvetica", 11, "bold"), bg=COLORS["bg"], fg=COLORS["warning"])
        self.lbl_d1.pack(pady=5)

        tk.Button(
            self.root, text="Load D1 Master JSON", command=self.load_d1_profile,
            font=("Helvetica", 12, "bold"), width=20
        ).pack(pady=(0, 15))

        self.frame = tk.Frame(self.root, bg=COLORS["card"], padx=25, pady=20, relief="solid", bd=1)
        self.frame.pack(fill="both", expand=True, padx=30, pady=10)

        for step in self.steps:
            btn = tk.Button(
                self.frame, text=step["label"], command=step["action"],
                font=("Helvetica", 12, "bold"), pady=5, cursor="hand2", state="disabled"
            )
            btn.pack(fill="x", pady=8)
            self.step_buttons[step["id"]] = btn

        self.btn_compile = tk.Button(
            self.root, text="Compile Master JSON", command=self.compile_and_save,
            font=("Helvetica", 14, "bold"), pady=10, state="disabled"
        )
        self.btn_compile.pack(fill="x", padx=30, pady=20)

    def load_d1_profile(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")], title="Select D1 Master Profile")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.d1_master_data = json.load(f)

                import tkinter.simpledialog as sd
                self.varga_name = sd.askstring("Varga Name", "Enter the Varga prefix (e.g., 'D9'):")
                if not self.varga_name:
                    # F-19: D1 is now in memory but the prefix is missing — make
                    # the half-loaded state visible instead of the stale red label.
                    self.lbl_d1.config(text=f"🟡 D1 loaded — varga prefix pending: {os.path.basename(file_path)}", fg=COLORS["warning"])
                    self.show_info("Varga prefix missing.\nThe D1 data is loaded; press Load D1 and enter the prefix.")
                    return

                filename = os.path.basename(file_path)
                self.lbl_d1.config(text=f"🟢 D1 Loaded: {filename} | Target: {self.varga_name}", fg="#10B981")
                for btn in self.step_buttons.values(): btn.config(state="normal")
            except Exception as e:
                self.show_error(f"Failed to load D1 Profile: {str(e)}")

    def mark_complete(self, step_id):
        self.step_buttons[step_id].config(text=f"{self.step_buttons[step_id]['text']}  ✓", state="disabled")
        if all(btn['state'] == 'disabled' for btn in self.step_buttons.values()):
            self.btn_compile.config(state="normal")

    def show_error(self, msg):
        err = tk.Toplevel(self.root)
        err.title("Notice")
        err.attributes('-topmost', True)
        tk.Label(err, text=msg, padx=20, pady=20).pack()
        tk.Button(err, text="OK", command=err.destroy, width=10).pack(pady=(0, 20))

    def show_info(self, msg):
        # F-17: success/info modals are visually distinct from error modals.
        info = tk.Toplevel(self.root)
        info.title("✓ Success")
        info.attributes('-topmost', True)
        tk.Label(info, text=msg, padx=20, pady=20).pack()
        tk.Button(info, text="OK", command=info.destroy, width=10).pack(pady=(0, 20))

    def ingest_planets(self):
        # F-13: standard notice instead of a TypeError when a module is missing.
        if not clean_and_parse_planets: return self.show_error("Planets module missing.")
        if not compute_argala_matrix: return self.show_error("Argala module missing.")
        try:
            raw = pyperclip.paste()
            # F-11: an empty or unparseable clipboard must not mark the step complete.
            if not raw or not raw.strip():
                return self.show_error("Planet Parse Failed.\nClipboard is empty. Copy the JHora planet table first.")
            parsed = clean_and_parse_planets(raw)
            positions = parsed.get("planetary_positions", [])
            if not positions:
                return self.show_error("Planet Parse Failed.\nNo planet rows found in the clipboard text.")
            self.raw_parsed_data["planets"] = positions
            argala_out = compute_argala_matrix(parsed)
            self.raw_parsed_data["argala"] = argala_out.get("argala_analysis", {})
            self.mark_complete("planets")
        except Exception as e: self.show_error(f"Planet Parse Failed.\n{str(e)}")

    def ingest_avasthas(self):
        # F-13: standard notice instead of a TypeError when a module is missing.
        if not clean_and_parse_avastha: return self.show_error("Avasthas module missing.")
        try:
            raw = pyperclip.paste()
            # F-11: an empty or unparseable clipboard must not mark the step complete.
            if not raw or not raw.strip():
                return self.show_error("Avastha Parse Failed.\nClipboard is empty. Copy the JHora avastha table first.")
            avasthas = clean_and_parse_avastha(raw).get("avasthas", [])
            if not avasthas:
                return self.show_error("Avastha Parse Failed.\nNo avastha rows found in the clipboard text.")
            self.raw_parsed_data["avasthas"] = avasthas
            self.mark_complete("avastha")
        except Exception as e: self.show_error(f"Avastha Parse Failed.\n{str(e)}")

    def launch_aspects_ui(self):
        if not AspectsApp: return self.show_error("Aspects App module missing.")
        top = tk.Toplevel(self.root)
        app = AspectsApp(top)

        def hijacked_export():
            if hasattr(app, 'mode') and app.mode == "manual": app.compile_manual_data()
            if app.final_output:
                # F-01: normalize paste-mode floats to the object shape at capture.
                self.raw_parsed_data["aspects"] = normalize_aspect_values(app.final_output.get("aspect_strengths", {}))
            top.destroy()
            self.mark_complete("aspects")

        app.export_json = hijacked_export

    def ingest_yogas(self):
        # F-13: standard notice instead of a TypeError when a module is missing.
        if not clean_and_parse_yogas: return self.show_error("Yogas module missing.")
        try:
            raw = pyperclip.paste()
            # F-11: an empty or unparseable clipboard must not mark the step complete.
            if not raw or not raw.strip():
                return self.show_error("Yoga Parse Failed.\nClipboard is empty. Copy the JHora yoga table first.")
            yogas = clean_and_parse_yogas(raw).get("yogas", {})
            if not yogas:
                return self.show_error("Yoga Parse Failed.\nNo yoga rows found in the clipboard text.")
            self.raw_parsed_data["yogas"] = yogas
            self.mark_complete("yogas")
        except Exception as e: self.show_error(f"Yoga Parse Failed.\n{str(e)}")

    def launch_bav_ui(self):
        if not AshtakavargaApp: return self.show_error("Ashtakavarga App module missing.")
        top = tk.Toplevel(self.root)
        app = AshtakavargaApp(top)

        def hijacked_export():
            app.final_output = {
                "bhinnashtakavarga": app.bav_data,
                "samudayashtakavarga": app.calculate_sav()
            }
            self.raw_parsed_data["ashtakavarga"] = app.final_output
            top.destroy()
            self.mark_complete("ashtakavarga")

        app.export_json = hijacked_export

    def launch_arudha_ui(self):
        if not ArudhaApp: return self.show_error("Arudha App module missing.")
        top = tk.Toplevel(self.root)
        app = ArudhaApp(top)

        def hijacked_export():
            final_payload = {}
            for screen_id, items_dict in app.vars.items():
                screen_data = {}
                for item, var_obj in items_dict.items():
                    val = var_obj.get()
                    if val != "None":
                        screen_data[item] = int(val)
                if screen_data:
                    final_payload[screen_id] = screen_data

            self.raw_parsed_data["arudhas"] = final_payload
            top.destroy()
            self.mark_complete("arudha")

        app.export_json = hijacked_export

    def compile_and_save(self):
        # F-01: any compile failure surfaces as a modal, never a raw traceback —
        # a traceback would lose the whole session's captured data.
        try:
            self._compile_and_save_impl()
        except Exception as e:
            self.show_error(f"Compile Failed.\n{str(e)}")

    def _compile_and_save_impl(self):
        warnings = []
        final_payload, _evaluations, unattached_yogas = build_master_payload(
            self.d1_master_data, self.raw_parsed_data, self.varga_name, CORE_PLANET_NAMES, warnings)

        export_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=f"Master_Merged_{self.varga_name}.json",
            filetypes=[("JSON Files", "*.json")],
            title="Save Merged Final JSON"
        )
        if export_path:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(final_payload, f, indent=4)
            # F-12: make the ingested content visible in the success notice so a
            # sparse compile is obvious at a glance.
            aspect_data = self.raw_parsed_data.get("aspects", {})
            ingested = (
                f"Rows ingested: {len(self.raw_parsed_data.get('planets', []))} planet rows, "
                f"{len(self.raw_parsed_data.get('avasthas', []))} avasthas, "
                f"{len(aspect_data.get('planet_to_planet_aspects', {})) + len(aspect_data.get('from_ascendant_to_houses', {}))} aspect receivers, "
                f"{len(self.raw_parsed_data.get('yogas', {}))} yogas, "
                f"{len(self.raw_parsed_data.get('ashtakavarga', {}).get('samudayashtakavarga', {}))} SAV signs, "
                f"{sum(len(m) for m in self.raw_parsed_data.get('arudhas', {}).values())} arudha entries"
            )
            notice = f"SUCCESS!\nMaster JSON compiled and safely saved to:\n{export_path}\n{ingested}"
            # TODO-09: make the previously silent G-19 drop visible.
            if unattached_yogas:
                notice += f"\n{len(unattached_yogas)} yoga(s) not attached (no core planet givers): {', '.join(unattached_yogas)}"
            if warnings:
                notice += f"\nWarnings: {'; '.join(warnings)}"
            self.show_info(notice)
            self.root.quit()
        else:
            # F-18: a cancelled save is no longer silent — all steps are still
            # complete, so re-running Compile is a safe retry.
            self.show_info("Save cancelled.\nPress Compile again to retry.")

if __name__ == "__main__":
    root = tk.Tk()
    app = MasterCompilerApp(root)
    root.mainloop()
