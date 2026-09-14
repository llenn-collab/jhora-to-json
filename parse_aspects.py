import tkinter as tk
from tkinter import messagebox, filedialog
import re
import json
import pyperclip

# Consistent mapping database aligned with your existing pipeline
NAME_DATABASE = {
    "planets": {
        "Sun": "sun", "Moon": "moon", "Mars": "mars", "Mercury": "mercury",
        "Jupiter": "jupiter", "Venus": "venus", "Saturn": "saturn",
        "Rahu": "rahu", "Ketu": "ketu"
    },
    "rasis": {
        "Ar": "aries", "Ta": "taurus", "Ge": "gemini", "Cn": "cancer",
        "Le": "leo", "Vi": "virgo", "Li": "libra", "Sc": "scorpio",
        "Sg": "sagittarius", "Cp": "capricorn", "Aq": "aquarius", "Pi": "pisces"
    }
}

ASPECTING_COLUMNS = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"]

COLORS = {
    "bg_main": "#121212", "bg_card": "#1E1E1E", "text_primary": "#FFFFFF",
    "text_muted": "#A1A1AA", "border": "#27272A", "dropdown_bg": "#27272A",
    "success": "#10B981"
}
FONTS = {
    "h1": ("Helvetica", 20, "bold"),
    "label": ("Helvetica", 14, "bold"),
    "body": ("Helvetica", 13),
    "small": ("Helvetica", 11)
}

RECEIVERS = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"] + [f"house_{i}" for i in range(1, 13)]
CASTERS = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"]
RELATIONS = ["neutral", "enemy", "friend", "worst_enemy", "good_friend", "own_house"]

def clean_and_parse_aspects(raw_text):
    output = {
        "aspect_strengths": {
            "from_ascendant_to_houses": {},
            "planet_to_planet_aspects": {}
        }
    }
    raw_text = raw_text.replace('\x00', '')
    lines = raw_text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line or line.startswith("Aspected Body"): continue
        match = re.search(r"^(.*?)\s+(\d+\s+[A-Za-z]{2}\s+\d+'\s+[\d.]+\")\s+(.*)$", line)
        if not match: continue

        raw_row_name = match.group(1).strip()
        longitude_str = match.group(2).strip()
        aspects_str = match.group(3).strip()

        sign_match = re.search(r"\d+\s+([A-Za-z]{2})\s+", longitude_str)
        sign_abbr = sign_match.group(1) if sign_match else None
        sign_full = NAME_DATABASE["rasis"].get(sign_abbr, "unknown")

        aspect_vals_raw = aspects_str.split()
        if len(aspect_vals_raw) != len(ASPECTING_COLUMNS): continue

        valid_aspects = {}
        for idx, val_str in enumerate(aspect_vals_raw):
            if val_str == '-': continue
            try:
                val_float = float(val_str.replace('%', ''))
                if val_float >= 64.5: valid_aspects[ASPECTING_COLUMNS[idx]] = val_float
            except ValueError: continue

        if not valid_aspects: continue

        clean_name = raw_row_name.replace("(R)", "").strip().lower()
        if clean_name == "lagna" or "from lagna" in clean_name:
            house_num = 1
            if "from lagna" in clean_name:
                num_match = re.search(r"^(\d+)", clean_name)
                if num_match: house_num = int(num_match.group(1))
            house_key = f"house_{house_num}_{sign_full}"
            output["aspect_strengths"]["from_ascendant_to_houses"][house_key] = valid_aspects
        elif clean_name in ASPECTING_COLUMNS:
            planet_key = f"{clean_name}_receives_aspects"
            output["aspect_strengths"]["planet_to_planet_aspects"][planet_key] = valid_aspects
    return output

class AspectsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Aspects Ingestion")
        self.root.geometry("850x700")
        self.root.resizable(False, False)
        self.root.configure(bg=COLORS["bg_main"])
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        self.root.focus_force()

        self.final_output = None
        self.mode = None
        self.grid_vars = {r: {c: {} for c in CASTERS} for r in RECEIVERS}
        self.create_main_menu()

    def create_main_menu(self):
        for widget in self.root.winfo_children(): widget.destroy()

        self.header_frame = tk.Frame(self.root, bg=COLORS["bg_main"], pady=40)
        self.header_frame.pack(fill="x")
        tk.Label(self.header_frame, text="Select Input Method", font=FONTS["h1"], bg=COLORS["bg_main"], fg=COLORS["text_primary"]).pack()
        tk.Label(self.header_frame, text="Choose how to ingest Aspect Strengths", font=FONTS["body"], bg=COLORS["bg_main"], fg=COLORS["text_muted"]).pack(pady=(5, 20))

        btn_frame = tk.Frame(self.root, bg=COLORS["bg_main"])
        btn_frame.pack(expand=True)

        tk.Button(btn_frame, text="Paste from JHora Clipboard", command=self.do_paste, font=FONTS["label"], width=30, height=2, cursor="hand2").pack(pady=10)
        tk.Button(btn_frame, text="Manual Matrix Entry (Grid)", command=self.show_manual, font=FONTS["label"], width=30, height=2, cursor="hand2").pack(pady=10)

    def show_manual(self):
        self.mode = "manual"
        for widget in self.root.winfo_children(): widget.destroy()

        self.header_frame = tk.Frame(self.root, bg=COLORS["bg_main"], pady=15)
        self.header_frame.pack(fill="x")
        tk.Label(self.header_frame, text="Manual Matrix Entry", font=FONTS["h1"], bg=COLORS["bg_main"], fg=COLORS["text_primary"]).pack()
        tk.Label(self.header_frame, text="Type % strength. Press ENTER on any cell to select its relation.", font=FONTS["small"], bg=COLORS["bg_main"], fg=COLORS["text_muted"]).pack()

        # Fixed Header Frame for Columns (Casters)
        h_frame = tk.Frame(self.root, bg=COLORS["bg_card"], bd=1, relief="solid")
        h_frame.pack(fill="x", padx=20, pady=(10, 0))
        tk.Label(h_frame, text="Receivers ↓", font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_muted"], width=12, anchor="w").grid(row=0, column=0, padx=10, pady=5)

        for j, cast in enumerate(CASTERS):
            tk.Label(h_frame, text=cast[:3].capitalize(), font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_primary"], width=8, anchor="center").grid(row=0, column=j+1, padx=2)

        # Scrollable Layout Configuration
        self.list_frame = tk.Frame(self.root, bg=COLORS["bg_card"], bd=1, relief="solid", highlightbackground=COLORS["border"], highlightthickness=1)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        # Setup Canvas and Link Scrollbar (Fix 1: Explicitly configure yscrollcommand)
        self.canvas = tk.Canvas(self.list_frame, bg=COLORS["bg_card"], highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self.list_frame, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.scrollable_frame = tk.Frame(self.canvas, bg=COLORS["bg_card"])
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Populate Grid Entries
        for i, recv in enumerate(RECEIVERS):
            lbl_text = recv.capitalize().replace("_", " ")
            tk.Label(self.scrollable_frame, text=lbl_text, font=FONTS["small"], bg=COLORS["bg_card"], fg=COLORS["text_primary"], width=12, anchor="w").grid(row=i, column=0, padx=10, pady=4)

            for j, cast in enumerate(CASTERS):
                var = tk.StringVar()
                entry = tk.Entry(self.scrollable_frame, textvariable=var, width=8, justify="center", bg=COLORS["dropdown_bg"], fg=COLORS["text_primary"], font=FONTS["small"], insertbackground="white", relief="flat")
                entry.grid(row=i, column=j+1, padx=3, pady=4)

                # Bind ENTER key to relation selector popup
                entry.bind("<Return>", lambda e, r=recv, c=cast: self.popup_relation(e, r, c))
                self.grid_vars[recv][cast] = {"var": var, "rel": "neutral", "entry": entry}

        # Fix 2: Bind scrollwheel to the entire UI hierarchy recursively so scrolling never locks
        self.bind_scroll_recursive(self.canvas)
        self.bind_scroll_recursive(self.scrollable_frame)

        # Bottom Action Buttons
        btn_frame = tk.Frame(self.root, bg=COLORS["bg_main"], pady=15)
        btn_frame.pack(fill="x", padx=20)
        tk.Button(btn_frame, text="Save & Export", command=self.export_json, font=FONTS["label"], cursor="hand2", width=15).pack(side="right")

    # Recursive scrollwheel binding helper (Crucial for macOS trackpad scrolling inside Entry fields)
    def bind_scroll_recursive(self, widget):
        widget.bind("<MouseWheel>", self.on_mousewheel)
        widget.bind("<Button-4>", self.on_mousewheel)
        widget.bind("<Button-5>", self.on_mousewheel)
        for child in widget.winfo_children():
            self.bind_scroll_recursive(child)

    def on_mousewheel(self, event):
        # Handle macOS, Windows, and Linux scrolling behaviors naturally
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            if abs(event.delta) >= 120:
                amount = int(-1 * (event.delta / 120))
            else:
                amount = -1 if event.delta > 0 else 1
            self.canvas.yview_scroll(amount, "units")

    def popup_relation(self, event, recv, cast):
        val = self.grid_vars[recv][cast]["var"].get().strip()
        if not val: return

        try: float(val)
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid numeric strength.")
            return

        menu = tk.Menu(self.root, tearoff=0, font=FONTS["small"])
        for rel in RELATIONS:
            menu.add_command(label=rel.replace("_", " ").title(), command=lambda r=rel: self.set_relation(recv, cast, r))

        x = event.widget.winfo_rootx()
        y = event.widget.winfo_rooty() + event.widget.winfo_height()
        menu.post(x, y)

    def set_relation(self, recv, cast, rel):
        self.grid_vars[recv][cast]["rel"] = rel
        # Turn text green to provide instant visual confirmation
        self.grid_vars[recv][cast]["entry"].config(fg=COLORS["success"])

    def do_paste(self):
        self.mode = "paste"
        raw = pyperclip.paste()
        if not raw.strip():
            messagebox.showerror("Error", "Clipboard is empty. Copy JHora Aspects data first.")
            return
        try:
            self.final_output = clean_and_parse_aspects(raw)
            self.export_json()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse JHora data:\n{e}")

    def compile_manual_data(self):
        output = {"aspect_strengths": {"from_ascendant_to_houses": {}, "planet_to_planet_aspects": {}}}

        for recv in RECEIVERS:
            for cast in CASTERS:
                cell = self.grid_vars[recv][cast]
                strength_str = cell["var"].get().strip()
                if not strength_str: continue

                try: strength = float(strength_str)
                except ValueError: continue

                rel = cell["rel"]
                payload = {"strength": strength, "relation": rel}

                if recv.startswith("house_"):
                    if recv not in output["aspect_strengths"]["from_ascendant_to_houses"]:
                        output["aspect_strengths"]["from_ascendant_to_houses"][recv] = {}
                    output["aspect_strengths"]["from_ascendant_to_houses"][recv][cast] = payload
                else:
                    p_key = f"{recv}_receives_aspects"
                    if p_key not in output["aspect_strengths"]["planet_to_planet_aspects"]:
                        output["aspect_strengths"]["planet_to_planet_aspects"][p_key] = {}
                    output["aspect_strengths"]["planet_to_planet_aspects"][p_key][cast] = payload

        self.final_output = output

    def export_json(self):
        if self.mode == "manual": self.compile_manual_data()

        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], title="Export Aspects Schema")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f: json.dump(self.final_output, f, indent=4)
            messagebox.showinfo("Success", f"Aspects data safely exported to:\n{file_path}")
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AspectsApp(root)
    root.mainloop()
