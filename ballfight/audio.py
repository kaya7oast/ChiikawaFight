"""
Procedural sound effects (no numpy, so it also runs in the browser build).
Sounds are generated to match whatever format the mixer actually opened with.
"""
import array
import math
import random

import pygame

pygame.mixer.pre_init(22050, -16, 2, 512)
pygame.init()
print(f"[Audio] mixer opened as {pygame.mixer.get_init()}")


class _Silent:
    def play(self, *a, **k):
        pass


def make_sfx(f0, f1, dur, wave="sine", vol=0.14):
    init = pygame.mixer.get_init()
    if not init:
        return _Silent()
    sr, size, channels = init
    n = int(sr * dur)
    # match the sample format the mixer really opened with (Windows often gives 32-bit float,
    # and an int16 buffer played as float is silent)
    if size == 32:
        code, scale, offset = "f", 1.0, 0.0
    elif size == -32:
        code, scale, offset = "i", 2147483647, 0
    elif size == 16:
        code, scale, offset = "H", 32767, 32768
    elif size == 8:
        code, scale, offset = "B", 127, 128
    elif size == -8:
        code, scale, offset = "b", 127, 0
    else:
        code, scale, offset = "h", 32767, 0
    buf = array.array(code)
    phase = 0.0
    for i in range(n):
        t = i / n
        freq = f0 + (f1 - f0) * t
        phase += 2 * math.pi * freq / sr
        if wave == "square":
            s = 1.0 if math.sin(phase) >= 0 else -1.0
        elif wave == "noise":
            s = random.uniform(-1, 1)
        else:
            s = math.sin(phase)
        v = s * (1.0 - t * 0.99) * vol * scale + offset
        if code != "f":
            v = int(v)
        for _ in range(channels):
            buf.append(v)
    try:
        return pygame.mixer.Sound(buffer=buf.tobytes())
    except Exception:
        return _Silent()


SFX_BOUNCE = make_sfx(250, 200, 0.04, "sine", 0.07)
SFX_WEED = make_sfx(520, 880, 0.12, "sine", 0.14)
SFX_CHARGE = make_sfx(300, 580, 0.12, "square", 0.14)
SFX_SPIN = make_sfx(480, 210, 0.15, "square", 0.15)
SFX_HIT = make_sfx(280, 110, 0.09, "square", 0.18)
SFX_SEED = make_sfx(620, 340, 0.05, "square", 0.12)
SFX_JUMP = make_sfx(280, 680, 0.18, "sine", 0.13)
SFX_SLAM = make_sfx(180, 55, 0.25, "noise", 0.22)
SFX_WARN = make_sfx(740, 880, 0.14, "square", 0.15)
SFX_DEKATSUYO = make_sfx(220, 65, 0.38, "noise", 0.26)
SFX_CAR = make_sfx(140, 320, 0.22, "square", 0.15)
SFX_EXPLODE = make_sfx(160, 40, 0.32, "noise", 0.25)
SFX_COUNTER = make_sfx(880, 440, 0.16, "square", 0.20)
SFX_CLAW = make_sfx(520, 180, 0.08, "noise", 0.18)
SFX_STARE = make_sfx(310, 140, 0.30, "square", 0.20)
SFX_CRAZY = make_sfx(420, 920, 0.20, "square", 0.16)
