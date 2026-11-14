# Chiikawa Ball Fight

Run on PC: `python main.py`   (needs `pip install pygame`; numpy is no longer needed)

Controls: the game opens on the **character select** screen - pick **1 v 1** or **2 v 2**, tap a slot,
then tap a fighter to put them in it, then **FIGHT!** During a match: **MENU** (or tap a team card),
**REMATCH**, **RANDOM**. Keyboard: `1` / `2` cycle the first fighter on each side, `SPACE` rematch,
`M` menu, `ESC` quit.

## Uploading changes to GitHub
- First time only: double-click `connect_github.bat` (needs Git: https://git-scm.com/download/win).
- After that: double-click `push_update.bat` whenever you change something. The phone version rebuilds in ~2 min.
  (Or use GitHub Desktop: File -> Add local repository -> this folder.)

## Play on your phone (GitHub Pages)
1. Make a GitHub repo and push this folder to its `main` branch.
2. On GitHub: **Settings -> Pages -> Build and deployment -> Source: GitHub Actions**.
3. Every push builds the web version (`.github/workflows/web.yml`, uses pygbag). Watch it under the **Actions** tab (~2-3 min).
4. Open `https://<your-username>.github.io/<repo-name>/` on your phone, tap once to start (browsers need a tap before sound can play).
   Tip: "Add to Home Screen" makes it open like an app.

Test the web build on PC first if you like: `pip install pygbag` then `pygbag .` and open http://localhost:8000

## Images
Drop pictures into `assets/` named after the character. Names the game looks for:
`chiikawa`, `hachiware`, `momonga`, `rakko`, `usagi`, `anoko`, `kurimanju` (or `kuromanju`), `shisa`, `kani`,
plus summons `dekatsuyo` and `yoroi` (Shisa's sensei), and extras `anoko_tail` (tail spin) and `kani_crabclaw` (claw snips).
Case and extension don't matter. Transparent cut-outs look best (they get a white + team-colour sticker outline, no ball).
Want the coloured ball back behind pictures? Set `SHOW_BALL_UNDER_PICTURES = True` in `ballfight/config.py`.
Optional props: `weed`, `food`, `pink_car`, `rakko_sword`, `usagi_stick`, `sasumata_pink`, `sasumata_blue`.

## Layout
- `main.py` - entry point
- `ballfight/fighters/` - one file per character (+ `_template.py` to copy)
- `ballfight/game.py` - main loop
- `ballfight/ui.py` / `scene.py` - HUD cards, background, arena
- `ballfight/world_objects.py` / `effects.py` - weeds, food, seeds, Dekatsuyo, particles
- `ballfight/config.py` / `audio.py` / `assets.py` - settings, sounds, image loading
- `.github/workflows/web.yml` - builds the phone/web version
- `old/` - your original single-file version

## Adding a character
1. Copy `fighters/_template.py` to e.g. `fighters/kurimanju.py`, rename the class/key, write the attack.
2. Uncomment the `register_solo(...)` line at the bottom.
3. Add `from . import kurimanju` to `fighters/__init__.py`.
4. Put `kurimanju.png` in `assets/`.
It then shows up in the roster, the HUD and the winner screen automatically.

## Shared mechanics you can use in new characters
- `enemy.apply_knockback(vx, vy, attacker, wall_damage=True)` - shove; wall slams hurt 3-9 by speed
- `enemy.apply_daze(seconds)` - their attack bar fills 50% slower
- `self.dmg_mult`, `self.dmg_taken_mult`, `self.cd_rate_mult` - buffs/debuffs
- `world["floor"]` - ground hazards drawn under fighters (e.g. Shisa's ramen pool)
- `DekatsuyoRunner(..., damage=, sprite_key=, radius=)` - any "big thing charges across the arena" summon
