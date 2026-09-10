#BIOME HOPPER 3000!!!!! v2
# Adapted from https://github.com/debelopguy/BiomeHopper
# v2 fixes for this machine:
#  - DPI-aware: screenshots/window rects are in PHYSICAL pixels (2560x1440 @125% scaling)
#  - Roblox window is resized to a 1600x900 CLIENT area each loop, so all coordinates
#    map 1:1 from the 1600x900 reference space (images/*.png) to the real screen
#  - clicks go through pyautogui with integer, mapped coordinates (the old `mouse moveTo`
#    got float coords like 800.0x450.0 which int.Parse() rejected, so every move silently
#    failed and clicks landed at the raw cursor position)
#  - biome detection uses per-channel tolerance instead of exact pixel equality
#    (new game version renders slightly differently than the repo's screenshots)
#  - "loaded" detection is reference-free (hotbar strip variance + frame change),
#    no OpenCV / locateOnScreen needed anymore
#  - discord_webhook import is optional (settings "webhook":"None" still works)
#  - stop key exits cleanly instead of os.kill(getppid()) which nuked the terminal
#  - every step prints to the console so nothing fails silently

import ctypes, json, os, random, subprocess, sys, time
from ctypes import wintypes

ctypes.windll.user32.SetProcessDPIAware()
# keep the display awake so screenshots never go black from a sleeping screen
_ES_CONTINUOUS = 0x80000000
_ES_DISPLAY_REQUIRED = 0x00000002
ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS | _ES_DISPLAY_REQUIRED)
import pyautogui
pyautogui.FAILSAFE = False  # an AFK macro must not abort because the mouse rests in a corner
from PIL import Image

try:
    import discord_webhook
except ImportError:
    discord_webhook = None

settings = json.load(open("./settings.json", encoding="utf-8"))
print("yooooooo loaded! beginning in 2 seconds.")
time.sleep(2)

user32 = ctypes.windll.user32
REF_W, REF_H = 1600, 900

# ---------------------------------------------------------------- window stuff

def find_roblox_hwnd():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq RobloxPlayerBeta.exe",
                          "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    lines = [l for l in out.strip().splitlines() if "RobloxPlayerBeta" in l]
    if not lines:
        return None
    pids = {int(l.split(",")[1].strip('"')) for l in lines}
    found = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value in pids and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True
    user32.EnumWindows(cb, 0)
    return found[0] if found else None

def client_rect(hwnd):
    cr = wintypes.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(cr))
    pt = wintypes.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y, cr.right, cr.bottom

def ensure_1600x900(hwnd):
    """Resize the Roblox window so its CLIENT area is exactly 1600x900 at (0,0)."""
    ox, oy, cw, ch = client_rect(hwnd)
    if (cw, ch) == (REF_W, REF_H):
        return ox, oy, cw, ch
    if user32.IsZoomed(hwnd):
        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        time.sleep(0.5)
    wr = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(wr))
    # fullscreen-exclusive games can't be GDI-captured (black screenshots) and
    # ignore MoveWindow. Detect it: no window chrome (client == window rect)
    # and covering the whole screen. F11 toggles back to windowed.
    sw = user32.GetSystemMetrics(0)  # SM_CXSCREEN
    sh = user32.GetSystemMetrics(1)  # SM_CYSCREEN
    if (wr.right - wr.left) >= sw - 4 and (wr.bottom - wr.top) >= sh - 4 \
            and abs((ox - wr.left)) <= 1 and abs((oy - wr.top)) <= 1:
        print("* fullscreen detected - pressing F11 to go windowed")
        keyboard.press_and_release("f11")
        time.sleep(2)
        ox, oy, cw, ch = client_rect(hwnd)
        if (cw, ch) == (REF_W, REF_H):
            return ox, oy, cw, ch
        user32.GetWindowRect(hwnd, ctypes.byref(wr))
    chrome_l = ox - wr.left
    chrome_r = wr.right - (ox + cw)
    chrome_t = oy - wr.top
    chrome_b = wr.bottom - (oy + ch)
    user32.MoveWindow(hwnd, 0, 0, REF_W + chrome_l + chrome_r,
                      REF_H + chrome_t + chrome_b, True)
    time.sleep(2.5)
    return client_rect(hwnd)

# coords in 1600x900 reference space -> physical screen
g_ox, g_oy, g_sx, g_sy = 0, 0, 1.0, 1.0
g_hwnd = None

def set_view(hwnd):
    global g_ox, g_oy, g_sx, g_sy, g_hwnd
    g_hwnd = hwnd
    ox, oy, cw, ch = ensure_1600x900(hwnd)
    g_ox, g_oy = ox, oy
    g_sx, g_sy = cw / REF_W, ch / REF_H

def to_phys(x, y):
    return int(g_ox + x * g_sx), int(g_oy + y * g_sy)

def frame_is_black(shot):
    """True when a capture is pure black (display asleep, fullscreen overlay,
    or a transition) - nothing useful can be detected from it."""
    small = shot.resize((80, 45)).convert("L")
    px = list(small.getdata())
    mean = sum(px) / len(px)
    var = sum((v - mean) ** 2 for v in px) / len(px)
    return mean < 10 and var < 20

def snap_viewport():
    """Screenshot the game viewport. Re-checks the window rect first: Roblox
    restores its OWN saved window size when the game reloads after joining,
    so the 1600x900 resize has to be re-applied every time it changes.
    Retries briefly when the capture comes back black."""
    if g_hwnd is not None:
        try:
            ox, oy, cw, ch = client_rect(g_hwnd)
            if cw > 0 and ch > 0 and ((cw, ch) != (REF_W, REF_H) or (ox, oy) != (g_ox, g_oy)):
                set_view(g_hwnd)  # re-resize + remap (only sleeps when actually resizing)
        except Exception:
            pass  # stale handle (Roblox was killed) - just use the old mapping
    for _ in range(3):
        shot = pyautogui.screenshot()
        view = shot.crop((g_ox, g_oy, g_ox + int(REF_W * g_sx), g_oy + int(REF_H * g_sy))).resize((REF_W, REF_H))
        if not frame_is_black(view):
            return view
        time.sleep(1)
    return view

# ---------------------------------------------------------------- helpers

def returnctime():
    import datetime
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

def sendbywebhook(the):
    if discord_webhook is None or settings.get("webhook") == "None":
        print("[webhook-off]", the.get("content", "")[:120])
        return
    try:
        the["content"] = the["content"] + " (" + str(returnctime()) + ")"
        wh = discord_webhook.DiscordWebhook(url=settings["webhook"], content=the["content"])
        if "file" in the:
            with open(the["file"], "rb") as f:
                wh.add_file(file=f.read(), filename=the["file"])
        wh.execute()
    except Exception as e:
        print("[webhook-error]", e)

def click(x, y, clicks=1, interval=None):
    px, py = to_phys(x, y)
    for _ in range(clicks):
        pyautogui.click(px, py)
        if interval is not None:
            time.sleep(interval)

# ---------------------------------------------------------------- detection

def isimagesame(biomescreenshot, currentscreen):
    """Compare via random sky-band samples with per-channel tolerance.
    Returns the match FRACTION (0..1) - the caller decides the threshold.
    biomescreenshot is a cached sky band (x200-1560, y0-150 of the frame),
    so full-frame sample coords are remapped into band space."""
    tol = settings.get("biomepixeltolerance", 12)
    checks = settings["biomepixelchecks"]
    misses_allowed = checks - int(settings["biomepixelthreshold"])
    grace = 0
    misses = 0
    for _ in range(checks):
        # sample the TOP SKY BAND only (y 0..150): avoids game UI, the ground
        # and summons that stand at ground level; the biome sky is up there.
        pixel = (random.randrange(200, 1560), random.randrange(0, 150))
        a = currentscreen.getpixel(pixel)
        b = biomescreenshot.getpixel((pixel[0] - 200, pixel[1]))
        if abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol and abs(a[2] - b[2]) <= tol:
            grace += 1
        else:
            misses += 1
            if misses > misses_allowed:
                break  # threshold unreachable - stop early
    return grace / checks

import glob as _glob

_ref_cache = {}  # biome -> (signature, [sky-band images])
MAX_AUTO_REFS = 4  # per biome: curated main ref + this many random auto-refs

def sky_band(img):
    return img.crop((200, 0, 1560, 150))

def load_refs(biome):
    """Curated main ref + a few random auto-refs, cached as small sky bands.
    Full 1600x900 frames would eat ~1.6GB RAM for ~400 refs; bands are ~0.6MB
    each (~50MB total). The random subset re-picks whenever the folder
    changes, so every cycle sees fresh variety."""
    single = f"./images/{biome}.png"
    folder = f"./images/{biome}"
    try:
        sig = (os.path.getmtime(single) if os.path.exists(single) else 0,
               tuple(sorted(os.listdir(folder))) if os.path.isdir(folder) else ())
    except OSError:
        sig = (0, ())
    hit = _ref_cache.get(biome)
    if hit is not None and hit[0] == sig:
        return hit[1]
    paths = []
    if os.path.exists(single):
        paths.append(single)
    autos = []
    if os.path.isdir(folder):
        autos = [os.path.join(folder, p) for p in sorted(os.listdir(folder))
                 if p.endswith(".png") and not p.endswith("_ground.png")]
    if len(autos) > MAX_AUTO_REFS:
        autos = random.sample(autos, MAX_AUTO_REFS)
    paths += autos
    refs = [sky_band(Image.open(p).convert("RGB")) for p in paths]
    _ref_cache[biome] = (sig, refs)
    return refs

def full_ref(biome):
    """A full-frame reference (for the mid-frame zoom check, loaded on demand
    instead of cached - it runs at most a few times per cycle)."""
    p = f"./images/{biome}.png"
    if os.path.exists(p):
        return Image.open(p).convert("RGB")
    folder = f"./images/{biome}"
    if os.path.isdir(folder):
        for f in sorted(os.listdir(folder)):
            if f.endswith(".png") and not f.endswith("_ground.png"):
                return Image.open(os.path.join(folder, f)).convert("RGB")
    return None

_ground_cache = {}  # name -> mean color (ground refs never change mid-run)

def ground_ref_mean(name):
    hit = _ground_cache.get(name)
    if hit is not None:
        return hit
    ref_path = f"./images/{name}_ground.png"
    if not os.path.exists(ref_path):
        return None
    ref = Image.open(ref_path).convert("RGB")
    m = ground_mean_color(ref)
    _ground_cache[name] = m
    return m

def best_biome_match(currentscreen, names):
    """Return (best_biome_name, best_score). Picks the ref with the highest
    match fraction instead of 'any ref above threshold', so shared-looking
    dark skies (star/void/loading...) resolve to the closest one."""
    best_name, best_score = None, 0.0
    for name in names:
        for ref in load_refs(name):
            s = isimagesame(ref, currentscreen)
            if s > best_score:
                best_name, best_score = name, s
    return best_name, best_score

def ground_mean_color(img):
    """Mean RGB of the horizon band (ocean/beach zone) - used to tell apart
    biomes that share a skybox (pvc/hvuh/asta: purple/red/black ocean).
    Accepts a full 1600x900 frame OR an already-cropped ground band."""
    if img.size == (REF_W, REF_H):
        band = img.crop((200, 380, 1560, 520))
    else:
        band = img  # already the ground crop
    band = band.resize((68, 7))
    px = list(band.getdata())
    return tuple(sum(c[i] for c in px) // len(px) for i in range(3))

def resolve_shared_sky(best, currentscreen):
    """If the sky match belongs to a shared-sky group, use the horizon color
    to pick the exact biome. The sky can match ANY member's reference (they
    show the same skybox), so the group is looked up by member, not by key.
    Classification is hue-based first (purple vs red are far apart in hue),
    distance-based as a fallback."""
    group = None
    for members in settings.get("sharedskies", {}).values():
        if best in members:
            group = members
            break
    if not group:
        return best
    mean = ground_mean_color(currentscreen)
    candidates = []
    for n in group:
        rm = ground_ref_mean(n)
        if rm is None:
            continue
        candidates.append((n, rm))
    if len(candidates) == 1:
        return candidates[0][0]
    # hue dominance: purple has blue dominant, red has red dominant
    if mean[2] > mean[1] + 25 and mean[2] > mean[0]:
        for n, rm in candidates:
            if rm[2] > rm[1] + 25 and rm[2] > rm[0]:
                return n
    if mean[0] > mean[1] + 25 and mean[0] > mean[2]:
        for n, rm in candidates:
            if rm[0] > rm[1] + 25 and rm[0] > rm[2]:
                return n
    # ambiguous band: nearest reference color wins
    best_name, best_dist = None, 10**9
    for n, rm in candidates:
        d = max(abs(mean[i] - rm[i]) for i in range(3))
        if d < best_dist:
            best_dist, best_name = d, n
    if best_name is not None and best_dist < 60:
        return best_name
    return best

# ---------------------------------------------------------------- view validation

def band_lum(shot, y0, y1):
    b = shot.crop((200, y0, 1560, y1)).convert("L")
    px = list(b.getdata())
    return sum(px) / len(px)

def mid_band_match(ref, cur, n=200, tol=16):
    """How well the frame's mid section matches the reference's - a zoomed-in
    camera puts the character there and scores near 0, the macro camera ~0.9+."""
    m = 0
    for _ in range(n):
        x = random.randrange(200, 1560)
        y = random.randrange(350, 700)
        a = cur.getpixel((x, y))
        b = ref.getpixel((x, y))
        if abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol and abs(a[2] - b[2]) <= tol:
            m += 1
    return m / n

def zoom_out():
    for _ in range(20):
        keyboard.press("o")
        time.sleep(0.1)
    keyboard.release("o")
    time.sleep(1)

def looks_indoor(shot):
    """Lobby wall / camera-inside-geometry signature: grey and uniform from
    the top band down through the mid frame. Dark biomes (void/star) have
    high saturation or a bright island below the dark sky, so they don't
    trigger this."""
    top = band_lum(shot, 0, 150)
    mid = band_lum(shot, 300, 650)
    top_sat = shot.crop((200, 0, 1560, 150)).convert("HSV").split()[1]
    sp = list(top_sat.getdata())
    sat = sum(sp) / len(sp)
    return sat < 35 and abs(top - mid) < 25 and 50 < (top + mid) / 2 < 150

def view_state(shot):
    """Classify the current camera view:
    'indoor'  -> lobby wall fills the screen (needs a respawn)
    'close'   -> outdoors but the camera is zoomed in (needs zoom-out)
    'unknown' -> cannot tell (unmatched biome and/or odd angle)
    'ok'      -> matches a reference at the macro camera"""
    if looks_indoor(shot):
        return "indoor"
    best, score = best_biome_match(shot, rarebiomes + worthskipping + ["normal"])
    if best is not None and score >= 0.5:
        ref = full_ref(best)
        if ref is not None and mid_band_match(ref, shot) < 0.35:
            return "close"
        return "ok"
    return "unknown"

def validate_view():
    """After joining: fix a wrong view (indoor lobby -> respawn) or a camera
    that didn't zoom out (close-up -> zoom out again). Returns True if the
    view is acceptable."""
    shot = snap_viewport()
    for attempt in range(3):
        state = view_state(shot)
        if state == "indoor":
            print(f"* [view-check {attempt+1}/3] indoor lobby detected - respawning")
            keyboard.press_and_release("esc")
            time.sleep(0.4)
            keyboard.press_and_release("r")
            time.sleep(0.4)
            keyboard.press_and_release("enter")
            time.sleep(5)
            zoom_out()
        elif state == "close":
            print(f"* [view-check {attempt+1}/3] camera too close - zooming out")
            zoom_out()
            if attempt == 1:  # second failure: angle is probably off too - respawn resets it
                print("* [view-check] zoom not helping - respawning to reset the camera")
                keyboard.press_and_release("esc")
                time.sleep(0.4)
                keyboard.press_and_release("r")
                time.sleep(0.4)
                keyboard.press_and_release("enter")
                time.sleep(5)
                zoom_out()
        elif state == "unknown" and attempt == 0:
            print("* [view-check] nothing matched yet - one harmless zoom-out to be safe")
            zoom_out()
        else:
            print(f"* [view-check] view OK ({state})")
            return True
        shot = snap_viewport()
    print("* [view-check] unresolved after 3 tries - continuing anyway")
    return False

_disc_ref = None  # cached disconnected-screen reference (loaded once)

def check_disconnected(shot):
    """The 'Disconnected' modal (Error 273 - same account on another device):
    a near-black frame with a grey centered dialog.
    TWO gates, both required: a strong modal-region match AND a black
    surround. Either one alone false-positives (grey stone platforms look
    like the dialog; dark skies look black) - together they only fire on
    the real error screen."""
    global _disc_ref
    ref_path = "./images/disconnected.png"
    if not os.path.exists(ref_path):
        return False
    if _disc_ref is None:
        _disc_ref = Image.open(ref_path).convert("RGB")
        if _disc_ref.size != (REF_W, REF_H):
            _disc_ref = _disc_ref.resize((REF_W, REF_H))
    ref = _disc_ref
    tol = 20
    n = 150
    m = 0
    for _ in range(n):
        x = random.randrange(550, 1050)
        y = random.randrange(330, 570)
        a = shot.getpixel((x, y))
        b = ref.getpixel((x, y))
        if abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol and abs(a[2] - b[2]) <= tol:
            m += 1
    if m / n < 0.65:
        return False
    dark = 0
    tot = 0
    for _ in range(40):
        x = random.randrange(0, 1600)
        y = random.randrange(0, 900)
        if 550 <= x <= 1050 and 330 <= y <= 570:
            continue
        tot += 1
        if max(shot.getpixel((x, y))) < 40:
            dark += 1
    return tot > 0 and dark / tot >= 0.8

def wait_for_loaded(hwnd, timeout=180):
    """Reference-free: wait for the game to actually reload after joining.
    'Loaded' = the hotbar/UI is visible again:
      - normal case: a loading dip was seen, then 2s of hotbar structure
      - fast joins: the dip can be missed by the 1s polls - accept after 3s
        of hotbar structure at t>=8 instead of waiting 30s
    Stuck-loading recovery (frozen screen -> reopen the link) ONLY applies
    while the game shows NO UI - a loaded-but-static screen must never
    trigger a rejoin."""
    prev = None
    saw_loading = False
    loaded_streak = 0
    hotbar_streak = 0
    rejoined_at = None
    frozen_since = None
    for t in range(timeout):
        time.sleep(1)
        shot = snap_viewport()
        if check_disconnected(shot):
            print("## 'Disconnected' screen (error 273) - killing Roblox and retrying")
            kill_roblox()
            return False
        strip = shot.crop((400, 820, 1200, 890)).convert("L")
        px = list(strip.getdata())
        mean = sum(px) / len(px)
        var = sum((v - mean) ** 2 for v in px) / len(px)
        hotbar_ok = var > 300
        diff = 0
        if prev is not None:
            a = shot.resize((160, 90)).convert("L")
            b = prev.resize((160, 90)).convert("L")
            pa, pb = list(a.getdata()), list(b.getdata())
            diff = sum(1 for i in range(len(pa)) if abs(pa[i] - pb[i]) > 20) / len(pa)
        prev = shot

        if not hotbar_ok:
            saw_loading = True
            loaded_streak = 0
            hotbar_streak = 0
        else:
            hotbar_streak += 1
            if saw_loading:
                loaded_streak += 1
                if loaded_streak >= 2:
                    print(f"loaded! (t={t}s, hotbar-var={var:.0f}, diff={diff:.2f})")
                    return True
            elif hotbar_streak >= 3 and t >= 8:
                # join was so fast the loading dip was missed - UI is up now
                print(f"loaded! (fast join, no dip seen, t={t}s, hotbar-var={var:.0f})")
                return True

        # stuck-loading recovery: only while the game still shows NO UI
        if not hotbar_ok:
            if diff < 0.03:
                frozen_since = t if frozen_since is None else frozen_since
            else:
                frozen_since = None
            if rejoined_at is None and t >= 30 and frozen_since is not None and t - frozen_since >= 15:
                rejoined_at = t
                print(f"* screen frozen for {t - frozen_since}s at t={t}s - reopening the VIP link")
                open_vip_link(settings["vip"])
                minimize_browser()
        else:
            frozen_since = None
        print(f"waiting for load... t={t}s hotbar-var={var:.0f} diff={diff:.2f} saw-loading={saw_loading}")
    return False

# ---------------------------------------------------------------- actions

def open_vip_link(link):
    try:
        os.startfile(link)
    except Exception as e:
        print(f"os.startfile failed ({e}), falling back to webbrowser.")
        import webbrowser
        webbrowser.open_new_tab(link)

def minimize_browser():
    """The browser window that pops up over the game when the VIP link opens
    would end up inside our screenshots - minimize it (it gets killed after
    load anyway)."""
    exe = settings.get("browsertoclose", "chrome").lower() + ".exe"
    time.sleep(4)  # let the tab open first
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe}", "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    pids = {int(l.split(",")[1].strip('"')) for l in out.strip().splitlines() if exe in l}
    found = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value in pids and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True
    user32.EnumWindows(cb, 0)
    for h in found:
        user32.ShowWindow(h, 6)  # SW_MINIMIZE
    if found:
        print(f"* minimized {len(found)} {exe} window(s)")

def summon_pets():
    keyboard.press("a")
    keyboard.press_and_release("o")
    time.sleep(1)
    keyboard.release("a")
    time.sleep(1)
    keyboard.press_and_release("1")      # D1
    time.sleep(1.001)
    click(800, 450)
    time.sleep(0.5)
    keyboard.press_and_release("2")      # D2
    time.sleep(1.5)
    click(800, 450)

def kill_roblox():
    """Leave the game GRACEFULLY first (ESC menu -> L = leave -> Enter) so the
    private server shuts down, then kill the client and wait 'killcooldown'
    seconds so the next join rolls a fresh server/biome."""
    try:
        keyboard.press_and_release("esc")
        time.sleep(1.2)
        keyboard.press_and_release("l")
        time.sleep(1.2)
        keyboard.press_and_release("enter")
        time.sleep(3)  # let the leave request go through
    except Exception as e:
        print(f"* graceful leave failed ({e!r}) - just killing.")
    subprocess.call("TASKKILL /IM RobloxPlayerBeta.exe /F", shell=True)
    time.sleep(settings.get("killcooldown", 3))

def mathclamp(num, min_, max_):
    return max(min_, min(max_, num))

# ---------------------------------------------------------------- main loop

import keyboard
skippablebosses = set()
worthskipping = list(settings["skippablebiomes"])
rarebiomes = list(settings["rarebiomes"])
finishall = False
timestried = 0

def finishfunc(key):
    global finishall
    finishall = True
    data = {"content": "## PRESSED STOP KEY (" + (settings["keytopause"]).upper() + ") STOPPING NOW"}
    sendbywebhook(data)
    sys.exit(0)

keyboard.on_press_key(settings["keytopause"], finishfunc)

def unbreakablehumanspirit():
    global finishall
    cycle = 0
    while True:
        if finishall:
            break
        cycle += 1
        try:
            one_cycle()
        except Exception as e:
            print(f"!!! cycle error: {e!r} - waiting 10s and retrying")
            import traceback
            traceback.print_exc()
            try:
                sendbywebhook({"content": f"!!! cycle error: {e!r} - retrying in 10s"})
            except Exception:
                pass
            time.sleep(10)

def one_cycle():
    global finishall, timestried
    biomefound = False
    whichbiomefound = "None"

    hwnd = find_roblox_hwnd()
    opened_to_launch = False
    if hwnd is None:
        print("Roblox not running - opening VIP link to launch it...")
        time.sleep(settings["rejoindelay"])
        open_vip_link(settings["vip"])
        opened_to_launch = True
        minimize_browser()
        for _ in range(60):
            time.sleep(1)
            hwnd = find_roblox_hwnd()
            if hwnd is not None:
                break
        if hwnd is None:
            print("!!! Roblox still not running after 60s, retrying.")
            time.sleep(5)
            return

    set_view(hwnd)
    time.sleep(settings["rejoindelay"])
    if not opened_to_launch:
        print("* opening the vip link now")
        sendbywebhook({"content": "* opening the vip link now"})
        open_vip_link(settings["vip"])
        minimize_browser()

    if not wait_for_loaded(hwnd):
        print("## Roblox took too long to load! Restarting.")
        sendbywebhook({"content": "## WARN Roblox took too long to load! Restarting."})
        kill_roblox()
        return

    set_view(hwnd)  # the game reload may have reset the window size - fix it again

    # close the browser so it doesn't eat your ram
    if settings.get("killbrowser", True):
        subprocess.call("TASKKILL /IM " + settings["browsertoclose"] + ".exe /F", shell=True)

    screenshot = snap_viewport()
    screenshot.save("tempscreen.png")
    towait = mathclamp(settings["waitbeforerejoin"], 20, 120)
    print("## Roblox loaded!")
    sendbywebhook({"content": "## Roblox loaded!", "file": "tempscreen.png"})

    if settings["resetuponload"]:
        # your manual macro: respawn to get out of the indoor lobby
        keyboard.press_and_release("esc")
        time.sleep(0.1)
        keyboard.press_and_release("r")
        time.sleep(0.1)
        keyboard.press_and_release("enter")
        time.sleep(5)

    # click to focus into the window, then zoom out
    print("* focusing into roblox.")
    sendbywebhook({"content": "* focusing into roblox."})
    click(800, 450 + random.randint(-5, 5), clicks=15, interval=0.1)
    time.sleep(2)
    for _ in range(20):  # hold O for 2 seconds to zoom out
        keyboard.press("o")
        time.sleep(0.1)
    keyboard.release("o")
    keyboard.press_and_release("tab")
    print("* zoomed out.")
    sendbywebhook({"content": "* zoomed out."})
    time.sleep(2)

    # make sure the camera is actually usable: indoor lobby -> respawn,
    # zoom that didn't take -> zoom out again
    validate_view()

    # NOTE: summons stay OFF during detection - they cover the sky region
    # (the red/white sphere floats up there). They're brought out only
    # after a rare biome is confirmed, right before farming starts.

    print(f"* Waiting {towait} seconds now.")
    unknown_streak = 0
    wait_end = towait
    currentscreen = None
    score = 0.0
    wait_start = time.time()
    i = 0
    while True:
        # wall-clock tick: the counter tracks real seconds even when a scan
        # iteration takes longer than 1s (hundreds of refs to compare)
        i = int(time.time() - wait_start) + 1
        tick_start = time.time()
        if finishall:
            break
        currentscreen = snap_viewport()
        if check_disconnected(currentscreen):
            print("## 'Disconnected' screen during wait - killing Roblox and restarting")
            sendbywebhook({"content": "## 'Disconnected' screen (error 273) during wait - killing Roblox and restarting."})
            kill_roblox()
            return
        keyboard.press_and_release(str(settings["whichslottoequip"]))  # equip item
        click(800, 450 + random.randint(-5, 5))
        keyboard.press_and_release("z, x, c")  # incase its an item
        if i % 15 == 0:  # reset every 15s for alignment
            keyboard.press_and_release("esc")
            time.sleep(0.5)
            keyboard.press_and_release("r")
            time.sleep(0.5)
            keyboard.press_and_release("enter")

        yepifoundit = False
        nahskip = False
        is_unknown = False
        best, score = best_biome_match(currentscreen, rarebiomes + worthskipping + ["normal", "DIDNT_LOAD"])
        need = settings["biomepixelthreshold"] / settings["biomepixelchecks"]
        if frame_is_black(currentscreen):
            whichbiomefound = "None"  # transition frame - ignore entirely
        elif best == "DIDNT_LOAD" and score >= need:
            whichbiomefound = "None"  # loading screen, not a biome - wait it out
            unknown_streak = 0
        elif best is not None and score >= need:
            best = resolve_shared_sky(best, currentscreen)
            whichbiomefound = best
            if best in rarebiomes:
                yepifoundit = True
            elif best in worthskipping:
                nahskip = True
            else:
                whichbiomefound = "None"  # plain grasslands = keep waiting
            unknown_streak = 0
        elif looks_indoor(currentscreen):
            whichbiomefound = "None"  # knocked into a wall / bad camera - fix it
            print(f"* camera inside geometry at t={i}s - respawning to fix it")
            keyboard.press_and_release("esc")
            time.sleep(0.5)
            keyboard.press_and_release("r")
            time.sleep(0.5)
            keyboard.press_and_release("enter")
            time.sleep(5)
            zoom_out()
            unknown_streak = 0
        else:
            whichbiomefound = "None"  # genuine unknown biome
            is_unknown = True
            unknown_streak += 1
            # unknown biome: ping Discord so the user can screenshot it
            # (skip the ping while the capture is black - nothing to see;
            # disable entirely with "pingunknown": false)
            if settings.get("pingunknown", True) \
                    and (unknown_streak == 15 or (unknown_streak > 15 and unknown_streak % 30 == 0)) \
                    and not frame_is_black(currentscreen):
                print(f"* UNKNOWN BIOME for {unknown_streak}s - pinging to screenshot it")
                currentscreen.save("tempscreen.png")
                sendbywebhook({"content": "<@" + settings["userid"] + "> **UNKNOWN BIOME detected** - no reference for the current biome! Come screenshot the game (attached is the macro's view).",
                               "file": "tempscreen.png"})

        # auto-grow references: save VERY CONFIDENT matches (>=85%) as extra
        # refs (borderline matches can be misidentifications - don't pollute)
        if (yepifoundit or nahskip) and score >= 0.85:
            refdir = f"./images/{whichbiomefound}"
            os.makedirs(refdir, exist_ok=True)
            currentscreen.save(f"{refdir}/{time.strftime('%Y%m%d_%H%M%S')}.png")
        elif is_unknown and i % 30 == 0:
            os.makedirs("unknowns", exist_ok=True)
            currentscreen.save(f"unknowns/{time.strftime('%Y%m%d_%H%M%S')}.png")

        msg = f"* {i}/{wait_end}s passed; good biome: {yepifoundit}, bad biome: {nahskip}, which: {whichbiomefound}"
        print(msg)
        if i % settings["screenshotstatusinterval"] == 0:
            data = {"content": msg}
            currentscreen.save("tempscreen.png")
            data["file"] = "tempscreen.png"
            sendbywebhook(data)
        if yepifoundit:
            biomefound = True
            break
        elif nahskip:
            break
        if i >= wait_end:
            if unknown_streak >= 15 and settings.get("pingunknown", True):
                # persistent unknown biome: keep waiting so the user can screenshot it
                wait_end = 180
                print("* unknown biome present - extending the wait so you can screenshot it")
            else:
                break
        if i >= 180:
            break
        time.sleep(max(0, 1.0 - (time.time() - tick_start)))  # keep ~1 tick per real second

    if biomefound:
        print("# " + whichbiomefound.upper() + " FOUND on try " + str(timestried))
        data = {"content": "# " + whichbiomefound.upper() + " FOUND <@" + settings["userid"] + ">\n# " + settings["vip"] + "\nonly took " + str(timestried) + " tries!" + ("\n### AFK FARM IS ON, WILL CONTINUE RUNNING" if settings["afkfarm"] else "")}
        sendbywebhook(data)
        if settings["afkfarm"]:
            # bring out the summons now that we're farming
            snap_viewport()  # re-fix the window mapping before clicking
            print("* summoning pets (D1 + D2).")
            sendbywebhook({"content": "* summoning pets (D1 + D2)."})
            summon_pets()
            time.sleep(1)
            rarebiomeended = False
            afktimeelapsed = 0
            farm_start = time.time()
            while not rarebiomeended:
                afktimeelapsed = int(time.time() - farm_start)
                tick_start = time.time()
                if finishall:
                    break
                currentscreen = snap_viewport()  # re-checks the window rect too
                if check_disconnected(currentscreen):
                    print("## 'Disconnected' screen during farm - killing Roblox and restarting")
                    sendbywebhook({"content": "## 'Disconnected' screen (error 273) during farm - killing Roblox and restarting."})
                    kill_roblox()
                    return
                keyboard.press_and_release(str(settings["slottoafkfarm"]))  # equip item
                click(800, 450 + random.randint(-5, 5))
                keyboard.press_and_release("z, x, c")
                if afktimeelapsed % 20 == 0:
                    keyboard.press_and_release("esc")
                    time.sleep(0.5)
                    keyboard.press_and_release("r")
                    time.sleep(0.5)
                    keyboard.press_and_release("enter")
                if afktimeelapsed % 30 == 0:
                    summon_pets()  # re-summon in case a summon died

                best, score = best_biome_match(currentscreen, ["normal"])
                if best == "normal" and score >= settings["biomepixelthreshold"] / settings["biomepixelchecks"]:
                    rarebiomeended = True

                if rarebiomeended:
                    screenshot = snap_viewport()
                    screenshot.save("tempscreen.png")
                    timestried = 0
                    print(f"## {whichbiomefound.upper()} ended in {afktimeelapsed}s! continuing.")
                    sendbywebhook({"content": f"## {whichbiomefound.upper()} ended in {afktimeelapsed}s! macro continues.", "file": "tempscreen.png"})
                    if not finishall:
                        kill_roblox()
                else:
                    msg = f"* {whichbiomefound.upper()} has been going for {afktimeelapsed}s."
                    print(msg)
                    data = {"content": msg}
                    if afktimeelapsed % settings["screenshotstatusinterval"] == 0:
                        currentscreen.save("tempscreen.png")
                        data["file"] = "tempscreen.png"
                    sendbywebhook(data)
                time.sleep(max(0, 1.0 - (time.time() - tick_start)))
    else:
        timestried += 1
        msg = f"* skipped {whichbiomefound} (score {score:.2f}). [{settings['strugglemessage']}] #{timestried}"
        print(msg)
        data = {"content": msg}
        if currentscreen is not None and not frame_is_black(currentscreen):
            try:
                currentscreen.save("tempscreen.png")  # show what was actually there
                data["file"] = "tempscreen.png"
            except Exception:
                pass
        sendbywebhook(data)
        if not finishall:
            kill_roblox()

try:
    if __name__ == "__main__":
        unbreakablehumanspirit()
except KeyboardInterrupt:
    print("stopped by user.")
try:
    os.remove("tempscreen.png")
except FileNotFoundError:
    pass
