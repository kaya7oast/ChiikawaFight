"""Shared battle simulation + drawing, used by the real match (game.py) and the intro demo (demo.py)."""
import math

from .audio import SFX_BOUNCE
from .scene import draw_shadow, draw_hit_flash, draw_daze_stars


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


def step_battle(team_left, team_right, world, dt):
    """One simulation tick (fighters, projectiles, hazards, collisions)."""
    all_fighters = team_left.fighters + team_right.fighters
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


def step_fx(all_fighters, world, dt):
    """Effects / particles / popups / hit flash / screen shake (runs even after the match ends)."""
    for key in ("effects", "particles", "popups"):
        for obj in world[key]:
            obj.update(dt)
        world[key] = [o for o in world[key] if o.life > 0]
    for f in all_fighters:
        if f.hit_flash > 0:
            f.hit_flash -= dt
    world["shake"] = max(0.0, world["shake"] - 40.0 * dt)


def draw_battle(frame, team_left, team_right, world, t, arena_surf, arena_pos):
    """Arena + everything inside it."""
    frame.blit(arena_surf, arena_pos)
    for key in ("floor", "weeds", "foods", "effects", "projectiles"):
        for obj in world[key]:
            obj.draw(frame)

    all_fighters = team_left.fighters + team_right.fighters
    for f in all_fighters:
        if f.alive and not f.in_air:
            draw_shadow(frame, f.x, f.y, f.radius)

    pairs = [(f, team_right.fighters if f in team_left.fighters else team_left.fighters) for f in all_fighters]
    for f, enemies in sorted(pairs, key=lambda item: item[0].draw_layer):
        f.draw(frame, enemies)
        if f.alive and f.hit_flash > 0 and not f.in_air:
            draw_hit_flash(frame, f.x, f.y, f.radius, f.hit_flash)
        if f.alive and f.daze_timer > 0:
            draw_daze_stars(frame, f.x, f.y - f.radius - 10, t)

    for key in ("hazards", "particles", "popups"):
        for obj in world[key]:
            obj.draw(frame)
