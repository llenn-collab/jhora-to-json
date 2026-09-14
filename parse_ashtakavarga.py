import tkinter as tk
from tkinter import messagebox, filedialog
import json

PLANETS = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "lagna"]
ZODIAC = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces"
]

COLORS = {
    "bg_main": "#000000",
    "bg_card": "#060606",
    "text_primary": "#FFFFFF",
    "text_muted": "#F8FAFC",
    "border": "#E2E8F0",
}

FONTS = {
    "h1": ("Helvetica", 18, "bold"),
    "h2": ("Helvetica", 14, "bold"),
    "body": ("Helvetica", 11),
    "label": ("Helvetica", 11, "bold"),
    "input": ("Helvetica", 12)
}

class AshtakavargaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JHora Ashtakavarga Ingestion")
        self.root.geometry("400x680")
        self.root.resizable(False, False)
        self.root.configure(bg=COLORS["bg_main"])

        self.final_output = None

        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        self.root.focus_force()

        self.current_idx = 0
        self.bav_data = {p: {s: 0 for s in ZODIAC} for p in PLANETS}
        self.entries = []
        self.sign_vars = []

        self.create_ui()
        self.load_screen()

    def create_ui(self):
        self.header_frame = tk.Frame(self.root, bg=COLORS["bg_main"], pady=20)
        self.header_frame.pack(fill="x")

        self.header_var = tk.StringVar()
        header_lbl = tk.Label(
            self.header_frame, textvariable=self.header_var,
            font=FONTS["h1"], bg=COLORS["bg_main"], fg=COLORS["text_primary"]
        )
        header_lbl.pack()

        self.instructions_var = tk.StringVar()
        instructions = tk.Label(
            self.header_frame, textvariable=self.instructions_var,
            font=FONTS["body"], bg=COLORS["bg_main"], fg=COLORS["text_muted"]
        )
        instructions.pack(pady=(5, 0))

        self.list_frame = tk.Frame(self.root, bg=COLORS["bg_card"], bd=1, relief="solid")
        self.list_frame.pack(fill="both", expand=True, padx=40, pady=10)

        for i, sign in enumerate(ZODIAC):
            row_frame = tk.Frame(self.list_frame, bg=COLORS["bg_card"])
            row_frame.pack(fill="x", pady=6, padx=15)

            lbl = tk.Label(
                row_frame, text=sign.title(), font=FONTS["label"],
                bg=COLORS["bg_card"], fg=COLORS["text_primary"], width=12, anchor="w"
            )
            lbl.pack(side="left")

            var = tk.StringVar(value="0")
            var.trace_add("write", lambda name, index, mode, v=var: self.enforce_limits(v))
            self.sign_vars.append(var)

            entry = tk.Entry(
                row_frame, textvariable=var, width=6, justify="center",
                font=FONTS["input"], bg=COLORS["bg_main"], fg=COLORS["text_primary"],
                relief="flat", highlightbackground=COLORS["border"], highlightthickness=1
            )
            entry.pack(side="right")
            entry.bind('<Return>', lambda e, idx=i: self.on_enter(e, idx))
            entry.bind('<FocusIn>', lambda e, widget=entry: widget.select_range(0, tk.END))
            self.entries.append(entry)

        self.preview_frame = tk.Frame(self.root, bg=COLORS["bg_card"], bd=1, relief="solid")
        self.preview_labels = {}

        for i, sign in enumerate(ZODIAC):
            r, c = divmod(i, 2)
            p_row = tk.Frame(self.preview_frame, bg=COLORS["bg_card"])
            p_row.grid(row=r, column=c, sticky="nsew", padx=15, pady=12)

            tk.Label(
                p_row, text=f"{sign.title()}:", font=FONTS["body"],
                bg=COLORS["bg_card"], fg=COLORS["text_muted"]
            ).pack(side="left")

            val_lbl = tk.Label(
                p_row, text="0", font=FONTS["label"],
                bg=COLORS["bg_card"], fg=COLORS["text_primary"]
            )
            val_lbl.pack(side="right", padx=(5, 0))
            self.preview_labels[sign] = val_lbl

        btn_frame = tk.Frame(self.root, bg=COLORS["bg_main"], pady=20)
        btn_frame.pack(fill="x", padx=40)

        self.btn_back = tk.Button(
            btn_frame, text="< Back", command=self.prev_screen,
            font=FONTS["label"], width=8, cursor="hand2"
        )
        self.btn_back.pack(side="left")

        self.btn_next = tk.Button(
            btn_frame, text="Next >", command=self.next_screen,
            font=FONTS["label"], width=12, cursor="hand2"
        )
        self.btn_next.pack(side="right")

    def enforce_limits(self, var):
        val = var.get()
        if not val: return
        clean_val = "".join(filter(str.isdigit, val))
        if not clean_val: var.set("")
        elif int(clean_val) > 8: var.set("8")
        elif clean_val != val: var.set(clean_val)

    def on_enter(self, event, current_idx):
        if current_idx < 11: self.entries[current_idx + 1].focus_set()
        else: self.next_screen()

    def save_current_data(self):
        if self.current_idx < len(PLANETS):
            planet = PLANETS[self.current_idx]
            for i, sign in enumerate(ZODIAC):
                val = self.sign_vars[i].get()
                self.bav_data[planet][sign] = int(val) if val else 0

    def load_screen(self):
        if self.current_idx < len(PLANETS):
            self.preview_frame.pack_forget()
            self.list_frame.pack(fill="both", expand=True, padx=40, pady=10)

            planet = PLANETS[self.current_idx]
            self.header_var.set(f"Planet: {planet.upper()}")
            self.instructions_var.set("Enter points (0-8). Press 'Enter' to step down. Values auto-clamp to 0–8.")

            for i, sign in enumerate(ZODIAC):
                self.sign_vars[i].set(str(self.bav_data[planet][sign]))

            self.btn_back.config(state="normal" if self.current_idx > 0 else "disabled")
            self.btn_next.config(text="Next >")

            self.entries[0].focus_set()
            self.entries[0].select_range(0, tk.END)
        else:
            self.list_frame.pack_forget()
            self.preview_frame.pack(fill="both", expand=True, padx=20, pady=10)
            self.header_var.set("SAV Preview")
            self.instructions_var.set("Review calculated Samudayashtakavarga.")

            sav_payload = self.calculate_sav()
            for sign in ZODIAC:
                self.preview_labels[sign].config(text=str(sav_payload[sign]))

            self.btn_next.config(text="Export JSON")

    def calculate_sav(self):
        sav = {sign: 0 for sign in ZODIAC}
        for planet, p_data in self.bav_data.items():
            if planet == "lagna":
                continue # Lagna BAV is tracked but strictly excluded from SAV sum
            for sign, val in p_data.items():
                sav[sign] += val
        return sav

    def prev_screen(self):
        if self.current_idx > 0:
            self.save_current_data()
            self.current_idx -= 1
            self.load_screen()

    def next_screen(self):
        self.save_current_data()
        if self.current_idx < len(PLANETS):
            self.current_idx += 1
            self.load_screen()
        else:
            self.export_json()

    def export_json(self):
        sav_payload = self.calculate_sav()
        self.final_output = {
            "bhinnashtakavarga": self.bav_data,
            "samudayashtakavarga": sav_payload
        }

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            title="Export Ashtakavarga Schema"
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.final_output, f, indent=4)
            messagebox.showinfo("Success", f"Ashtakavarga data safely exported to:\n{file_path}")

            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AshtakavargaApp(root)
    root.mainloop()
