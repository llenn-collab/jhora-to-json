import re
import json
import pyperclip

NAME_DATABASE = {
    "planets": {
        "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
        "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa", "Rahu": "Ra", "Ketu": "Ke"
    }
}

def format_yoga_key(raw_name):
    """
    Converts 'Yogada (HL)' -> 'yogada_hl_yoga'
    Converts 'Daama/Daamini' -> 'daama_daamini_yoga'
    """
    clean_name = raw_name.replace('(', '').replace(')', '')
    clean_name = re.sub(r'[\s/\-]+', '_', clean_name).lower()
    if not clean_name.endswith('yoga'): clean_name += '_yoga'
    return clean_name

def clean_and_parse_yogas(raw_text):
    parsed_yogas = {}
    raw_text = raw_text.replace('\x00', '')
    lines = raw_text.strip().split('\n')
    
    # Store dynamic column bounds for fixed-width parsing (The absolute safest method for JHora strings)
    header_bounds = {}
    
    for line in lines:
        original_line = line.rstrip() # Preserve the exact spacing for slicing
        line = line.strip()

        if not line or "Varga Yoga givers" in line or line.startswith("---"):
            continue

        # Detect and store the exact character indices of the columns to create a vertical cookie-cutter
        if "Yoga" in line and "Varga" in line and "Yoga givers" in line:
            header_bounds['varga'] = original_line.find("Varga")
            header_bounds['givers'] = original_line.find("Yoga givers")
            header_bounds['results'] = original_line.find("Results")
            header_bounds['def'] = original_line.find("Brief def")
            continue

        # 1. First Pass: Tab separation (Ideal if clipboard naturally preserved tabs)
        if '\t' in line:
            cols = [c.strip() for c in line.split('\t') if c.strip()]
            if len(cols) >= 4:
                yoga_name = cols[0]
                givers = cols[2]
                results = cols[3]
            else:
                continue
                
        # 2. Second Pass: Dynamic fixed-width slicing based on header
        # This completely ignores whatever complex strings exist inside the 'Varga' column.
        elif header_bounds and header_bounds.get('varga', -1) > 0:
            # Pad line to ensure we don't index out of bounds on shorter lines
            padded_line = original_line.ljust(header_bounds['results'] + 10)
            yoga_name = padded_line[:header_bounds['varga']].strip()
            givers = padded_line[header_bounds['givers']:header_bounds['results']].strip()
            
            if header_bounds.get('def', -1) != -1 and header_bounds['def'] < len(padded_line):
                results = padded_line[header_bounds['results']:header_bounds['def']].strip()
            else:
                results = padded_line[header_bounds['results']:].strip()
                
        # 3. Third Pass: Robust Regex Fallback if Header is Missing
        else:
            # Safely match 'Rasi' or any 'D-XX x D-XX (Trd)' variation without greedy over-selection
            varga_pattern = r"(Rasi|D-\d+(?:\s*\([^)]*\))?(?:\s*x\s*D-\d+(?:\s*\([^)]*\))?)?)"
            match = re.match(r"^(.*?)\s+" + varga_pattern + r"\s+(.*)$", original_line.strip())

            if match:
                yoga_name = match.group(1).strip()
                remainder = match.group(3).strip()
                
                # Extreme Edge Case: "Naabhasa yoga" lacks double spaces in JHora. 
                # We trap it manually so it doesn't merge with the 'Results' column.
                if remainder.startswith("Naabhasa yoga - throughout life"):
                    givers = "Naabhasa yoga - throughout life"
                    results = remainder[len(givers):].strip()
                else:
                    parts = re.split(r'\s{2,}', remainder)
                    if len(parts) >= 2:
                        givers = parts[0]
                        results = parts[1]
                    else:
                        givers = parts[0] if parts else ""
                        results = ""
            else:
                # Absolute desperate fallback
                cols = re.split(r'\s{2,}', original_line.strip())
                if len(cols) >= 4:
                    yoga_name = cols[0]
                    givers = cols[2]
                    results = cols[3]
                else:
                    continue

        base_key = format_yoga_key(yoga_name)
        yoga_key = base_key

        counter = 2
        while yoga_key in parsed_yogas:
            yoga_key = f"{base_key}_{counter}"
            counter += 1

        parsed_yogas[yoga_key] = {
            "active": True,
            "yoga_givers": givers,
            "definition": results
        }

    return {"yogas": parsed_yogas}

if __name__ == "__main__":
    clipboard_data = pyperclip.paste()
    if not clipboard_data.strip():
        print("[!] Clipboard is empty. Copy JHora Yogas data first.")
    else:
        result_json = clean_and_parse_yogas(clipboard_data)
        print(json.dumps(result_json, indent=4))