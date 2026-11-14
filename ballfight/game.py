"""Main loop: input, simulation step, rendering. Async so it also runs in the browser (pygbag)."""
import asyncio
import math
import random

import pygame

from .config import WIDTH, HEIGHT, FPS, ARENA_RECT
from .audio import SFX_BOUNCE
from . import registry
from .assets import init_assets
from .voices import init_voices
from .teams import build_side
from .menu import SelectMenu
from . import fighters  # noqa: F401  (registers all characters)
from .scene import build_background, build_arena, draw_shadow, draw_hit_flash, draw_daze_stars
from .ui import draw_team_ui, draw_vs_badge, draw_winner, draw_footer, BUTTONS, card_rect


def new_world():
    return {
        "weeds": [], "foods": [], "floor": [], "projectiles": [], "hazards": [],
        "effects": [], "particles": [], "popups": [], "shake": 0.0,
    }


def resolve_ball_collisions(fighters_list):
    roaming = [
        f for f in fighters_list
        if f.alive and not f.in_air and not f.grabbed_by and f.state in f.COLLIDE_STATES
    ]
    for i in range(len(roaming)):
        for j in range(i + 1, len(roaming)):
            b1, b2 = roaming[i], roaming[j]
            dx, dy = b2.x - b1.x, b2.y - b1.y
            dist = math.hypot(dx, dy)
            min_d = b1.radius + b2.radius
            if 0 < dist < min_d:
                nx, ny = dx / dist, dy / dist
                overlap = (min_d - dist) * 0.5
                b1.x -= nx * overlap
                b1.y -= ny * overlap
                b2.x += nx * overlap
                b2.y += ny * overlap
                s1, s2 = b1.bounce_speed(), b2.bounce_speed()
                b1.vx, b2.vx = -nx * s1, nx * s2
                b1.vy, b2.vy = -ny * s1, ny * s2
                SFX_BOUNCE.play()


async def main():
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Chiikawa Ball Fight")
    clock = pygame.time.Clock()
    init_assets()
    init_voices()

    background = build_background()
    arena_surf, arena_pos = build_arena()
    frame = pygame.Surface((WIDTH, HEIGHT))

    menu = SelectMenu()
    screen_mode = "MENU"  # "MENU" (pick fighters) or "FIGHT"

    def reset_match():
        return build_side(menu.picks("LEFT"), "LEFT"), build_side(menu.picks("RIGHT"), "RIGHT"), new_world(), 0.0

    team_left, team_right, world, match_time = reset_match()
    winner, winner_side, winner_anim = None, None, 0.0
    pressed = {}  # button -> flash timer (tap feedback)

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        action = None
        menu_click = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                action = {pygame.K_1: "LEFT", pygame.K_2: "RIGHT", pygame.K_m: "MENU",
                          pygame.K_r: "REMATCH", pygame.K_SPACE: "REMATCH"}.get(event.key, action)
                if screen_mode == "MENU" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    action = "FIGHT"
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # touch screens send taps as left clicks
                if screen_mode == "MENU":
                    menu_click = event.pos
                else:
                    for name, rect in BUTTONS.items():
                        if rect.collidepoint(event.pos):
                            action = name
                    if card_rect("LEFT").collidepoint(event.pos) or card_rect("RIGHT").collidepoint(event.pos):
                        action = "MENU"

        if screen_mode == "MENU" and menu_click and menu.click(menu_click) == "FIGHT":
            action = "FIGHT"
        if action:
            pressed[action] = 0.15
            if action == "MENU":
                screen_mode = "MENU"
            elif action in ("LEFT", "RIGHT"):
                menu.cycle(action)
            elif action == "RANDOM":
                menu.randomize()
            if action != "MENU":
                if action == "FIGHT" or screen_mode == "FIGHT" or action in ("LEFT", "RIGHT"):
                    screen_mode = "FIGHT"
                    team_left, team_right, world, match_time = reset_match()
                    winner, winner_side, winner_anim = None, None, 0.0
        for k in list(pressed):
            pressed[k] -= dt
            if pressed[k] <= 0:
                del pressed[k]

        if screen_mode == "MENU":
            frame.blit(background, (0, 0))
            menu.draw(frame, dt)
            screen.blit(frame, (0, 0))
            pygame.display.flip()
            await asyncio.sleep(0)
            continue

        all_fighters = team_left.fighters + team_right.fighters

        # ---------------- SIMULATION ----------------
        if winner is None:
            match_time += dt
            for f in all_fighters:
                f.update_status(dt, world)
            team_left.update(dt, team_right.fighters, world)
            team_right.update(dt, team_left.fighters, world)

            world["weeds"] = [w for w in world["weeds"] if w.alive]
            world["foods"] = [f for f in world["foods"] if f.alive]

            for key in ("floor", "projectiles", "hazards"):
                for obj in world[key]:
                    targets = team_left.fighters if obj.owner in team_right.fighters else team_right.fighters
                    obj.update(dt, targets, world)
                world[key] = [o for o in world[key] if o.alive]

            resolve_ball_collisions(all_fighters)

            if not any(f.alive and f.core for f in team_right.fighters):
                winner, winner_side = team_left, "LEFT"
            elif not any(f.alive and f.core for f in team_left.fighters):
                winner, winner_side = team_right, "RIGHT"
        else:
            winner_anim += dt

        for key in ("effects", "particles", "popups"):
            for obj in world[key]:
                obj.update(dt)
            world[key] = [o for o in world[key] if o.life > 0]

        for f in all_fighters:
            if f.hit_flash > 0:
                f.hit_flash -= dt
        world["shake"] = max(0.0, world["shake"] - 40.0 * dt)

        # ---------------- RENDER ----------------
        frame.blit(background, (0, 0))
        draw_team_ui(frame, team_left, "LEFT", dt)
        draw_team_ui(frame, team_right, "RIGHT", dt)
        draw_vs_badge(frame, match_time)
        frame.blit(arena_surf, arena_pos)

        for fl in world["floor"]:
            fl.draw(frame)
        for w in world["weeds"]:
            w.draw(frame)
        for fd in world["foods"]:
            fd.draw(frame)
        for eff in world["effects"]:
            eff.draw(frame)
        for proj in world["projectiles"]:
            proj.draw(frame)

        for f in all_fighters:
            if f.alive and not f.in_air:
                draw_shadow(frame, f.x, f.y, f.radius)

        pairs = [(f, team_right.fighters if f in team_left.fighters else team_left.fighters) for f in all_fighters]
        for f, enemies in sorted(pairs, key=lambda item: item[0].draw_layer):
            f.draw(frame, enemies)
            if f.alive and f.hit_flash > 0 and not f.in_air:
                draw_hit_flash(frame, f.x, f.y, f.radius, f.hit_flash)
            if f.alive and f.daze_timer > 0:
                draw_daze_stars(frame, f.x, f.y - f.radius - 10, match_time)

        for h in world["hazards"]:
            h.draw(frame)
        for pt in world["particles"]:
            pt.draw(frame)
        for pop in world["popups"]:
            pop.draw(frame)

        if winner:
            draw_winner(frame, winner, winner_side, winner_anim)

        draw_footer(frame, pressed)

        shake = world["shake"]
        ox = int(random.uniform(-shake, shake)) if shake > 0.5 else 0
        oy = int(random.uniform(-shake, shake)) if shake > 0.5 else 0
        if ox or oy:
            screen.fill((0, 0, 0))
        screen.blit(frame, (ox, oy))
        pygame.display.flip()
        await asyncio.sleep(0)  # lets the browser breathe (required for the web build)
