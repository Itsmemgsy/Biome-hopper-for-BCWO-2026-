# settings_gui.py — review/edit macro settings before it runs.
# run_macro.bat opens this first; "Save & Run" starts the macro, "Cancel" doesn't.
import json, os, subprocess, sys, tkinter as tk
from tkinter import ttk, messagebox

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
SETTINGS = "settings.json"

BIOMES = [
    ("pvc", "Pure vs Corrupt", "1/750"),
    ("hvuh", "Holy vs Unholy", "1/1125"),
    ("void", "Void Infiltration", "1/2500"),
    ("angel", "Angel's Descent", "1/2500"),
    ("bene", "Blinding Light", "1/5000"),
    ("cult", "Cultist Legion", "1/7500"),
    ("asta", "Shrouding Darkness", "1/5000"),
    ("moon", "Night", "1/125"),
    ("flame", "Flare", "1/180"),
    ("forest", "Nature", "1/180"),
    ("storm", "Stormsurge", "1/180"),
    ("blizzard", "Blizzard", "1/180"),
    ("irradiated", "Irradiated", "1/600"),
    ("star", "Starry Night", "1/600"),
]

class App:
    def __init__(self, root):
        self.root = root
        root.title("Biome Hopper - settings")
        root.geometry("740x780")
        self.settings = json.load(open(SETTINGS, encoding="utf-8"))
        self.var = {}
        self.build()

    def build(self):
        f = ttk.LabelFrame(self.root, text="Links & notifications", padding=8)
        f.pack(fill="x", padx=8, pady=6)
        ttk.Label(f, text="VIP link:").grid(row=0, column=0, sticky="w")
        self.var["vip"] = tk.StringVar(value=self.settings.get("vip", ""))
        ttk.Entry(f, textvariable=self.var["vip"], width=85).grid(row=0, column=1, sticky="we", padx=8)
        ttk.Label(f, text="Discord webhook (None = off):").grid(row=1, column=0, sticky="w")
        self.var["webhook"] = tk.StringVar(value=self.settings.get("webhook", "None"))
        ttk.Entry(f, textvariable=self.var["webhook"], width=85).grid(row=1, column=1, sticky="we", padx=8)
        ttk.Label(f, text="Discord user ID (for pings):").grid(row=2, column=0, sticky="w")
        self.var["userid"] = tk.StringVar(value=self.settings.get("userid", "0"))
        ttk.Entry(f, textvariable=self.var["userid"], width=85).grid(row=2, column=1, sticky="we", padx=8)
        f.columnconfigure(1, weight=1)

        g = ttk.LabelFrame(self.root, text="Behaviour", padding=8)
        g.pack(fill="x", padx=8, pady=6)
        self.var["afkfarm"] = tk.BooleanVar(value=bool(self.settings.get("afkfarm", True)))
        ttk.Checkbutton(g, text="AFK farm rare biomes until they end", variable=self.var["afkfarm"]).grid(row=0, column=0, sticky="w")
        self.var["resetuponload"] = tk.BooleanVar(value=bool(self.settings.get("resetuponload", True)))
        ttk.Checkbutton(g, text="Respawn + zoom out after joining", variable=self.var["resetuponload"]).grid(row=1, column=0, sticky="w")
        self.var["killbrowser"] = tk.BooleanVar(value=bool(self.settings.get("killbrowser", True)))
        ttk.Checkbutton(g, text="Close Chrome after the game loads", variable=self.var["killbrowser"]).grid(row=2, column=0, sticky="w")
        self.var["pingunknown"] = tk.BooleanVar(value=bool(self.settings.get("pingunknown", True)))
        ttk.Checkbutton(g, text="Ping Discord for unknown biomes (safety net)", variable=self.var["pingunknown"]).grid(row=3, column=0, sticky="w")
        ttk.Label(g, text="Seconds to wait after killing Roblox before rejoining:").grid(row=4, column=0, sticky="w", pady=2)
        self.var["killcooldown"] = tk.StringVar(value=str(self.settings.get("killcooldown", 3)))
        ttk.Entry(g, textvariable=self.var["killcooldown"], width=8).grid(row=4, column=1, sticky="w")
        ttk.Label(g, text="Seconds to watch each server (20-120):").grid(row=5, column=0, sticky="w", pady=2)
        self.var["waitbeforerejoin"] = tk.StringVar(value=str(self.settings.get("waitbeforerejoin", 60)))
        ttk.Entry(g, textvariable=self.var["waitbeforerejoin"], width=8).grid(row=5, column=1, sticky="w")

        b = ttk.LabelFrame(self.root, text="Targeted biomes", padding=8)
        b.pack(fill="both", expand=True, padx=8, pady=6)
        ttk.Label(b, text="Biome", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", padx=4)
        ttk.Label(b, text="Action", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w", padx=4)
        ttk.Label(b, text="Odds", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, sticky="w", padx=4)
        self.var["biome"] = {}
        rare = self.settings.get("rarebiomes", {})
        skip = self.settings.get("skippablebiomes", {})
        for i, (name, label, odds) in enumerate(BIOMES, start=1):
            current = "farm" if name in rare else ("skip" if name in skip else "off")
            ttk.Label(b, text=label).grid(row=i, column=0, sticky="w", padx=4)
            cb = ttk.Combobox(b, values=["Farm (rare)", "Skip", "Off"], state="readonly", width=14)
            cb.current(["farm", "skip", "off"].index(current))
            cb.grid(row=i, column=1, sticky="w", padx=4)
            self.var["biome"][name] = cb
            ttk.Label(b, text=odds).grid(row=i, column=2, sticky="w", padx=4)
        note = ("Note: pvc / hvuh / asta share the same sky - they are told apart by ocean color, "
                "so they each need their horizon reference captured (the GUI capture does this).")
        ttk.Label(b, text=note, foreground="#888", wraplength=690).grid(
            row=len(BIOMES) + 1, column=0, columnspan=3, sticky="w", padx=4, pady=10)

        btns = ttk.Frame(self.root)
        btns.pack(fill="x", padx=8, pady=10)
        ttk.Button(btns, text="Save & Run macro", command=self.save_and_run).pack(side="left")
        ttk.Button(btns, text="Save only", command=self.save_only).pack(side="left", padx=8)
        ttk.Button(btns, text="Cancel", command=lambda: sys.exit(1)).pack(side="right")

    def collect(self):
        s = self.settings
        s["vip"] = self.var["vip"].get().strip()
        s["webhook"] = self.var["webhook"].get().strip()
        s["userid"] = self.var["userid"].get().strip()
        s["afkfarm"] = self.var["afkfarm"].get()
        s["resetuponload"] = self.var["resetuponload"].get()
        s["killbrowser"] = self.var["killbrowser"].get()
        s["pingunknown"] = self.var["pingunknown"].get()
        try:
            s["killcooldown"] = max(0, int(self.var["killcooldown"].get()))
        except ValueError:
            messagebox.showerror("Invalid", "killcooldown must be a number")
            return None
        try:
            s["waitbeforerejoin"] = min(120, max(20, int(self.var["waitbeforerejoin"].get())))
        except ValueError:
            messagebox.showerror("Invalid", "waitbeforerejoin must be a number")
            return None
        rare, skip = {}, {}
        for name, cb in self.var["biome"].items():
            v = cb.get()
            if v.startswith("Farm"):
                rare[name] = 0
            elif v.startswith("Skip"):
                skip[name] = 0
        s["rarebiomes"] = rare
        s["skippablebiomes"] = skip
        return s

    def write(self, s):
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump(s, f, indent=1)

    def save_only(self):
        s = self.collect()
        if s is None:
            return
        self.write(s)
        messagebox.showinfo("Saved", "settings.json updated")

    def save_and_run(self):
        s = self.collect()
        if s is None:
            return
        if not s["vip"].startswith("http"):
            messagebox.showerror("Invalid", "VIP link looks wrong - it must start with http")
            return
        if s["webhook"] != "None" and not s["webhook"].startswith("http"):
            messagebox.showerror("Invalid", "Webhook must be 'None' or a https://... link")
            return
        if self.macro_running():
            if not messagebox.askyesno(
                    "Macro is running",
                    "biome_hopper.py is already running - starting another instance "
                    "would fight over the same game.\n\nStop it first (F9), then retry.\n\n"
                    "Continue anyway?"):
                return
        self.write(s)
        open("run_flag.txt", "w").write("run")  # tells run_macro.bat to start the macro
        self.root.destroy()

    def macro_running(self):
        try:
            out = subprocess.run(["wmic", "process", "where", "name='python.exe'", "get", "commandline"],
                                 capture_output=True, text=True, timeout=10).stdout
            return "biome_hopper.py" in out
        except Exception:
            return False

def main():
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
