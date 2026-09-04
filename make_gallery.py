# make_gallery.py — generates gallery.html showing all current biome references.
# Run it (or press "Gallery" in the capture GUI) then open gallery.html.
import glob, json, os

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

settings = json.load(open("settings.json", encoding="utf-8"))
THUMBS = "gallery_thumbs"
os.makedirs(THUMBS, exist_ok=True)

RARE = [("pvc", "Pure vs Corrupt"), ("hvuh", "Holy vs Unholy"), ("void", "Void Infiltration"),
        ("angel", "Angel's Descent"), ("bene", "Blinding Light"), ("cult", "Cultist Legion"),
        ("asta", "Shrouding Darkness")]
SKIP = [("moon", "Night"), ("flame", "Flare"), ("forest", "Nature"), ("storm", "Stormsurge"),
        ("blizzard", "Blizzard"), ("irradiated", "Irradiated"), ("star", "Starry Night")]
BASIC = [("normal", "Grasslands"), ("DIDNT_LOAD", "Loading screen")]
STALE = set()  # play-camera refs that should be re-captured (currently none)

def status(name):
    if name == "DIDNT_LOAD":
        return "OK" if os.path.exists(f"images/{name}.png") else "MISSING"
    if name in STALE:
        return "RECAPTURE"
    if os.path.exists(f"images/{name}.png"):
        return "OK"
    return "MISSING"

def thumb(name, src, w=220):
    out = os.path.join(THUMBS, name + ".jpg")
    if not os.path.exists(src):
        return None
    if not os.path.exists(out) or os.path.getmtime(src) > os.path.getmtime(out):
        from PIL import Image
        im = Image.open(src).convert("RGB")
        im.thumbnail((w, w * 9 // 16))
        im.save(out, quality=80)
    return os.path.relpath(out, ROOT)

badge = {"OK": ("#1f8f3d", "#d5f5e3"), "MISSING": ("#b3261e", "#fdecea"), "RECAPTURE": ("#b26a00", "#fff3d6")}

def card(name, label):
    st = status(name)
    fg, bg = badge[st]
    full = thumb(name, f"images/{name}.png")
    ground = thumb(name + "_g", f"images/{name}_ground.png")
    extra = ""
    if os.path.isdir(f"images/{name}"):
        n = len(glob.glob(f"images/{name}/*.png"))
        extra = f'<div class="extra">+{n} auto-captured</div>' if n else ""
    g = f'<img class="g" src="{ground}" title="horizon color">' if ground else '<div class="g none">no ground ref</div>'
    f = f'<img class="f" src="{full}">' if full else '<div class="f none">no reference yet</div>'
    return f"""<div class="card">
  <div class="head"><b>{label}</b> <span class="badge" style="background:{bg};color:{fg}">{st}</span></div>
  {f}{extra}
  <div class="groundrow">horizon: {g}</div>
</div>"""

def section(title, entries):
    return f"<h2>{title}</h2><div class='grid'>" + "".join(card(n, l) for n, l in entries) + "</div>"

html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Biome Hopper - references</title>
<style>
 body {{ font-family: Segoe UI, sans-serif; background:#14161a; color:#ddd; margin:24px }}
 h1 {{ color:#fff }} h2 {{ color:#7aa7ff; margin-top:28px }}
 .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(230px,1fr)); gap:14px }}
 .card {{ background:#1d2128; border:1px solid #2c313a; border-radius:8px; padding:10px }}
 .head {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:8px }}
 .badge {{ padding:2px 8px; border-radius:10px; font-size:11px; font-weight:bold }}
 .f {{ width:100%; border-radius:4px; cursor:pointer }}
 .g {{ width:100%; border-radius:4px; margin-top:2px }}
 .none {{ color:#666; font-size:11px; padding:6px 0 }}
 .groundrow {{ font-size:11px; color:#999; margin-top:6px }}
 .extra {{ font-size:11px; color:#8f8; margin-top:4px }}
 .note {{ background:#23262e; border-left:3px solid #7aa7ff; padding:10px 14px; margin-top:20px; border-radius:4px }}
</style></head><body>
<h1>Biome Hopper — current references</h1>
{section("RARE (farm these)", RARE)}
{section("SKIP (rejoin instead)", SKIP)}
{section("BASIC", BASIC)}
<div class="note"><b>captures/</b> = watch-mode raw frames &nbsp;·&nbsp; <b>unknowns/</b> = frames the macro couldn't identify &nbsp;·&nbsp; <b>images/&lt;biome&gt;/</b> = extra auto-captured refs<br>
Recapture anything marked <span style="color:#b26a00;font-weight:bold">RECAPTURE</span> via the capture GUI when that biome is announced.</div>
</body></html>"""

with open("gallery.html", "w", encoding="utf-8") as f:
    f.write(html)
print("gallery.html written - open it in a browser")
