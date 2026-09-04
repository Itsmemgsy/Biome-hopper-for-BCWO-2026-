# 🌾 Biome Hopper — automatic biome farming for Balanced Craftwars Overhaul

Opens your private server, waits for a biome, farms the rare ones (summons out,
AFK fighting) and re-joins to skip the rest. Pings you on Discord when it
finds something worth your attention.

MUST READ!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
PUT YOUR TWILIGHT AND OTHER SUMMON ON FIRST AND SECOND PLACE OF YOUR INVENTORY

Adapted from https://github.com/debelopguy/BiomeHopper and reworked: the
repo's screenshots, boss checks and clicks were built for an older BCWO and a
fixed 1600×900 screen. This version auto-sizes the game window, recaptures its
own references, and validates the camera every cycle.

## What you need

- **Windows 10/11** (64-bit)
- **Python 3.10+** from python.org — during install tick **"Add python.exe to PATH"**
- https://www.python.org/
- **Roblox** installed, running **windowed** (not exclusive fullscreen — the
  macro forces windowed with F11 if needed)
- **Your private (VIP) server link** for Balanced Craftwars Overhaul
- Optional: a **Discord webhook** for notifications

## Step 1 — install the packages

Open a terminal (PowerShell/CMD) **in this folder** and run:

```
pip install discord_webhook pyautogui keyboard pillow
```

That's all the script needs. No OpenCV, no drivers, no admin rights.

## Step 2 — allow the "Open Roblox?" popup (one time)

Open your VIP link in your browser by hand once. The browser will ask
something like *"Open Roblox? [x] Always allow this site to open links of
this type"* — tick the checkbox and click Open. If you skip this, every join
stalls on the permission popup and the macro can't proceed.

## Step 3 — start it

Double-click **`run_macro.bat`**.

1. A **settings window** pops up, already filled in. Check:
   - **VIP link** — your private server link (paste yours)
   - **Discord webhook** — paste a channel webhook URL, or `None` to disable
   - **Discord user ID** — right-click your name in Discord → *Copy User ID*
     (this is who gets pinged for rare/unknown biomes)
   - **Targeted biomes** — set each biome to **Farm (rare)**, **Skip**, or **Off**
2. Click **Save & Run macro** (or Cancel to not run).

`run_macro.bat` must be used rather than double-clicking the `.py` file, so
errors stay visible in the console instead of flashing past.

## Step 4 — what a healthy first run looks like

Watch the console and the game window:

1. Roblox window is resized to a **1600×900 game area** at the top-left
   (this is how all the picture-matching stays exact — any resolution monitor works).
2. Chrome opens your link, then gets **minimized** so it can't cover the game.
3. `loaded!` appears once the game world + hotbar are detected (a fast join is
   accepted in ~8s; a stuck one re-opens the link at 30s).
4. Chrome is killed, the game **respawns** (esc → R → enter, to leave the indoor
   lobby), clicks focus the window, camera **zooms out** (hold O), pets are
   *not* summoned yet.
5. A **view check** fixes anything off: lobby-wall view → respawn; camera too
   close → zoom out again (up to 3 tries).
6. It watches for up to `waitbeforerejoin` seconds:
   - rare biome → pings Discord, summons D1 + D2, AFK-farms until the biome ends
   - skip biome → closes Roblox and re-joins for a fresh roll
   - nothing it knows → after 15s+ unknown it **pings you with a screenshot**
     so you can picture it, then keeps waiting up to 3 minutes before re-joining

Press **F9** anytime to stop. The macro never injects or hacks — it only
presses keys and clicks like a normal macro, and it never changes your Roblox
settings or sensitivity.

## Step 5 — teach it biomes (the reference pictures)

Biome detection = comparing ~300 random pixels from the **top sky band** of your
screen against saved reference pictures, best-match wins. Most references are
already captured (`OK` in the gallery), but the game changes — and **pvc /
hvuh / asta share the same cloudy sky**, told apart by ocean color
(purple / red / black).

**Easy way:** open the capture window with

```
pythonw capture_gui.py
```

When a biome is announced in chat, press its **Capture** button. It respawns
you, zooms out, and snapshots exactly what the macro sees.
Buttons show `MISSING` (red), `OK` (green) or `RECAPTURE` (orange — captured
from the wrong angle before).

Double-check everything anytime with **`gallery.html`** (press *Gallery* in the
capture window to regenerate it) — one card per biome with its picture and its
horizon-color strip.

Reference lookup table (chat message → button):

| Chat message | Biome | Odds |
|---|---|---|
| "The angels of the sky are descending!" | Angel's Descent | 1/2500 |
| "A bright light is blinding the world!" | Blinding Light | 1/5000 |
| "Your actions have brought imbalances to reality." | Cultist Legion | 1/7500 |
| "The war between holy and unholy has started!" | Holy vs Unholy | 1/1125 |
| "The war between pure and corrupt has started!" | Pure vs Corrupt | 1/750 |
| "The world is being shrouded in darkness!" | Shrouding Darkness | 1/5000 |
| "The void is infiltrating reality!" | Void Infiltration | 1/2500 |
| "A bright blue moon illuminates the sky…" | Starry Night | 1/600 |
| "The moon is rising!" | Night | 1/125 |
| "An incredibly strong blizzard is freezing the island!" | Blizzard | 1/180 |
| "A powerful stormsurge has engulfed the island!" | Stormsurge | 1/180 |
| "Magical flames have warped the island!" | Flare | 1/180 |
| "The wind is sweeping life energy…" | Nature | 1/180 |
| "The island has been irradiated…" | Irradiated | 1/600 |
| *(nothing — default)* | Grasslands (normal) | — |

> Note: Benedictus phase 2 (Blinding Light boss) hides the sky behind a
> reflective ceiling — references must be captured from the *normal* view.
>
> Note: asta (Shrouding Darkness) ships with no reference yet — the macro will
> report it as UNKNOWN and ping you; capture it the first time it appears.

## The Discord messages

- `joining / loaded!` — a cycle started
- `# CULT FOUND @you` + VIP link — a rare biome, farming starts now
- `**UNKNOWN BIOME detected**` + screenshot — it can't identify the biome;
  screenshot it so a reference can be made, it waits up to 3 minutes for you
- `skipped storm (score 0.91)` + screenshot — what it skipped and how sure it
  was (score 0–1, needs ≥0.5)
- "Disconnected screen (error 273)" — account kicked by another device; the
  macro kills Roblox and retries
- Periodic `STAR has been going for 120s.` updates while AFK-farming (every
  10s)

## settings.json reference

| Key | Default | What it does |
|---|---|---|
| `vip` | *(your link)* | Private server link opened every cycle |
| `webhook` | *(your webhook)* / `"None"` | Discord notifications on/off |
| `userid` | *(your Discord ID)* | Who gets pinged for rare/unknown biomes |
| `rarebiomes` | hvuh, void, angel, bene, cult, asta | Farm these until they end |
| `skippablebiomes` | pvc, moon, flame, forest, storm, blizzard, irradiated, star | Skip + rejoin on these |
| `sharedskies` | pvc → [pvc, hvuh, asta] | Skyboxes shared by several biomes; ocean color picks the exact one |
| `afkfarm` | true | Keep fighting during a rare biome instead of stopping |
| `slottoafkfarm` / `whichslottoequip` | 2 / 1 | Hotbar slots used while farming / watching |
| `waitbeforerejoin` | 60 (clamped 20–120) | Seconds to watch each server for a biome |
| `rejoindelay` | 0 | Extra pause before each join |
| `killcooldown` | 3 | Seconds to wait after killing Roblox so the empty server shuts down (raise to 15–60 if rejoins land on the same server) |
| `cleanupage_hours` / `cleanupmaxmb` | 24 / 200 | Auto-delete `captures/` + `unknowns/` older than this or over this size |
| `biomepixelchecks` / `biomepixelthreshold` / `biomepixeltolerance` | 300 / 150 / 12 | How many sky pixels sampled, how many must match (50%), per-channel tolerance |
| `killbrowser` | true | Kill Chrome after the game loads (saves RAM) |
| `browsertoclose` | chrome | `chrome` / `msedge` / `firefox` — must match the browser you use |
| `resetuponload` | true | Respawn after joining (spawn is an indoor lobby) |
| `screenshotstatusinterval` | 10 | Seconds between Discord status pictures |
| `keytopause` | f9 | Global stop key (no admin needed) |
| `strugglemessage` / `struggleattachment` | … | Flavor text + image in the skip messages |

## Troubleshooting

- **Same biome after every rejoin** — your private server survives the empty
  lobby. The macro leaves gracefully (esc → L → Enter) then kills Roblox and
  waits `killcooldown` seconds; if that isn't enough, raise `killcooldown` to
  15–60. If the server simply persists forever, farm there instead of rejoining.
- **It keeps reopening the browser link** — the stuck-loading recovery only
  fires when the screen is frozen *and* shows no game UI; check for a Roblox
  error popup blocking the load.
- **"Disconnected … Error 273"** — your account is logged in on another
  device. The macro kills Roblox and retries automatically.
- **Blank/black screenshots in Discord** — the monitor went to sleep or Roblox
  went fullscreen; the macro tries to keep the display awake and forces
  windowed mode. Black frames are retried, never saved as references, and never
  pinged.
- **Console full of cycle errors / link reopens** — enable the console text you
  see and read the first error; mis-sized reference pictures (anything not
  1600×900) are the usual cause. `IndexError: image index out of range` means
  a stray file (e.g. a `*_ground.png`) ended up inside an `images/<biome>/`
  folder.
- **Nothing matches after a game update** — the skybox changed. Re-capture the
  biomes with the Capture button (they overwrite the old reference) and confirm
  in `gallery.html`.
- **Fail-safe / corner errors** — disabled by design (`FAILSAFE = False`); an
  AFK macro can't abort because the mouse rests in a corner.
- **Roblox feels different afterwards** — the macro only ever moves/resizes the
  window; your settings and sensitivity are untouched. Drag the window back to
  your usual size (Roblox remembers it per game).

## Files

| File | Purpose |
|---|---|
| `run_macro.bat` | **Start here** — opens the settings GUI, then runs the macro |
| `settings_gui.py` | The pre-run settings popup |
| `biome_hopper.py` | The macro itself |
| `settings.json` | All configuration |
| `capture_gui.py` / `capture.py` | One-click reference captures (`--resetcamera` = same camera as the macro) |
| `make_gallery.py` / `gallery.html` | Visual overview + status of every reference |
| `images/` | References: `<biome>.png` sky, `<biome>_ground.png` horizon strip, `<biome>/` extra auto-captured shots (≥85% matches only) |
| `unknowns/` / `captures/` | Frames the macro couldn't identify / watch-mode snapshots — auto-pruned |
