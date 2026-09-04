# capture_gui.py — one-click biome reference capture for the Biome Hopper
# Press the button of the biome that was JUST announced in chat.
# It respawns you, zooms out and snaps a reference at the macro's camera.
import json, os, subprocess, sys, threading, tkinter as tk
from tkinter import ttk, messagebox

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

# (name, display name, chat announcement, rarity note)
RARE = [
    ("pvc",   "Pure vs Corrupt",  "The war between pure and corrupt has started!", "1/750"),
    ("hvuh",  "Holy vs Unholy",   "The war between holy and unholy has started!", "1/1125"),
    ("void",  "Void Infiltration", "The void is infiltrating reality!", "1/2500"),
    ("angel", "Angel's Descent",  "The angels of the sky are descending!", "1/2500"),
    ("bene",  "Blinding Light",   "A bright light is blinding the world!", "1/5000"),
    ("cult",  "Cultist Legion",   "Your actions have brought imbalances to reality.", "1/7500"),
    ("asta",  "Shrouding Darkness", "The world is being shrouded in darkness!", "1/5000"),
]
SKIP = [
    ("moon",       "Night",          "The moon is rising!", "1/125"),
    ("flame",      "Flare",          "Magical flames have warped the island!", "1/180"),
    ("forest",     "Nature",         "The wind is sweeping life energy...", "1/180"),
    ("storm",      "Stormsurge",     "A powerful stormsurge has engulfed the island!", "1/180"),
    ("blizzard",   "Blizzard",       "An incredibly strong blizzard is freezing the island!", "1/180"),
    ("irradiated", "Irradiated",     "The island has been irradiated by an unknown wave of energy...", "1/600"),
    ("star",       "Starry Night",   "A bright blue moon illuminates the sky along with countless shooting stars...", "1/600"),
]
NORMAL = [("normal", "Grasslands", "(default biome - for the 'biome ended' check)", "-")]

# refs that were captured from a play camera before --resetcamera existed
STALE = set()

class App:
    def __init__(self, root):
        self.root = root
        root.title("Biome Hopper - Reference Capture")
        root.geometry("860x620")
        self.busy = set()
        self.buttons = {}
        self.status_lbls = {}

        top = ttk.Frame(root, padding=8)
        top.pack(fill="x")
        ttk.Label(top, text="When a biome is announced in chat, press its Capture button.",
                  font=("Segoe UI", 11, "bold")).pack(side="left")
        ttk.Button(top, text="Gallery", command=self.gallery).pack(side="right")
        ttk.Button(top, text="Refresh", command=self.refresh).pack(side="right")

    def gallery(self):
        try:
            subprocess.Popen([sys.executable, "make_gallery.py"])
            self.msg.config(text="generating gallery...")
            self.root.after(1500, lambda: (os.startfile("gallery.html"), self.msg.config(text="gallery opened")))
        except Exception as e:
            self.msg.config(text=f"gallery error: {e!r}")

        self.msg = ttk.Label(root, text="", foreground="#666")
        self.msg.pack(fill="x", padx=8)

        wrap = ttk.Frame(root)
        wrap.pack(fill="both", expand=True, padx=8, pady=4)
        canvas = tk.Canvas(wrap)
        scroll = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        self.table = ttk.Frame(canvas)
        self.table.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.table, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self.log = tk.Text(root, height=6, state="disabled", bg="#111", fg="#9f9", font=("Consolas", 9))
        self.log.pack(fill="x", padx=8, pady=(0, 8))
        self.build()
        self.refresh()

    def build(self):
        row = 0
        for col, txt, w in [(0, "BIOME", 150), (1, "CHAT ANNOUNCEMENT", 380), (2, "STATUS", 90), (3, "", 90)]:
            ttk.Label(self.table, text=txt, font=("Segoe UI", 9, "bold")).grid(row=row, column=col, sticky="w", padx=4, pady=2)

        def add_section(title, entries):
            nonlocal row
            row += 1
            ttk.Label(self.table, text=title, font=("Segoe UI", 9, "bold", "underline"), foreground="#37f") \
                .grid(row=row, column=0, columnspan=4, sticky="w", padx=4, pady=(8, 2))
            for name, label, ann, rarity in entries:
                row += 1
                ttk.Label(self.table, text=f"{label}  ({rarity})").grid(row=row, column=0, sticky="w", padx=4)
                ttk.Label(self.table, text=ann, foreground="#555").grid(row=row, column=1, sticky="w", padx=4)
                sl = ttk.Label(self.table, text="...", font=("Segoe UI", 9, "bold"))
                sl.grid(row=row, column=2, sticky="w", padx=4)
                self.status_lbls[name] = sl
                b = ttk.Button(self.table, text="Capture", width=10,
                               command=lambda n=name: self.capture(n))
                b.grid(row=row, column=3, padx=4)
                self.buttons[name] = b

        add_section("RARE - farm these (priority)", RARE)
        add_section("SKIP - rejoin instead", SKIP)
        add_section("BASIC", NORMAL)

    def refresh(self):
        for name, sl in self.status_lbls.items():
            if name in self.busy:
                continue
            if name in STALE:
                sl.config(text="RECAPTURE", foreground="#c60")
            elif os.path.exists(f"images/{name}.png"):
                sl.config(text="OK", foreground="#080")
            else:
                sl.config(text="MISSING", foreground="#c00")

    def log_line(self, text):
        self.log.config(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def macro_running(self):
        try:
            out = subprocess.run(["wmic", "process", "where", "name='python.exe'", "get", "commandline"],
                                 capture_output=True, text=True, timeout=10).stdout
            return "biome_hopper.py" in out
        except Exception:
            return False

    def capture(self, name):
        if name in self.busy:
            return
        if self.macro_running():
            if not messagebox.askyesno(
                    "Macro is running",
                    "The macro (biome_hopper.py) is active and will fight your key presses / kill Roblox "
                    "mid-cycle.\n\nPress F9 in the macro console to stop it first, then capture.\n\n"
                    "Continue capturing anyway?"):
                return
        self.busy.add(name)
        self.buttons[name].config(state="disabled")
        self.status_lbls[name].config(text="CAPTURING...", foreground="#00c")
        self.msg.config(text=f"Capturing {name} - respawning you, wait ~15s...")

        def work():
            try:
                p = subprocess.run([sys.executable, "capture.py", name, "--resetcamera"],
                                   capture_output=True, text=True, timeout=90)
                out = (p.stdout + p.stderr).strip()
                ok = os.path.exists(f"images/{name}.png")
                self.root.after(0, lambda: self.finish(name, ok, out))
            except Exception as e:
                self.root.after(0, lambda: self.finish(name, False, f"error: {e!r}"))

        threading.Thread(target=work, daemon=True).start()

    def finish(self, name, ok, out):
        self.busy.discard(name)
        self.buttons[name].config(state="normal")
        self.status_lbls[name].config(text="OK" if ok else "FAILED", foreground="#080" if ok else "#c00")
        self.msg.config(text=f"{name}: {'saved!' if ok else 'capture FAILED - see log'}")
        for line in out.splitlines()[-8:]:
            self.log_line(f"[{name}] {line}")
        self.refresh()

def main():
    root = tk.Tk()
    App(root)
    root.mainloop()

if __name__ == "__main__":
    main()
