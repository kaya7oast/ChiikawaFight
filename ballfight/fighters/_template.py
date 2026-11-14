"""
TEMPLATE – copy this file to make a new character (e.g. fighters/kurimanju.py),
then add `from . import kurimanju` in fighters/__init__.py. That's it: the roster,
UI card, HP bar and image loading all pick it up automatically.

Image: put kurimanju.png (or .webp/.jpg, any case) in assets/. Transparent cut-outs look best.
"""
from ..config import *
from ..audio import *
from ..effects import *
from ..world_objects import *
from ..drawing import *
from ..teams import register_solo
from .base import BaseFighter

NEW_COLOR = (180, 140, 100)


class TemplateFighter(BaseFighter):
    def __init__(self, x, y):
        # char_type must match the key passed to register_solo below
        super().__init__("TEMPLATE", x, y, hp=250, color=NEW_COLOR, radius=31, speed=220.0)
        self.cd_max = 3.0      # seconds between attacks (UI reads cd_timer / cd_max)
        self.cd_timer = 0.0

    def update(self, dt, enemies, world):
        if not self.alive or self.grabbed_by:
            return
        if self.stun_timer > 0:
            self.stun_timer -= dt
            return
        self.check_enemy_food_pickup(world)

        living = [e for e in enemies if e.alive]
        self.cd_timer += dt * self.cd_rate()
        if self.cd_timer >= self.cd_max and living:
            self.cd_timer = 0.0
            target = min(living, key=lambda e: math.hypot(e.x - self.x, e.y - self.y))
            # --- your attack here ---
            target.receive_damage(15, self, world)
            world["effects"].append(RingEffect(target.x, target.y, target.radius + 10, self.color))

        self.move_and_bounce(dt)

    def draw(self, surf, enemies):
        if not self.alive:
            return
        cx, cy = int(self.x), int(self.y)
        draw_ball_avatar(surf, self.type, cx, cy, self.radius)
        if self.stun_timer > 0:
            draw_dashed_circle(surf, MEDUSA_PURPLE, (cx, cy), self.radius + 6, 3, 16)


# Uncomment to enable (the template is NOT imported by default):
# register_solo("TEMPLATE", "Template", NEW_COLOR, TemplateFighter)
