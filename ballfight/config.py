import os

import pygame

# ==========================================
# WINDOW & ARENA CONFIGURATION
# ==========================================
WIDTH, HEIGHT = 540, 860
ARENA_SIZE = 460
ARENA_RECT = pygame.Rect((WIDTH - ARENA_SIZE) // 2, 210, ARENA_SIZE, ARENA_SIZE)
FPS = 60

# Draw the coloured ball behind characters that have a picture?
SHOW_BALL_UNDER_PICTURES = False

ASSET_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")

# Color Palette
BG_COLOR = (224, 236, 248)
WHITE = (255, 255, 255)
BLACK = (28, 28, 32)
DARK_SLATE = (32, 34, 38)
CHIIKAWA_PINK = (238, 130, 158)
HACHIWARE_BLUE = (104, 142, 206)
MOMONGA_CYAN = (96, 178, 230)
RAKKO_BROWN = (186, 135, 98)
CAR_PINK = (248, 148, 182)
USAGI_YELLOW = (245, 208, 76)
ANOKO_CREAM = (232, 118, 138)
MEDUSA_PURPLE = (175, 95, 225)
DEKATSUYO_GOLD = (245, 200, 55)
HP_GREEN = (98, 198, 108)
HP_GREEN_SHINE = (138, 222, 146)
WEED_GREEN = (115, 185, 95)
