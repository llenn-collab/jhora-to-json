"""Audit & regression suite for jhora-to-json (headless; tkinter stubbed).

Milestone A (TODO-01..05, 2026-09-15): capture-time aspect normalization,
compile wrapper modal, ingest guards, success counts — T9/T10/T15-T17.
Milestone B (TODO-06..09, 2026-09-15): get_quarter float fix (T14/T20), yoga
pass hardening (T14), G-19 unattached-yoga notice (T9).
Milestone C (TODO-16..19/21/22, 2026-09-15): extracted pure helpers verified
byte-identical via golden JSON hashes; per-planet yoga deepcopies (T9),
cancelled-save notice (T21), malformed aspect key / SP collision guards (T22),
standalone clipboard guards (T23).
Run:  python tests/audit_smoke.py   (in-repo copy, canonical)
"""
import sys, os, types, json, traceback, re as _re, ast

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root (tests/..)
sys.path.insert(0, REPO)
os.makedirs("/tmp/jhora_audit", exist_ok=True)

tk_stub = types.ModuleType("tkinter")
class _Fake:
    def __init__(self, *a, **k): pass
    def __call__(self, *a, **k): return _Fake()
    def __getattr__(self, name): return _Fake()
tk_stub.Tk = _Fake; tk_stub.Label = _Fake; tk_stub.Button = _Fake
tk_stub.Frame = _Fake; tk_stub.Toplevel = _Fake; tk_stub.StringVar = _Fake
tk_stub.END = "end"
tk_stub_msgbox = types.ModuleType("tkinter.messagebox")
tk_stub_filedlg = types.ModuleType("tkinter.filedialog")
tk_stub.messagebox = tk_stub_msgbox
tk_stub.filedialog = tk_stub_filedlg
sys.modules["tkinter"] = tk_stub
sys.modules["tkinter.messagebox"] = tk_stub_msgbox
sys.modules["tkinter.filedialog"] = tk_stub_filedlg

import parse_planets, calculate_argala, parse_avastha, parse_yogas, parse_aspects
import compile_all

PASS, FAIL = 0, 0
def check(name, cond, detail=""):
    global PASS, FAIL
    if cond: PASS += 1; print(f"  [ok] {name}")
    else: FAIL += 1; print(f"  [FAIL] {name} {detail}")

# =====================================================================
print("== T1: parse_planets — full table (lagna Ta) ==")
TABLE = (
    "\x00Body\x00            Longitude\n"
    "Lagna           08 Ta 33' 40\"\n"
    "Sun             10 Le 30' 0.00\"\n"
    "Moon            27 Pi 01' 45.3\"\n"
    "Mars (R)        22 Ar 50' 12.3\"\n"
    "Mercury         01 Vi 00' 00.0\"\n"
    "Jupiter         15 Ta 20' 0.0\"\n"
    "Venus           28 Li 01' 30.0\"\n"
    "Saturn          10 Ge 30' 10.0\"\n"
    "Rahu            05 Cn 15' 0.0\"\n"
    "Ketu            05 Cp 15' 0.0\"\n"
    "Maandi          12 Cn 03' 05.0\"\n"
    "Gulika          12 Le 00' 00.0\"\n"
    "Bhava Lagna     20 Cn 10' 00.0\"\n"
    "Yama Ghantaka   03 Sc 09' 00.0\"\n"
)
res = parse_planets.clean_and_parse_planets(TABLE)
recs = {r["body"]: r for r in res["planetary_positions"]}
check("14 records parsed", len(res["planetary_positions"]) == 14, str(len(res["planetary_positions"])))
check("lagna Ta h1", recs["lagna"]["rasi"] == "taurus" and recs["lagna"]["house"] == 1)
check("sun h4 MT own_house", recs["sun"]["house"] == 4 and recs["sun"].get("special_dignity") == "moolatrikona" and recs["sun"].get("house_dignity") == "own_house")
check("moon h11 friend_house", recs["moon"]["house"] == 11 and recs["moon"].get("house_dignity") == "friend_house")
check("mars (R) in body cell -> retrograde", recs["mars"].get("is_retrograde") is True)
check("mars own_house", recs["mars"].get("house_dignity") == "own_house")
check("mercury exalted (shadows MT)", recs["mercury"].get("special_dignity") == "exalted")
check("jupiter worst_enemy_house", recs["jupiter"].get("house_dignity") == "worst_enemy_house")
check("venus own_house", recs["venus"].get("house_dignity") == "own_house")
check("saturn good_friend_house", recs["saturn"].get("house_dignity") == "good_friend_house")
check("rahu h3 upachaya", recs["rahu"]["house"] == 3 and "upachaya_effect" in recs["rahu"])
check("ketu h9 no upachaya", recs["ketu"]["house"] == 9 and "upachaya_effect" not in recs["ketu"], str(recs.get("ketu")))
check("maandi h3 upachaya (upagraha)", "upachaya_effect" in recs["maandi"])
check("longitude keeps source decimals", recs["sun"]["longitude"] == "10° 30' 0.00\"", recs["sun"]["longitude"])
check("special points carry house (maandi h3)", recs["maandi"]["house"] == 3)

print("== T1b: (R) detection — body cell + post-coordinate (TODO-10, owner: additive) ==")
b = parse_planets.clean_and_parse_planets("Mars  22 Ar 50' 12.3\" (R)\n")["planetary_positions"][0]
check("after-coords (R) now detected (additive tolerance)", b.get("is_retrograde") is True, str(b))
b2 = parse_planets.clean_and_parse_planets("Mars (R)  22 Ar 50' 12.3\"\n")["planetary_positions"][0]
check("body-cell (R) still detected (contract intact)", b2.get("is_retrograde") is True, str(b2))
b3 = parse_planets.clean_and_parse_planets("Mars  22 Ar 50' 12.3\"\n")["planetary_positions"][0]
check("no (R) -> no flag (no false positives)", "is_retrograde" not in b3, str(b3))

print("== T2: no lagna row ==")
res2 = parse_planets.clean_and_parse_planets("Sun  10 Le 30' 0.0\"\nMoon 27 Pi 01' 45.3\"\n")
check("no house/house_dignity without lagna", all("house" not in r and "house_dignity" not in r for r in res2["planetary_positions"]))
check("special_dignity still computed without lagna", res2["planetary_positions"][0].get("special_dignity") == "moolatrikona")

print("== T5: calculate_argala (corrected house math) ==")
def P(lagna_sign, body, sign, deg_int):
    return {"body": body, "rasi": sign, "longitude": f"{int(deg_int)}° 00' 00.0\"",
            "house": (parse_planets.ZODIAC_ORDER.index(sign) - parse_planets.ZODIAC_ORDER.index(lagna_sign)) % 12 + 1}
def matrix(rows):
    return calculate_argala.compute_argala_matrix({"planetary_positions": [P("aries","lagna","aries",8)] + rows})["argala_analysis"]

# case 1: sun h2 q1 dhana; moon h12 q4 virodhargala (1+4=5 CANCEL); jupiter h4 q2 subha survives; mars h3 malefic special
m = matrix([P("aries","sun","taurus",1), P("aries","moon","pisces",28), P("aries","jupiter","cancer",10), P("aries","mars","gemini",5)])
h1 = m["house_1"]
check("cancellation: sun dhana gone (q1+q4=5)", "2H" not in h1["working_argala"], str(h1["working_argala"]))
check("subha survives: jupiter 4H", h1["working_argala"].get("4H", {}).get("type") == "subha")
check("1 malefic in 3H -> 3rd_house_special", h1["working_argala"].get("3H", {}).get("type") == "3rd_house_special")
check("strength medium (2 planets)", h1["argala_strength_by_count"] == "medium", h1["argala_strength_by_count"])

# case 2: quarter boundary 7.49 vs 7.5 (q1 vs q2) — 1+4 cancel vs 2+4 survive
ma = matrix([P("aries","sun","taurus",7), P("aries","moon","pisces",28)])   # 7° -> q1 -> cancel
mb = matrix([P("aries","sun","taurus",7), P("aries","moon","pisces",28), P("aries","venus","taurus",8)])  # 8° -> q2 -> survive (1+4? venus q2 + moon q4 = 6)
check("boundary: 7°0' sun q1 cancelled", "2H" not in ma["house_1"]["working_argala"], str(ma["house_1"]["working_argala"]))
check("boundary: 8°0' venus q2 survives (2+4=6)", "2H" in mb["house_1"]["working_argala"], str(mb["house_1"]["working_argala"]))

# case 3: reverse counting (rahu h8 scorpio; ketu h2 taurus)
m3 = matrix([P("aries","rahu","scorpio",20), P("aries","ketu","taurus",20), P("aries","mars","aquarius",10)])
h8 = m3["house_8"]
check("h8 is_reverse_counted", h8["is_reverse_counted"] is True)
# mars h11 (aquarius): fwd (11-8)%12+1 = 4 -> eff 14-4 = 10 -> virodhargala for subha. none subha.
# For target h8: who is eff 2 (dhana)? fwd = 14-2 = 12 -> src h12 (pisces). empty.
# eff 11 (labha)? fwd = 14-11 = 3 -> src h3 (gemini) empty.
check("h8 working argala empty (no eff-axis sources)", h8["working_argala"] == {}, str(h8["working_argala"]))
# verify reverse label: make something land on an axis: venus in capricorn h10: fwd (10-8)%12+1=3 -> eff 11 -> labha (reverse)
m4 = matrix([P("aries","rahu","scorpio",20), P("aries","ketu","taurus",20), P("aries","venus","capricorn",10)])
check("h8: venus fwd3 -> eff11 labha (reverse) from 10H", m4["house_8"]["working_argala"].get("10H", {}).get("type") == "labha (reverse)", str(m4["house_8"]["working_argala"]))

# case 4: ketu's dual role (non-reverse): ketu h9 eff9 = vidya GIVER; venus h9 eff9 = virodhargala; jupiter h5 eff5 blocked (q4+q1=5)
m5 = matrix([P("aries","ketu","sagittarius",1), P("aries","rahu","gemini",1), P("aries","venus","sagittarius",5), P("aries","jupiter","cancer",25)])
h1b = m5["house_1"]
check("ketu in eff-9 gives vidya (9H)", h1b["working_argala"].get("9H", {}).get("type") == "vidya" and "ketu" in h1b["working_argala"].get("9H", {}).get("planets", []), str(h1b["working_argala"]))
check("jupiter eff-5 vidya blocked by venus eff-9 (q4+q1=5)", "5H" not in h1b["working_argala"], str(h1b["working_argala"]))

print("== T6: parse_avastha ==")
av = parse_avastha.clean_and_parse_avastha(
    "\x00Planet\x00   Alertness\n"
    "Sun    Madya (Adult) Jaagrita (Awake) Hunger (Hunger) Thirst (Thirst)\n"
    "Moon   Vriddha (Old) Sushupta (Asleep)\n"
    "Mars   Baala (Child)\n")
s = next(a for a in av["avasthas"] if a["body"] == "sun")
check("sun positional contract", s == {"body": "sun", "age": "Madya", "alertness": "Awake", "moods": ["Hunger", "Thirst"]}, str(s))
check("1-pair row dropped", len(av["avasthas"]) == 2)
check("alertness case-insensitive matching possible", any(k in s["alertness"].lower() for k in ("awake",)))

print("== T7: parse_yogas 3 passes ==")
y1 = parse_yogas.clean_and_parse_yogas(
    "Yoga\tVarga\tYoga givers\tResults\tBrief def\n"
    "Gaja Kesari\tRasi\tMo Ju\tWealth\tRich kings\n"
    "Vipareeta Raja\tRasi\tSa\tEnemies fall\tDusthana lordship\n")
check("tab pass: name/givers/results(cols 0/2/3)", y1["yogas"].get("gaja_kesari_yoga") == {"active": True, "yoga_givers": "Mo Ju", "definition": "Wealth"}, str(y1.get("yogas", {}).get("gaja_kesari_yoga")))
check("tab pass: definition is Results column", y1["yogas"].get("vipareeta_raja_yoga", {}).get("definition") == "Enemies fall")
y2 = parse_yogas.clean_and_parse_yogas(
    "Yoga               Varga  Yoga givers  Results            Brief def\n"
    "Sunapha Yoga       Rasi   Mo           Wealth             Moon-Sun combo\n"
    "Shakata Yoga       Rasi   Sa Ve        Obstacle           Saturn-Venus\n")
check("fixed-width pass (header-anchored slicing)", y2["yogas"].get("sunapha_yoga", {}).get("yoga_givers") == "Mo" and y2["yogas"].get("shakata_yoga", {}).get("definition") == "Obstacle", str(y2))
y3 = parse_yogas.clean_and_parse_yogas(
    "Dhana Yoga  D-9 (D-9 x D-9)  Ju Sa  Wealth  Riches of the lord\n"
    "Naabhasa yoga  Rasi  Naabhasa yoga - throughout life  No results noted\n")
check("regex pass: D-9 token + givers", y3["yogas"].get("dhana_yoga", {}).get("yoga_givers") == "Ju Sa", str(y3))
check("Naabhasa special-case prefix", y3["yogas"].get("naabhasa_yoga", {}).get("yoga_givers") == "Naabhasa yoga - throughout life")
y4 = parse_yogas.clean_and_parse_yogas("Dhana Yoga  Rasi  Ju  A  x\nDhana Yoga  Rasi  Sa  B  y\n")
check("duplicate keys -> _2 suffix", list(y4["yogas"].keys()) == ["dhana_yoga", "dhana_yoga_2"])

print("== T8: parse_aspects paste parser ==")
ASP = (
    "Aspected Body    Longitude       Su    Mo    Ma    Me    Ju    Ve    Sa    Ra    Ke\n"
    "Lagna            08 Ta 33' 40\"  75    60    -     50    90    80    70    65    60\n"
    "5 from lagna     10 Ge 30' 10\"  50    55    80    40    30    99    20    10    05\n"
    "Sun              10 Le 30' 0\"   70    65    80    55    90    75    66    60    55\n"
    "Moon             27 Pi 01' 45\"  10    20    30    40    50    60    70    80    90\n"
    "BadRow           05 Ar 05' 05\"  10    20    30    40    50    60    70    80\n")
ap = parse_aspects.clean_and_parse_aspects(ASP)["aspect_strengths"]
check("lagna row -> house_1_taurus (cutoff 64.5)", ap["from_ascendant_to_houses"].get("house_1_taurus") == {"sun": 75.0, "jupiter": 90.0, "venus": 80.0, "saturn": 70.0, "rahu": 65.0}, str(ap["from_ascendant_to_houses"].get("house_1_taurus")))
check("5 from lagna -> house_5_gemini", ap["from_ascendant_to_houses"].get("house_5_gemini") == {"mars": 80.0, "venus": 99.0})
check("sun row floats (65.0 kept, >=64.5)", ap["planet_to_planet_aspects"].get("sun_receives_aspects") == {"sun": 70.0, "moon": 65.0, "mars": 80.0, "jupiter": 90.0, "venus": 75.0, "saturn": 66.0}, str(ap["planet_to_planet_aspects"].get("sun_receives_aspects")))
check("moon row", ap["planet_to_planet_aspects"].get("moon_receives_aspects") == {"saturn": 70.0, "rahu": 80.0, "ketu": 90.0})
check("8-col row dropped", "badrow_receives_aspects" not in ap["planet_to_planet_aspects"])
# F-03 corrected (audit V-07): both parsers require apostrophe + space before
# seconds. Aligned after the owner decision — the seconds token is a proper
# decimal in both. The no-space variant is rejected by BOTH (documented format).
probe = parse_aspects.clean_and_parse_aspects("Jupiter 15 Ta 20'0\"  70 20 30 40 50 60 70 80 90\n")["aspect_strengths"]["planet_to_planet_aspects"]
check("no-space '20'0\" row rejected by BOTH parsers (aligned contract)",
      "jupiter_receives_aspects" not in probe
      and len(parse_planets.clean_and_parse_planets("Jupiter 15 Ta 20'0\"  70\n")["planetary_positions"]) == 0)
probe2 = parse_aspects.clean_and_parse_aspects("Jupiter 15 Ta 20' 0\"  70 20 30 40 50 60 70 80 90\n")["aspect_strengths"]["planet_to_planet_aspects"]
check("proper '20' 0\" row parses in BOTH parsers (aligned tolerance)",
      "jupiter_receives_aspects" in probe2
      and len(parse_planets.clean_and_parse_planets("Jupiter 15 Ta 20' 0\"\n")["planetary_positions"]) == 1)

# =====================================================================
print("== T9: full compile ==")
d1 = {
    "planets": {
        "sun": {"D1_placement": {"sign": "leo", "house": 10}, "notes": "keep-me"},
        "moon": {"D1_placement": {"sign": "pisces", "house": 5}},
        "mars": {"D1_placement": {"sign": "aries", "house": 1}}
    },
    "signs": {"aries": {"D1_house_number": 1}, "taurus": {"D1_house_number": 1}}
}
varga_planet_text = (
    "Lagna           08 Ta 33' 40\"\n"
    "Sun             10 Le 30' 30.0\"\n"
    "Moon            27 Pi 01' 45.3\"\n"
    "Mars (R)        22 Ar 50' 12.3\"\n"
    "Mercury         01 Vi 00' 00.0\"\n"
    "Jupiter         15 Ta 20' 0.0\"\n"
    "Venus           28 Li 01' 30.0\"\n"
    "Saturn          10 Ge 30' 10.0\"\n"
    "Rahu            05 Cn 15' 0.0\"\n"
    "Ketu            05 Cp 15' 0.0\"\n"
    "Gulika          09 Le 58' 00.0\"\n"
    "Maandi          11 Cp 00' 00.0\"\n"
)
vp = parse_planets.clean_and_parse_planets(varga_planet_text)
va = parse_avastha.clean_and_parse_avastha(
    "Sun    Baala (Child) Sushupta (Asleep) Hunger (Hunger)\n"
    "Moon   Madya (Adult) Jaagrita (Awake)\n"
    "Mars   Baala (Child) Jaagrita (Awake)\n")
yogas = {
    "gaja_kesari_yoga": {"active": True, "yoga_givers": "Mo Ju", "definition": "Mothers' wealth"},
    "sun_mars_yoga":    {"active": True, "yoga_givers": "Su Ma", "definition": "Courage"},
    "maandi_yoga":      {"active": True, "yoga_givers": "Md", "definition": "maandi-only giver (G-19: can never attach)"},
}
aspects = {"aspect_strengths": {
    "from_ascendant_to_houses": {"house_1_taurus": {"mars": 75.3}, "house_5": {"venus": 81.0}},
    "planet_to_planet_aspects": {
        "moon_receives_aspects": {"jupiter": {"strength": 80.0, "relation": "friend"},
                                   "saturn": {"strength": 70.0, "relation": "enemy"}},
        "sun_receives_aspects": {"saturn": {"strength": 80.0, "relation": "enemy"}}
    }
}}
bav_planets = ["sun","moon","mars","mercury","jupiter","venus","saturn","lagna"]
ashtakavarga = {
    "bhinnashtakavarga": {p: {s: 0 for s in parse_planets.ZODIAC_ORDER} for p in bav_planets},
    "samudayashtakavarga": {s: 20 for s in parse_planets.ZODIAC_ORDER}
}
ashtakavarga["bhinnashtakavarga"]["sun"]["leo"] = 6
ashtakavarga["bhinnashtakavarga"]["moon"]["pisces"] = 1
ashtakavarga["samudayashtakavarga"]["pisces"] = 24
arudhas = {"arudhas": {"AL": 1}, "varnadas": {"V1": 5}}

def make_app(d1_data, varga, raw):
    app = object.__new__(compile_all.MasterCompilerApp)
    app.d1_master_data = json.loads(json.dumps(d1_data))
    app.varga_name = varga
    app.raw_parsed_data = raw
    app.root = types.SimpleNamespace(quit=lambda: None)
    return app

def run_compile(app, outfile):
    """Run compile via the public wrapper (TODO-02 swallows exceptions into
    show_error). Removes the stale output file first, captures all modals, and
    returns (failure_message_or_None, all_notes). A stale file + swallowed
    exception would otherwise produce a false green."""
    if os.path.exists(outfile): os.remove(outfile)
    notes = []
    app.show_error = lambda m: notes.append(m)
    app.show_info = lambda m: notes.append(m)  # F-17: success now routes through show_info
    compile_all.filedialog.asksaveasfilename = lambda **kw: outfile
    app.compile_and_save()
    failed = next((n for n in notes if n.startswith("Compile Failed.")), None)
    return failed, notes

def try_ingest(app, method):
    """Invoke an ingest method with modal capture; exceptions become notes
    (canary: mark_complete on a bare app would raise AttributeError)."""
    notes = []
    app.show_error = lambda m: notes.append(m)
    try:
        method(app)
    except Exception as e:
        notes.append(f"EXCEPTION {type(e).__name__}: {e}")
    return notes

app = make_app(d1, "D9", {
    "planets": vp["planetary_positions"],
    "argala": calculate_argala.compute_argala_matrix(vp)["argala_analysis"],
    "avasthas": va["avasthas"],
    "aspects": aspects["aspect_strengths"],
    "yogas": yogas,
    "ashtakavarga": ashtakavarga,
    "arudhas": arudhas,
})
# Simulate the GUI capture path: the aspects hijack normalizes paste-mode floats (TODO-01).
app.raw_parsed_data["aspects"] = compile_all.normalize_aspect_values(app.raw_parsed_data["aspects"])
failed, notes = run_compile(app, "/tmp/jhora_audit/out.json")
check("compile completed", failed is None and os.path.exists("/tmp/jhora_audit/out.json"), str(failed))

out = json.load(open("/tmp/jhora_audit/out.json"))
sun = out["planets"]["sun"]
check("D1 keys preserved", sun.get("notes") == "keep-me" and sun["D1_placement"]["house"] == 10)
check("sun D9 placement", sun["D9_placement"]["house"] == 4 and sun["D9_placement"]["sign"] == "leo")
check("mars is_retrograde", out["planets"]["mars"]["D9_placement"].get("is_retrograde") is True)
check("sun longitude truncated", sun["D9_placement"]["longitude"] == "10° 30'", sun["D9_placement"]["longitude"])
check("sun avastha triple", sun.get("D9_avastha_alertness") == "Asleep" and sun.get("D9_avastha_age") == "Baala" and sun.get("D9_avastha_moods") == ["Hunger"])
check("sun aspects_received", sun.get("D9_aspects_received") == {"saturn": {"strength": 80.0, "relation": "enemy"}})
g = next((sp for sp in out["signs"]["leo"].get("D9_special_points", []) if sp["name"] == "gulika"), None)
check("G-01: gulika 9°58' conjuncts sun 10°30' (pre-truncation math)", g is not None and "sun" in g.get("conjuncting_planets", []), str(out["signs"]["leo"].get("D9_special_points")))
check("SP longitude truncated keeps leading zero", g and g["longitude"] == "09°", str(g and g["longitude"]))
check("house numbers from lagna", out["signs"]["taurus"]["D9_house_number"] == 1 and out["signs"]["leo"]["D9_house_number"] == 4)
check("house lords", out["signs"]["leo"]["D9_house_lord"] == "sun" and out["signs"]["virgo"]["D9_house_lord"] == "mercury")
check("leo occupants [sun] (SP excluded)", out["signs"]["leo"].get("D9_occupants") == ["sun"])
check("empty occupants removed (scorpio)", "D9_occupants" not in out["signs"]["scorpio"])
check("non-empty occupants kept (aries: mars)", out["signs"]["aries"].get("D9_occupants") == ["mars"])
check("AL -> taurus", out["signs"]["taurus"].get("D9_arudhas") == ["AL"])
check("V1 house5 -> virgo", out["signs"]["virgo"].get("D9_varnadas") == ["V1"])
check("asc-aspects by sign key (normalized objects)", out["signs"]["taurus"].get("D9_aspects_received") == {"mars": {"strength": 75.3, "relation": "neutral"}}, str(out["signs"]["taurus"].get("D9_aspects_received")))
check("asc-aspects manual key 'house_5' -> virgo via house math (normalized objects)", out["signs"]["virgo"].get("D9_aspects_received") == {"venus": {"strength": 81.0, "relation": "neutral"}}, str(out["signs"]["virgo"].get("D9_aspects_received")))
check("success notice lists ingested rows (F-12)", any("Rows ingested:" in n for n in notes), str(notes))
check("TODO-09: G-19 maandi-only yoga named in success notice",
      any("1 yoga(s) not attached (no core planet givers): maandi_yoga" in n for n in notes), str(notes))
check("success notice routed through show_info (F-17) — captured",
      any(n.startswith("SUCCESS!") for n in notes), str(notes))
sm_sun = out["planets"]["sun"].get("D9_yogas", {}).get("sun_mars_yoga")
sm_mars = out["planets"]["mars"].get("D9_yogas", {}).get("sun_mars_yoga")
check("TODO-18: per-planet yoga payloads are separate objects (no aliasing)",
      sm_sun is not None and sm_mars is not None and sm_sun is not sm_mars and sm_sun == sm_mars)
check("sav/bav", out["signs"]["pisces"].get("D9_sav") == 24 and out["signs"]["pisces"].get("D9_bav", {}).get("moon") == 1)
check("argala attached", any("D9_effective_argala" in s for s in out["signs"].values()))
check("G-19: maandi-only yoga NOT attached anywhere", all("maandi_yoga" not in p.get("D9_yogas", {}) for p in out["planets"].values()))
gm = out["planets"]["moon"].get("D9_yogas", {}).get("gaja_kesari_yoga")
check("gaja kesari on moon+jupiter", gm is not None and "gaja_kesari_yoga" in out["planets"]["jupiter"].get("D9_yogas", {}), str(gm and gm.get("status")))
gm2 = out["planets"]["sun"].get("D9_yogas", {}).get("sun_mars_yoga")
check("sun_mars payload shared", gm2 and out["planets"]["mars"]["D9_yogas"]["sun_mars_yoga"]["technical_analysis"] == gm2["technical_analysis"])
check("yoga active flag consistent", all(p["D9_yogas"][k]["active"] == (p["D9_yogas"][k]["status"] == "Active") for p in out["planets"].values() for k in p.get("D9_yogas", {})))
print("   sample statuses:", {k: v.get("status") for k, v in out["planets"]["moon"].get("D9_yogas", {}).items()})

print("== T10: F-01 closed — paste-mode float aspects normalized at capture ==")
app2 = make_app({"planets": {"sun": {}}, "signs": {}}, "D9", {
    "planets": parse_planets.clean_and_parse_planets("Lagna 08 Ta 33' 40\"\nSun 10 Le 30' 30.0\"\n")["planetary_positions"],
    "argala": {}, "avasthas": [],
    "aspects": {"planet_to_planet_aspects": {"sun_receives_aspects": {"saturn": 70.0}},
                 "from_ascendant_to_houses": {"house_1_taurus": {"mars": 75.3}}},
    "yogas": {"sun_check_yoga": {"active": True, "yoga_givers": "Su", "definition": "score probe"}},
    "ashtakavarga": {}, "arudhas": {},
})
# Simulate the GUI capture path: the aspects hijack normalizes paste-mode floats (TODO-01).
app2.raw_parsed_data["aspects"] = compile_all.normalize_aspect_values(app2.raw_parsed_data["aspects"])
failed, _notes10 = run_compile(app2, "/tmp/jhora_audit/out2.json")
check("compile completes with paste-mode float aspects (F-01 closed)", failed is None and os.path.exists("/tmp/jhora_audit/out2.json"), str(failed))
out2 = json.load(open("/tmp/jhora_audit/out2.json"))
check("floats normalized to objects on planet node", out2["planets"]["sun"].get("D9_aspects_received") == {"saturn": {"strength": 70.0, "relation": "neutral"}}, str(out2["planets"]["sun"].get("D9_aspects_received")))
check("asc-aspect floats normalized to objects on sign node", out2["signs"]["taurus"].get("D9_aspects_received") == {"mars": {"strength": 75.3, "relation": "neutral"}}, str(out2["signs"]["taurus"].get("D9_aspects_received")))
ta2 = out2["planets"]["sun"].get("D9_yogas", {}).get("sun_check_yoga", {}).get("technical_analysis", "")
check("scoring consumed the strength (malefic aspect -15)", "Strong Malefic Aspect from Saturn (-15)" in ta2, ta2)
m2 = _re.search(r"Combined Strength Score: ([\-\d.]+)/100", ta2)
check("score = 125 (100 +10 kendra +20 MT +10 strong dispositor -15 aspect)", m2 and float(m2.group(1)) == 125.0, m2 and m2.group(1))
check("yoga Active for score >= 70", out2["planets"]["sun"]["D9_yogas"]["sun_check_yoga"]["status"] == "Active" and out2["planets"]["sun"]["D9_yogas"]["sun_check_yoga"]["active"] is True)

print("== T11: D1 self-heal ==")
app3 = make_app({"sun": {"D1_placement": {"sign": "leo"}}, "signs": {}}, "D9", {
    "planets": parse_planets.clean_and_parse_planets("Lagna 08 Ta 33' 40\"\n")["planetary_positions"],
    "argala": {}, "avasthas": [], "aspects": {}, "yogas": {}, "ashtakavarga": {}, "arudhas": {},
})
failed, _ = run_compile(app3, "/tmp/jhora_audit/out3.json")
check("T11 compile completed", failed is None and os.path.exists("/tmp/jhora_audit/out3.json"), str(failed))
out3 = json.load(open("/tmp/jhora_audit/out3.json"))
check("root sun re-nested", "sun" in out3["planets"] and "sun" not in out3)

print("== T12: unclamped scoring through FULL parser path ==")
t12_text = (
    "Lagna   08 Vi 33' 40\"\n"
    "Saturn  01 Ar 00' 00.0\"\n"
    "Mars    20 Le 30' 00.0\"\n"
    "Rahu    25 Ar 15' 00.0\"\n"
    "Sun     03 Ta 00' 00.0\"\n"
    "Moon    10 Ge 00' 00.0\"\n"
    "Mercury 10 Li 00' 00.0\"\n"
    "Jupiter 12 Ta 00' 00.0\"\n"
    "Venus   10 Pi 00' 00.0\"\n"
    "Ketu    25 Li 00' 00.0\"\n"
)
pos = parse_planets.clean_and_parse_planets(t12_text)["planetary_positions"]
sat = next(p for p in pos if p["body"] == "saturn")
check("setup: saturn debilitated + h8 + worst_enemy + no upachaya", sat.get("special_dignity") == "debilitated" and sat["house"] == 8 and sat.get("house_dignity") == "worst_enemy_house" and "upachaya_effect" not in sat, str(sat))
check("setup: rahu conjunct h8 (no upachaya)", next(p for p in pos if p["body"] == "rahu")["house"] == 8 and "upachaya_effect" not in next(p for p in pos if p["body"] == "rahu"))
check("setup: mars dispositor in h12 (dusthana, no upachaya)", (lambda m: m["house"] == 12 and "upachaya_effect" not in m)(next(p for p in pos if p["body"] == "mars")))
app4 = make_app({"planets": {}, "signs": {}}, "D9", {
    "planets": pos, "argala": {},
    "avasthas": [{"body": "saturn", "age": "Baala", "alertness": "Asleep", "moods": []}],
    "aspects": {"planet_to_planet_aspects": {"saturn_receives_aspects": {"mars": {"strength": 70.0, "relation": "enemy"}}}, "from_ascendant_to_houses": {}},
    "yogas": {"evil_yoga": {"active": True, "yoga_givers": "Sa", "definition": "x"}},
    "ashtakavarga": {"bhinnashtakavarga": {p: {"aries": 1} for p in bav_planets}, "samudayashtakavarga": {"aries": 24}},
    "arudhas": {},
})
failed, _ = run_compile(app4, "/tmp/jhora_audit/out4.json")
check("T12 compile completed", failed is None and os.path.exists("/tmp/jhora_audit/out4.json"), str(failed))
out4 = json.load(open("/tmp/jhora_audit/out4.json"))
ta = out4["planets"]["saturn"]["D9_yogas"]["evil_yoga"]
print("   reasons:", ta["technical_analysis"])
mval = _re.search(r"Combined Strength Score: ([\-\d.]+)/100", ta["technical_analysis"])
check("expected -75 (special dignity SUPPRESSES house-dignity line: 100-40dig-30h8-40asleep-10disp-10bav-10sav-20rahu-15asp)", mval and float(mval.group(1)) == -75.0, mval and mval.group(1))
check("precedence: debilitated -> no Enemy Sign line (house dignity skipped)", "Enemy Sign" not in ta["technical_analysis"])
check("status Asleep + active false", ta["status"] == "Asleep" and ta["active"] is False)

print("== T13: empty/edge compiles ==")
# only lagna in varga, empty everything else -> should still compile (G-14: step done proves nothing)
app5 = make_app({"planets": {"sun": {}}, "signs": {}}, "D9", {
    "planets": parse_planets.clean_and_parse_planets("Lagna 08 Ta 33' 40\"\n")["planetary_positions"],
    "argala": {}, "avasthas": [], "aspects": {}, "yogas": {}, "ashtakavarga": {}, "arudhas": {},
})
failed, _ = run_compile(app5, "/tmp/jhora_audit/out5.json")
check("lagna-only varga compiles", failed is None and os.path.exists("/tmp/jhora_audit/out5.json"), str(failed))
out5 = json.load(open("/tmp/jhora_audit/out5.json"))
check("sun neutral 100 (no placement)", "D9_placement" not in out5["planets"]["sun"])
check("signs scaffolded 12 with house numbers", len(out5["signs"]) == 12 and out5["signs"]["taurus"]["D9_house_number"] == 1)

# varga with NO lagna row -> fallback aries (G-05)
app6 = make_app({"planets": {}, "signs": {}}, "D9", {
    "planets": parse_planets.clean_and_parse_planets("Sun 10 Le 30' 30.0\"\n")["planetary_positions"],
    "argala": {}, "avasthas": [], "aspects": {}, "yogas": {}, "ashtakavarga": {}, "arudhas": {},
})
failed, _ = run_compile(app6, "/tmp/jhora_audit/out6.json")
check("no-lagna varga compiles", failed is None and os.path.exists("/tmp/jhora_audit/out6.json"), str(failed))
out6 = json.load(open("/tmp/jhora_audit/out6.json"))
check("no-lagna fallback: lagna aries (aries=house1)", out6["signs"]["aries"]["D9_house_number"] == 1 and out6["signs"]["leo"]["D9_house_number"] == 5)
check("no house in placement", out6["planets"]["sun"]["D9_placement"].get("house") is None)

print("== T14: edge probes (latent behaviors — hardened in Milestone B) ==")
y_edge = parse_yogas.clean_and_parse_yogas(
    "Yoga               Varga  Yoga givers  Brief def\n"
    "Sunapha Yoga       Rasi   Mo           Moon-Sun combo\n")
rec = y_edge["yogas"].get("sunapha_yoga", {})
check("TODO-07: header w/o 'Results' col now falls to the regex pass (clean values, no -1 slice)",
      rec.get("yoga_givers") == "Mo" and rec.get("definition") == "Moon-Sun combo", str(rec))
y_tab = parse_yogas.clean_and_parse_yogas("Some Yoga\tRasi\tJu\n")
check("TODO-08: tab row with <4 cols now falls through instead of being dropped",
      y_tab["yogas"].get("some_yoga", {}).get("yoga_givers") == "Ju", str(y_tab["yogas"]))
a_edge = parse_aspects.clean_and_parse_aspects("Lagna from lagna 08 Ta 33' 40\"  75 60 - 50 90 80 70 65 60\n")["aspect_strengths"]
check("'Lagna from lagna' -> house_1_{sign}", list(a_edge["from_ascendant_to_houses"]) == ["house_1_taurus"])
gq = calculate_argala.get_quarter("28.0° 00' 00.0\"")
check("TODO-06: float degree string '28.0°' -> quarter 4 (acceptance)", gq == 4, str(gq))
gq2 = calculate_argala.get_quarter("28° 00' 00.0\"")
check("TODO-06: int-degree strings unchanged (28° -> 4)", gq2 == 4, str(gq2))

print("== T15: TODO-02 — compile wrapper surfaces failures as a modal (no traceback, no partial file) ==")
app7 = make_app("corrupted-not-a-dict", "D9", {"planets": [], "argala": {}, "avasthas": [], "aspects": {}, "yogas": {}, "ashtakavarga": {}, "arudhas": {}})
failed, notes15 = run_compile(app7, "/tmp/jhora_audit/out7.json")
check("wrapped compile catches the exception into show_error", failed is not None and failed.startswith("Compile Failed."), str(notes15))
check("failure modal carries the factual cause", "str" in (failed or ""), str(failed))
check("no file written on failed compile", not os.path.exists("/tmp/jhora_audit/out7.json"))

print("== T16: TODO-03 — ingest module-missing guards ==")
EMPTY_RAW = {"planets": {}, "argala": {}, "avasthas": {}, "aspects": {}, "yogas": {}, "ashtakavarga": {}, "arudhas": {}}
app8 = make_app({}, "D9", EMPTY_RAW)
s_pp, s_ca, s_av, s_yo = (compile_all.clean_and_parse_planets, compile_all.compute_argala_matrix,
                          compile_all.clean_and_parse_avastha, compile_all.clean_and_parse_yogas)
try:
    compile_all.clean_and_parse_planets = None
    notes = try_ingest(app8, lambda a: a.ingest_planets())
    check("ingest_planets: 'Planets module missing.' + no completion",
          any(n == "Planets module missing." for n in notes) and not any(n.startswith("EXCEPTION") for n in notes), str(notes))
    compile_all.clean_and_parse_planets = s_pp  # restore before isolating the argala guard
    compile_all.compute_argala_matrix = None
    notes = try_ingest(app8, lambda a: a.ingest_planets())
    check("ingest_planets: 'Argala module missing.' + no completion",
          any(n == "Argala module missing." for n in notes) and not any(n.startswith("EXCEPTION") for n in notes), str(notes))
    compile_all.clean_and_parse_avastha = None
    notes = try_ingest(app8, lambda a: a.ingest_avasthas())
    check("ingest_avasthas: 'Avasthas module missing.' + no completion",
          any(n == "Avasthas module missing." for n in notes) and not any(n.startswith("EXCEPTION") for n in notes), str(notes))
    compile_all.clean_and_parse_yogas = None
    notes = try_ingest(app8, lambda a: a.ingest_yogas())
    check("ingest_yogas: 'Yogas module missing.' + no completion",
          any(n == "Yogas module missing." for n in notes) and not any(n.startswith("EXCEPTION") for n in notes), str(notes))
finally:
    compile_all.clean_and_parse_planets, compile_all.compute_argala_matrix = s_pp, s_ca
    compile_all.clean_and_parse_avastha, compile_all.clean_and_parse_yogas = s_av, s_yo

print("== T17: TODO-04 — empty clipboard / zero rows never mark the step complete ==")
class _FakeClipboard:
    def __init__(self, txt): self.txt = txt
    def paste(self): return self.txt
s_pc = compile_all.pyperclip
class _FakeBtn:
    def __init__(self): self.state = "normal"; self._text = "step"
    def __getitem__(self, k): return self._text if k == "text" else self.state
    def config(self, **kw):
        if "state" in kw: self.state = kw["state"]
        if "text" in kw: self._text = kw["text"]
try:
    app9 = make_app({}, "D9", EMPTY_RAW)
    app9.step_buttons = {s: _FakeBtn() for s in ("planets", "avastha", "aspects", "yogas", "ashtakavarga", "arudha")}
    app9.btn_compile = _FakeBtn()
    compile_all.pyperclip = _FakeClipboard("")
    notes = try_ingest(app9, lambda a: a.ingest_planets())
    check("planets: empty clipboard -> modal, no completion",
          any("Clipboard is empty" in n for n in notes) and not any(n.startswith("EXCEPTION") for n in notes), str(notes))
    compile_all.pyperclip = _FakeClipboard("Body            Longitude\n")
    notes = try_ingest(app9, lambda a: a.ingest_planets())
    check("planets: zero parsed rows -> modal, no completion",
          any("No planet rows found" in n for n in notes) and not any(n.startswith("EXCEPTION") for n in notes), str(notes))
    compile_all.pyperclip = _FakeClipboard("")
    notes = try_ingest(app9, lambda a: a.ingest_avasthas())
    check("avasthas: empty clipboard -> modal, no completion",
          any("Clipboard is empty" in n for n in notes) and not any(n.startswith("EXCEPTION") for n in notes), str(notes))
    compile_all.pyperclip = _FakeClipboard("Varga Yoga givers\n---\n")
    notes = try_ingest(app9, lambda a: a.ingest_yogas())
    check("yogas: zero rows -> modal, no completion",
          any("No yoga rows found" in n for n in notes) and not any(n.startswith("EXCEPTION") for n in notes), str(notes))
    # positive control: valid content still parses and completes the step (guards do not over-block)
    compile_all.pyperclip = _FakeClipboard("Sun    Madya (Adult) Jaagrita (Awake)\n")
    notes = try_ingest(app9, lambda a: a.ingest_avasthas())
    check("avasthas: valid row parses + mark_complete fires (no over-blocking)",
          not any(n.startswith("EXCEPTION") for n in notes) and len(app9.raw_parsed_data.get("avasthas", [])) == 1
          and app9.step_buttons["avastha"].state == "disabled", str(notes))
finally:
    compile_all.pyperclip = s_pc

print("== T20: TODO-06 mirror — parse_planets MT degree parse accepts float strings ==")
mt_fixed = parse_planets.clean_and_parse_planets(
    "Lagna          10 Ar 30' 00.0\"\n"
    "Jupiter        15 Sg 00' 00.0\"\n")
jup = next((r for r in mt_fixed["planetary_positions"] if r["body"] == "jupiter"), None)
check("Jupiter 15.0° Sg is OUT of the MT window (0-10) after float fix -> no moolatrikona",
      jup is not None and jup.get("special_dignity") != "moolatrikona", str(jup))
mt_probe = parse_planets.clean_and_parse_planets(
    "Lagna          10 Ar 30' 00.0\"\n"
    "Jupiter        05 Sg 00' 00.0\"\n")
jup2 = next((r for r in mt_probe["planetary_positions"] if r["body"] == "jupiter"), None)
check("Jupiter 5.0° Sg is IN the MT window -> moolatrikona (window math intact)",
      jup2 is not None and jup2.get("special_dignity") == "moolatrikona", str(jup2))

print("== T21: TODO-22 — cancelled save dialog is no longer silent ==")
app_c = make_app(d1, "D9", {"planets": vp["planetary_positions"], "argala": {}, "avasthas": [], "aspects": {}, "yogas": {}, "ashtakavarga": {}, "arudhas": {}})
cnotes = []
app_c.show_error = lambda m: cnotes.append(m)
app_c.show_info = lambda m: cnotes.append(m)
compile_all.filedialog.asksaveasfilename = lambda **kw: ""   # user cancelled
app_c.compile_and_save()
check("cancel -> notice 'Save cancelled' with retry pointer",
      any("Save cancelled." in n and "Press Compile again to retry." in n for n in cnotes), str(cnotes))
check("cancel -> no file written, no failure modal",
      not any(n.startswith("Compile Failed.") for n in cnotes))

print("== T22: TODO-19 — malformed aspect keys and duplicate special-point names ==")
dup_sp_text = ("Lagna          10 Le 30' 00.0\"\n"
               "Sun            10 Le 30' 00.0\"\n"
               "Gulika         10 Le 30' 00.0\"\n"
               "Gulika         10 Le 30' 00.0\"\n")
app_w = make_app({"planets": {}, "signs": {}}, "D9", {
    "planets": parse_planets.clean_and_parse_planets(dup_sp_text)["planetary_positions"],
    "argala": {}, "avasthas": [],
    "aspects": compile_all.normalize_aspect_values({"from_ascendant_to_houses": {"house_x_gemini": {"mars": 75.0}, "house_4_gemini": {"venus": 60.0}}}),
    "yogas": {}, "ashtakavarga": {}, "arudhas": {},
})
failed, wnotes = run_compile(app_w, "/tmp/jhora_audit/out_w.json")
check("malformed aspect key does not crash the compile (F-22)", failed is None, str(failed))
check("malformed key skipped + warned in success notice",
      any("Skipped malformed aspect key: 'house_x_gemini'" in n for n in wnotes), str(wnotes))
outw = json.load(open("/tmp/jhora_audit/out_w.json"))
check("valid key house_4_gemini still attached",
      outw["signs"]["gemini"].get("D9_aspects_received") == {"venus": {"strength": 60.0, "relation": "neutral"}},
      str(outw["signs"]["gemini"].get("D9_aspects_received")))
check("duplicate special-point name warned (F-21)",
      any("Special point name collision: 'gulika'" in n for n in wnotes), str(wnotes))
check("first duplicate occurrence kept for conjunction math",
      any(sp.get("name") == "gulika" for sp in outw["signs"]["leo"].get("D9_special_points", [])))

print("== T23: TODO-20 — standalone __main__ guards (static contract) ==")
for mod_path in ("parse_planets", "parse_avastha", "parse_yogas", "calculate_argala"):
    tree = ast.parse(open(f"{REPO}/{mod_path}.py").read())
    has_guard = any(
        isinstance(n, ast.Try) and any(
            isinstance(h, ast.ExceptHandler) and getattr(h.type, "id", None) == "PyperclipException"
            or (isinstance(h.type, ast.Attribute) and h.type.attr == "PyperclipException")
            for h in n.handlers)
        for n in ast.walk(tree))
    check(f"{mod_path}.py __main__ catches PyperclipException", has_guard)

print()
print(f"RESULTS: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
