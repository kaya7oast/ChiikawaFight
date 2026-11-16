"""Main loop: input, simulation step, rendering. Async so it also runs in the browser (pygbag)."""
import asyncio
import random

import pygame

from .config import WIDTH, HEIGHT, FPS
from .assets import init_assets
from .voices import init_voices
from .teams import build_side
from .menu import SelectMenu
from .demo import IntroDemo
from . import fighters  # noqa: F401  (registers all characters)
from .scene import build_background, build_arena
from .sim import new_world, step_battle, step_fx, draw_battle
from .ui import draw_team_ui, draw_vs_badge, draw_winner, draw_footer, BUTTONS, card_rect


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
    screen_mode = "MENU"  # "MENU" (pick fighters), "INTRO" (character demos) or "FIGHT"
    intro = None

    def reset_match():
        return build_side(menu.picks("LEFT"), "LEFT"), build_side(menu.picks("RIGHT"), "RIGHT"), new_world(), 0.0

    team_left, team_right, world, match_time = reset_match()
    winner, winner_side, winner_anim = None, None, 0.0
    pressed = {}  # button -> flash timer (tap feedback)

    while True:
        dt = min(clock.tick(FPS) / 1000.0, 0.05)

        action = None
        menu_click = None
        intro_click = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    return
                if screen_mode == "INTRO":
                    intro_click = "SKIP_ALL" if event.key == pygame.K_s else "NEXT"
                    continue
                action = {pygame.K_1: "LEFT", pygame.K_2: "RIGHT", pygame.K_m: "MENU",
                          pygame.K_r: "REMATCH", pygame.K_SPACE: "REMATCH"}.get(event.key, action)
                if screen_mode == "MENU" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                    action = "FIGHT"
                if screen_mode == "MENU" and event.key == pygame.K_d:
                    menu.intro_on = not menu.intro_on
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # touch screens send taps as left clicks
                if screen_mode == "MENU":
                    menu_click = event.pos
                elif screen_mode == "INTRO":
                    intro_click = event.pos
                else:
                    for name, rect in BUTTONS.items():
                        if rect.collidepoint(event.pos):
                            action = name
                    if card_rect("LEFT").collidepoint(event.pos) or card_rect("RIGHT").collidepoint(event.pos):
                        action = "MENU"

        if screen_mode == "MENU" and menu_click and menu.click(menu_click) == "FIGHT":
            action = "FIGHT"

        # ---------------- INTRO (character demos before the match) ----------------
        if screen_mode == "INTRO":
            if intro_click is not None:
                intro.click(intro_click)
            frame.blit(background, (0, 0))
            intro.update(dt)
            intro.draw(frame, arena_surf, arena_pos)
            screen.blit(frame, (0, 0))
            pygame.display.flip()
            if intro.done:
                screen_mode = "FIGHT"
                team_left, team_right, world, match_time = reset_match()
                winner, winner_side, winner_anim = None, None, 0.0
            await asyncio.sleep(0)
            continue

        if action:
            pressed[action] = 0.15
            if action == "MENU":
                screen_mode = "MENU"
            elif action in ("LEFT", "RIGHT"):
                menu.cycle(action)
            elif action == "RANDOM":
                menu.randomize()
            if action != "MENU":
                if action == "FIGHT" and menu.intro_on:
                    intro = IntroDemo(menu.picks("LEFT"), menu.picks("RIGHT"))
                    screen_mode = "INTRO"
                    continue
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
            step_battle(team_left, team_right, world, dt)
            if not any(f.alive and f.core for f in team_right.fighters):
                winner, winner_side = team_left, "LEFT"
            elif not any(f.alive and f.core for f in team_left.fighters):
                winner, winner_side = team_right, "RIGHT"
        else:
            winner_anim += dt
        step_fx(all_fighters, world, dt)

        # ---------------- RENDER ----------------
        frame.blit(background, (0, 0))
        draw_team_ui(frame, team_left, "LEFT", dt)
        draw_team_ui(frame, team_right, "RIGHT", dt)
        draw_vs_badge(frame, match_time)
        draw_battle(frame, team_left, team_right, world, match_time, arena_surf, arena_pos)

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
