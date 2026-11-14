"""Team wrappers + the build_team() factory used by the game loop."""
from .config import ARENA_RECT
from . import registry


class SingleBossTeam:
    """A team made of one fighter. Fighter class must expose cd_timer / cd_max."""

    def __init__(self, fighter_cls, side):
        self.side = side
        x_pos = ARENA_RECT.left + 115 if side == "LEFT" else ARENA_RECT.right - 115
        self.boss = fighter_cls(x_pos, ARENA_RECT.centery)
        self.fighters = [self.boss]

    @property
    def cooldown_ratio(self):
        return min(1.0, self.boss.cd_timer / self.boss.cd_max)

    def update(self, dt, enemies, world):
        self.boss.update(dt, enemies, world)


def register_solo(key, name, color, fighter_cls, image=None):
    """One-liner to register a single-ball character (sprite + roster entry)."""
    registry.register_sprite(key, color, image=image, name=name)
    registry.register_roster(key, [(name, color)], lambda side: SingleBossTeam(fighter_cls, side))


def build_team(key, side):
    info = registry.ROSTER[key]
    team = info["build"](side)
    team.info = info
    return team
