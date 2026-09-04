# capture.py <name>           — save a 1600x900 viewport snapshot as images/<name>.png
# capture.py <name> --zoomout — zoom the camera out first (like the macro does)
# capture.py watch            — auto-snapshot every 15s into captures/
# The sky does NOT change per biome - only the skybox texture matters, so refs
# are position/angle tolerant. Keep summons away from the camera when capturing.
import ctypes, glob, os, subprocess, sys, time
from ctypes import wintypes

ctypes.windll.user32.SetProcessDPIAware()
import pyautogui, keyboard
from PIL import Image

user32 = ctypes.windll.user32

def find_roblox_hwnd():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq RobloxPlayerBeta.exe",
                          "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    if "RobloxPlayerBeta" not in out:
        print("!!! Roblox is not running. Open the game and get in-game first.")
        sys.exit(1)
    lines = [l for l in out.strip().splitlines() if "RobloxPlayerBeta" in l]
    pid = int(lines[0].split(",")[1].strip('"'))
    found = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lparam):
        p = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
        if p.value == pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True
    user32.EnumWindows(cb, 0)
    return found[0] if found else None

def client_rect(hwnd):
    cr = wintypes.RECT(); user32.GetClientRect(hwnd, ctypes.byref(cr))
    pt = wintypes.POINT(0, 0); user32.ClientToScreen(hwnd, ctypes.byref(pt))
    return pt.x, pt.y, cr.right, cr.bottom

hwnd = find_roblox_hwnd()

# window must be 1600x900 client
ox, oy, cw, ch = client_rect(hwnd)
if (cw, ch) != (1600, 900):
    print("Resizing Roblox window to 1600x900 viewport...")
    wr = wintypes.RECT(); user32.GetWindowRect(hwnd, ctypes.byref(wr))
    chrome_l = ox - wr.left
    chrome_r = wr.right - (ox + cw)
    chrome_t = oy - wr.top
    chrome_b = wr.bottom - (oy + ch)
    user32.MoveWindow(hwnd, 0, 0, 1600 + chrome_l + chrome_r, 900 + chrome_t + chrome_b, True)
    time.sleep(2.5)
    ox, oy, cw, ch = client_rect(hwnd)

def snap():
    shot = pyautogui.screenshot()
    return shot.crop((ox, oy, ox + cw, oy + ch))

if len(sys.argv) < 2:
    print("usage: capture.py <name> [--zoomout] [--resetcamera]   |   capture.py watch")
    sys.exit(1)

resetcamera = "--resetcamera" in sys.argv
zoomout = "--zoomout" in sys.argv or resetcamera
if resetcamera:
    # replicate the macro's detection camera: respawn (out of the lobby) -> wait -> zoom out
    print("respawn + zoom out (matching the macro's camera)...")
    keyboard.press_and_release("esc")
    time.sleep(0.5)
    keyboard.press_and_release("r")
    time.sleep(0.5)
    keyboard.press_and_release("enter")
    time.sleep(6)
if zoomout:
    print("zooming out (hold O 2s)...")
    keyboard.press("o")
    time.sleep(2)
    keyboard.release("o")
    time.sleep(1)
if resetcamera:
    keyboard.press_and_release("tab")
    time.sleep(1)

mode = sys.argv[1]
if mode == "watch":
    os.makedirs("captures", exist_ok=True)
    print("Watching... snapshot every 15s into captures/  (Ctrl+C to stop)")
    n = 0
    try:
        while True:
            ts = time.strftime("%Y%m%d_%H%M%S")
            snap().save(f"captures/{ts}.png")
            print("saved captures/" + ts + ".png", flush=True)
            n += 1
            if n % 30 == 0:  # keep the disk tidy
                age = json.load(open("settings.json", encoding="utf-8")).get("cleanupage_hours", 24)
                size = json.load(open("settings.json", encoding="utf-8")).get("cleanupmaxmb", 200)
                files = sorted(glob.glob("captures/*.png"), key=os.path.getmtime)
                total = sum(os.path.getsize(f) for f in files)
                cutoff = time.time() - age * 3600
                for f in files:
                    if os.path.getmtime(f) >= cutoff and total <= size * 1024 * 1024:
                        break
                    total -= os.path.getsize(f)
                    os.remove(f)
            time.sleep(15)
    except KeyboardInterrupt:
        print("stopped.")
else:
    if not mode.endswith(".png"):
        mode += ".png"
    os.makedirs("images", exist_ok=True)
    path = "images/" + mode
    img = snap()
    img.save(path)
    print("saved " + path)
    ground = img.crop((200, 380, 1560, 520))
    ground.save("images/" + mode.replace(".png", "_ground.png"))
    print("saved images/" + mode.replace(".png", "_ground.png") + " (horizon discriminator)")
    img.save("current_viewport.png")
