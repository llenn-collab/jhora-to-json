import tkinter as tk
from tkinter import messagebox, filedialog
import json

SCREENS = [
    {"id": "arudhas", "title": "Bhavapada (Arudhas)", "items": ["AL", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "A10", "A11", "A12"]},
    {"id": "graha_arudhas", "title": "Graha Arudhas", "items": ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu"]},
    {"id": "varnadas", "title": "Varnada Lagnas", "items": ["V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10", "V11", "V12"]}
]

HOUSE_OPTIONS = ["None"] + [str(i) for i in range(1, 13)]

COLORS = {
    "bg_main": "#121212", "bg_card": "#1E1E1E", "text_primary": "#FFFFFF",
    "text_muted": "#A1A1AA", "border": "#27272A", "dropdown_bg": "#27272A"
}

FONTS = {
    "h1": ("Helvetica", 20, "bold"), "label": ("Helvetica", 14, "bold"), "body": ("Helvetica", 14)
}

class ArudhaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JHora Arudha Matrix Ingestion")
        self.root.geometry("450x780")
        self.root.resizable(False, False)
        self.root.configure(bg=COLORS["bg_main"])

        self.final_output = {}

        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        self.root.focus_force()

        self.current_idx = 0
        self.vars = {screen["id"]: {} for screen in SCREENS}

        for screen in SCREENS:
            for item in screen["items"]:
                self.vars[screen["id"]][item] = tk.StringVar(value="None")

        self.create_ui()
        self.load_screen()

    def create_ui(self):
        self.header_frame = tk.Frame(self.root, bg=COLORS["bg_main"], pady=20)
        self.header_frame.pack(fill="x")

        self.header_var = tk.StringVar()
        tk.Label(self.header_frame, textvariable=self.header_var, font=FONTS["h1"], bg=COLORS["bg_main"], fg=COLORS["text_primary"]).pack()
        tk.Label(self.header_frame, text="Select the house (1-12) for each point.\nLeave as 'None' to exclude from JSON.", font=("Helvetica", 12), bg=COLORS["bg_main"], fg=COLORS["text_muted"]).pack(pady=(5, 0))

        self.list_frame = tk.Frame(self.root, bg=COLORS["bg_card"], bd=1, relief="solid", highlightbackground=COLORS["border"], highlightthickness=1)
        self.list_frame.pack(fill="both", expand=True, padx=40, pady=10)

        btn_frame = tk.Frame(self.root, bg=COLORS["bg_main"], pady=20)
        btn_frame.pack(fill="x", padx=40)

        self.btn_back = tk.Button(btn_frame, text="< Back", command=self.prev_screen, font=FONTS["label"], width=8, cursor="hand2")
        self.btn_back.pack(side="left")

        self.btn_next = tk.Button(btn_frame, text="Next >", command=self.next_screen, font=FONTS["label"], width=12, cursor="hand2")
        self.btn_next.pack(side="right")

        self.btn_skip = tk.Button(btn_frame, text="Clear & Skip", command=self.skip_screen, font=("Helvetica", 12), width=12, cursor="hand2")
        self.btn_skip.pack(side="bottom", pady=(20, 0))

    def load_screen(self):
        for widget in self.list_frame.winfo_children(): widget.destroy()

        screen_data = SCREENS[self.current_idx]
        self.header_var.set(screen_data["title"])

        for item in screen_data["items"]:
            row_frame = tk.Frame(self.list_frame, bg=COLORS["bg_card"])
            row_frame.pack(fill="x", pady=6, padx=25)

            display_text = item.capitalize() if len(item) > 3 else item
            tk.Label(row_frame, text=display_text, font=FONTS["label"], bg=COLORS["bg_card"], fg=COLORS["text_primary"], width=10, anchor="w").pack(side="left")

            var = self.vars[screen_data["id"]][item]
            dropdown = tk.OptionMenu(row_frame, var, *HOUSE_OPTIONS)
            dropdown.config(bg=COLORS["dropdown_bg"], fg=COLORS["text_primary"], activebackground=COLORS["border"], activeforeground=COLORS["text_primary"], font=FONTS["body"], highlightthickness=0, relief="flat", width=6)
            dropdown["menu"].config(bg=COLORS["dropdown_bg"], fg=COLORS["text_primary"], font=FONTS["body"])
            dropdown.pack(side="right")

        self.btn_back.config(state="normal" if self.current_idx > 0 else "disabled")

        if self.current_idx == len(SCREENS) - 1:
            self.btn_next.config(text="Export JSON")
            self.btn_skip.pack_forget()
        else:
            self.btn_next.config(text="Next >")
            self.btn_skip.pack(side="bottom", pady=(20, 0))

    def skip_screen(self):
        for var in self.vars[SCREENS[self.current_idx]["id"]].values(): var.set("None")
        self.next_screen()

    def prev_screen(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self.load_screen()

    def next_screen(self):
        if self.current_idx < len(SCREENS) - 1:
            self.current_idx += 1
            self.load_screen()
        else:
            self.export_json()

    def export_json(self):
        final_payload = {}
        for screen in SCREENS:
            screen_id = screen["id"]
            screen_data = {}
            for item in screen["items"]:
                val = self.vars[screen_id][item].get()
                if val != "None": screen_data[item] = int(val)
            if screen_data: final_payload[screen_id] = screen_data

        self.final_output = final_payload
        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], title="Export Arudha Schema")
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f: json.dump(self.final_output, f, indent=4)
            messagebox.showinfo("Success", f"Arudha data safely saved to:\n{file_path}")
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ArudhaApp(root)
    root.mainloop()
