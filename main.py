import pygame
import random
import math
from pathlib import Path

pygame.init()

# ==========================================================
# GEARWING: FLIGHT PROTOCOL 3.0
# Theme: Gear + Flight
# Features:
# - Collectible gears that recharge the flight core
# - Wind-Up Boost (E)
# - Gear Shift slow motion (Q)
# - Moving mechanical gates
# - Progressive zones with changing sky colors
# - Particles, boost trail, screen shake, missions
# - Persistent best score and total gears
# ==========================================================

WIDTH, HEIGHT = 480, 700
FPS = 60
GROUND_HEIGHT = 85
PLAY_HEIGHT = HEIGHT - GROUND_HEIGHT

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("GEARWING: Flight Protocol 3.0")
clock = pygame.time.Clock()

FONT = pygame.font.SysFont("arial", 24, bold=True)
BIG_FONT = pygame.font.SysFont("arial", 40, bold=True)
SMALL_FONT = pygame.font.SysFont("arial", 16, bold=True)
TINY_FONT = pygame.font.SysFont("arial", 12, bold=True)

WHITE = (245, 249, 245)
DARK = (20, 35, 48)
BRASS = (218, 163, 73)
BRASS_LIGHT = (255, 207, 112)
BRASS_DARK = (132, 83, 42)
TEAL = (45, 196, 177)
TEAL_DARK = (21, 113, 113)
PANEL = (24, 49, 65)
MUTED = (164, 190, 194)
RED = (245, 105, 95)
PURPLE = (164, 119, 255)

BIRD_X = 115
BIRD_RADIUS = 17
GRAVITY = 1350
FLAP_VELOCITY = -390

PIPE_WIDTH = 72
PIPE_GAP = 190
BASE_PIPE_SPEED = 185
PIPE_INTERVAL = 245

MAX_ENERGY = 100
BOOST_COST = 50
BOOST_VELOCITY = -570
BOOST_DURATION = 0.22

SHIFT_COST = 35
SHIFT_DURATION = 1.7
SHIFT_COOLDOWN = 5.0

score_file = Path(__file__).with_name("best_score.txt")
gears_file = Path(__file__).with_name("total_gears.txt")

try:
    best_score = int(score_file.read_text().strip())
except (OSError, ValueError):
    best_score = 0

try:
    total_gears_saved = int(gears_file.read_text().strip())
except (OSError, ValueError):
    total_gears_saved = 0

# Three zones; the palette changes as the run progresses.
ZONES = [
    {"name": "WORKSHOP", "top": (16, 37, 58), "bottom": (36, 91, 105)},
    {"name": "SKY FACTORY", "top": (35, 32, 66), "bottom": (76, 75, 130)},
    {"name": "STORM ZONE", "top": (15, 27, 45), "bottom": (48, 83, 103)},
]

def make_background(zone_index):
    zone = ZONES[zone_index]
    surf = pygame.Surface((WIDTH, HEIGHT))
    for y in range(HEIGHT):
        t = y / HEIGHT
        color = tuple(int(zone["top"][i] * (1 - t) + zone["bottom"][i] * t)
                      for i in range(3))
        pygame.draw.line(surf, color, (0, y), (WIDTH, y))

    # Clouds and distant mechanical silhouettes
    rng = random.Random(100 + zone_index)
    for _ in range(7):
        x = rng.randint(-20, WIDTH + 20)
        y = rng.randint(90, HEIGHT - 150)
        r = rng.randint(12, 28)
        pygame.draw.circle(surf, (58, 91, 111), (x, y), r)
        pygame.draw.circle(surf, (58, 91, 111), (x + r, y + 4), int(r * .7))
    for x, y, r in [(420, 115, 24), (45, 330, 15), (385, 440, 19), (290, 170, 11)]:
        pygame.draw.circle(surf, (54, 83, 101), (x, y), r, 2)
        pygame.draw.circle(surf, BRASS_DARK, (x, y), 4)
    return surf

backgrounds = [make_background(i) for i in range(len(ZONES))]

ground = pygame.Surface((WIDTH, GROUND_HEIGHT))
ground.fill((28, 43, 53))
pygame.draw.rect(ground, TEAL, (0, 0, WIDTH, 5))
pygame.draw.rect(ground, BRASS_DARK, (0, 5, WIDTH, 4))
for gx in range(0, WIDTH, 40):
    pygame.draw.line(ground, (65, 87, 92), (gx, 18), (gx, GROUND_HEIGHT), 1)
    pygame.draw.circle(ground, BRASS, (gx + 8, 27), 2)

bird_y = HEIGHT * .43
bird_velocity = 0.0
pipes = []
collectibles = []
particles = []
score = 0
game_state = "ready"
ground_offset = 0.0
pipe_timer = 0.0
flight_energy = 0
boost_timer = 0.0
gear_rotation = 0.0
shift_timer = 0.0
shift_cooldown = 0.0
shake_timer = 0.0
shake_strength = 0
run_gears = 0
zone_index = 0
mission_text = ""
mission_timer = 0.0
last_mission_score = 0
best_score = best_score
total_gears_saved = total_gears_saved

# Main menu, garage and cosmetic progression.
player_data_file = Path(__file__).with_name("player_data.json")
SKINS = [
    {"id": "classic", "name": "CLASSIC CLOCKWORK", "cost": 0,
     "body": BRASS, "highlight": BRASS_LIGHT, "wing": TEAL_DARK, "eye": TEAL},
    {"id": "inferno", "name": "INFERNO ENGINE", "cost": 30,
     "body": (225, 83, 55), "highlight": (255, 177, 85), "wing": (130, 42, 48), "eye": (255, 220, 120)},
    {"id": "neon", "name": "NEON CIRCUIT", "cost": 60,
     "body": (135, 92, 255), "highlight": (216, 190, 255), "wing": (64, 39, 142), "eye": (70, 255, 230)},
    {"id": "apex", "name": "APEX AUTOMATON", "cost": 100,
     "body": (205, 218, 226), "highlight": (255, 255, 255), "wing": (77, 110, 132), "eye": (255, 196, 70)},
]
wallet_gears = total_gears_saved
unlocked_skins = ["classic"]
equipped_skin = "classic"
screen_state = "menu"  # menu, shop, game
menu_buttons = {}
shop_buttons = {}
gameover_buttons = {}

try:
    if player_data_file.exists():
        import json
        _player_data = json.loads(player_data_file.read_text(encoding="utf-8"))
        wallet_gears = max(0, int(_player_data.get("wallet_gears", wallet_gears)))
        unlocked_skins = _player_data.get("unlocked_skins", ["classic"])
        if not isinstance(unlocked_skins, list):
            unlocked_skins = ["classic"]
        if "classic" not in unlocked_skins:
            unlocked_skins.insert(0, "classic")
        unlocked_skins = [skin_id for skin_id in unlocked_skins if skin_id in {skin["id"] for skin in SKINS}]
        equipped_skin = _player_data.get("equipped_skin", "classic")
        if equipped_skin not in unlocked_skins:
            equipped_skin = "classic"
except (OSError, ValueError, TypeError):
    wallet_gears = total_gears_saved
    unlocked_skins = ["classic"]
    equipped_skin = "classic"

def save_progress():
    try:
        score_file.write_text(str(best_score))
        gears_file.write_text(str(total_gears_saved))
        import json
        player_data_file.write_text(json.dumps({
            "wallet_gears": wallet_gears,
            "unlocked_skins": unlocked_skins,
            "equipped_skin": equipped_skin,
        }, indent=2), encoding="utf-8")
    except OSError:
        pass

def reset_game():
    global bird_y, bird_velocity, pipes, collectibles, particles
    global score, game_state, ground_offset, pipe_timer
    global flight_energy, boost_timer, gear_rotation
    global shift_timer, shift_cooldown, shake_timer, shake_strength
    global run_gears, zone_index, mission_text, mission_timer, last_mission_score

    bird_y = HEIGHT * .43
    bird_velocity = 0.0
    pipes = []
    collectibles = []
    particles = []
    score = 0
    flight_energy = 20
    boost_timer = 0.0
    ground_offset = 0.0
    pipe_timer = 0.0
    gear_rotation = 0.0
    shift_timer = 0.0
    shift_cooldown = 0.0
    shake_timer = 0.0
    shake_strength = 0
    run_gears = 0
    zone_index = 0
    mission_text = "MISSION: COLLECT 5 GEARS"
    mission_timer = 3.5
    last_mission_score = 0
    game_state = "playing"

def flap():
    global bird_velocity
    if game_state == "ready":
        reset_game()
    if game_state == "playing":
        bird_velocity = FLAP_VELOCITY
        add_particles(BIRD_X - 15, bird_y + 5, TEAL, 4, 100)

def activate_boost():
    global flight_energy, bird_velocity, boost_timer
    if game_state == "playing" and flight_energy >= BOOST_COST:
        flight_energy -= BOOST_COST
        bird_velocity = BOOST_VELOCITY
        boost_timer = BOOST_DURATION
        add_particles(BIRD_X - 20, bird_y, BRASS_LIGHT, 18, 180)

def activate_gear_shift():
    global flight_energy, shift_timer, shift_cooldown
    if game_state == "playing" and shift_timer <= 0 and shift_cooldown <= 0 and flight_energy >= SHIFT_COST:
        flight_energy -= SHIFT_COST
        shift_timer = SHIFT_DURATION
        shift_cooldown = SHIFT_COOLDOWN
        add_particles(BIRD_X, bird_y, PURPLE, 22, 150)

def create_pipe():
    gap_y = random.randint(220, 490)
    pipe = {
        "x": float(WIDTH + 20),
        "gap_y": gap_y,
        "scored": False,
        "moving": score >= 5 and random.random() < 0.35,
        "phase": random.random() * math.tau,
        "base_gap_y": gap_y,
    }
    pipes.append(pipe)
    # A collectible gear sits near the middle of some gaps.
    if random.random() < 0.78:
        collectibles.append({
            "x": float(WIDTH + PIPE_WIDTH / 2),
            "y": float(gap_y + random.randint(-38, 38)),
            "collected": False,
            "rotation": random.randint(0, 359),
        })

def end_game():
    global game_state, best_score, shake_timer, shake_strength
    if game_state != "playing":
        return
    game_state = "gameover"
    shake_timer = 0.25
    shake_strength = 7
    if score > best_score:
        best_score = score
    save_progress()

def add_particles(x, y, color, count=8, speed=120):
    for _ in range(count):
        angle = random.uniform(0, math.tau)
        velocity = random.uniform(speed * .35, speed)
        particles.append({
            "x": float(x), "y": float(y),
            "vx": math.cos(angle) * velocity,
            "vy": math.sin(angle) * velocity,
            "life": random.uniform(.2, .55),
            "max_life": .55,
            "radius": random.randint(2, 4),
            "color": color,
        })

def draw_text(text, font, color, center, target=None):
    target = target or screen
    image = font.render(str(text), True, color)
    target.blit(image, image.get_rect(center=center))

def draw_gear(target, cx, cy, radius, rotation:float=0, color=BRASS):
    for angle in range(0, 360, 45):
        a = math.radians(angle + rotation)
        tx = cx + math.cos(a) * (radius - 1)
        ty = cy + math.sin(a) * (radius - 1)
        tooth = pygame.Rect(int(tx) - 4, int(ty) - 4, 8, 8)
        pygame.draw.rect(target, color, tooth, border_radius=2)
    pygame.draw.circle(target, BRASS_DARK, (cx, cy), radius)
    pygame.draw.circle(target, color, (cx, cy), max(3, radius - 4))
    pygame.draw.circle(target, DARK, (cx, cy), max(3, radius // 3))
    pygame.draw.circle(target, TEAL, (cx, cy), 3)

def draw_pipe(pipe, target):
    x = int(pipe["x"])
    gap_y = int(pipe["gap_y"])
    top = pygame.Rect(x, 0, PIPE_WIDTH, gap_y - PIPE_GAP // 2)
    bottom = pygame.Rect(x, gap_y + PIPE_GAP // 2, PIPE_WIDTH,
                         PLAY_HEIGHT - (gap_y + PIPE_GAP // 2))
    for rect in (top, bottom):
        pygame.draw.rect(target, TEAL_DARK, rect)
        pygame.draw.rect(target, BRASS, rect, 3)
        if rect.height > 20:
            pygame.draw.rect(target, TEAL, (rect.x + 9, rect.y, 5, rect.height))
            pygame.draw.rect(target, BRASS_DARK, (rect.right - 14, rect.y, 5, rect.height))
        for ry in range(rect.top + 25, rect.bottom - 8, 35):
            pygame.draw.circle(target, BRASS_LIGHT, (rect.x + 29, ry), 3)
        if rect.height > 85:
            draw_gear(target, rect.centerx, rect.centery, 17, gear_rotation, BRASS)
    lip_height = 18
    pygame.draw.rect(target, BRASS, (x - 5, top.bottom - lip_height, PIPE_WIDTH + 10, lip_height), border_radius=3)
    pygame.draw.rect(target, BRASS, (x - 5, bottom.top, PIPE_WIDTH + 10, lip_height), border_radius=3)
    pygame.draw.line(target, TEAL, (x, top.bottom - 4), (x + PIPE_WIDTH, top.bottom - 4), 3)
    pygame.draw.line(target, TEAL, (x, bottom.top + 4), (x + PIPE_WIDTH, bottom.top + 4), 3)

def draw_bird(target):
    x, y = BIRD_X, int(bird_y)
    skin = next((item for item in SKINS if item["id"] == equipped_skin), SKINS[0])
    body_color = skin["body"]
    highlight_color = skin["highlight"]
    wing_color = skin["wing"]
    eye_color = skin["eye"]
    if boost_timer > 0:
        pygame.draw.circle(target, TEAL, (x, y), 31, 3)
        pygame.draw.circle(target, (89, 240, 210), (x, y), 24, 1)
        pygame.draw.polygon(target, BRASS_LIGHT, [(x-18,y+3),(x-44,y-5),(x-31,y+8)])
    if shift_timer > 0:
        pygame.draw.circle(target, PURPLE, (x, y), 35, 2)
    pygame.draw.polygon(target, wing_color, [(x-15,y-3),(x-29,y-12),(x-25,y+3)])
    pygame.draw.ellipse(target, DARK, (x-21,y-17,43,35))
    pygame.draw.ellipse(target, body_color, (x-19,y-15,39,30))
    pygame.draw.ellipse(target, highlight_color, (x-12,y-11,22,9))
    wing_angle = max(-8, min(12, int(bird_velocity / 30)))
    wing_points = [(x-13,y+1),(x-8,y-9+wing_angle),(x+7,y-2+wing_angle),(x+4,y+8)]
    pygame.draw.polygon(target, wing_color, wing_points)
    pygame.draw.line(target, eye_color, (x-8,y-1+wing_angle//2),(x+3,y+3),3)
    pygame.draw.circle(target, BRASS_DARK, (x+9,y-6),9)
    pygame.draw.circle(target, eye_color, (x+9,y-6),6)
    pygame.draw.circle(target, WHITE, (x+10,y-7),2)
    pygame.draw.polygon(target, BRASS_LIGHT, [(x+16,y-1),(x+30,y+3),(x+16,y+7)])
    pygame.draw.circle(target, BRASS_DARK, (x-9,y+7),2)

def draw_ground(target, offset):
    target.blit(ground, (-int(offset), HEIGHT-GROUND_HEIGHT))
    target.blit(ground, (WIDTH-int(offset), HEIGHT-GROUND_HEIGHT))

def draw_energy_meter(target):
    x, y, bar_width, bar_height = 18, 22, 110, 15
    draw_text("FLIGHT CORE", SMALL_FONT, WHITE, (x+bar_width//2,y-2), target)
    bar_y = y + 12
    pygame.draw.rect(target, DARK, (x,bar_y,bar_width,bar_height), border_radius=5)
    fill_width = int(bar_width * flight_energy / MAX_ENERGY)
    if fill_width > 0:
        pygame.draw.rect(target, TEAL if flight_energy < 75 else BRASS_LIGHT,
                         (x,bar_y,fill_width,bar_height), border_radius=5)
    draw_text("E: BOOST", TINY_FONT, BRASS_LIGHT if flight_energy >= BOOST_COST else MUTED,
              (WIDTH-57, 24), target)
    shift_label = "Q: SHIFT" if shift_cooldown <= 0 and flight_energy >= SHIFT_COST else "Q: RECHARGE"
    draw_text(shift_label, TINY_FONT, PURPLE if shift_cooldown <= 0 and flight_energy >= SHIFT_COST else MUTED,
              (WIDTH-65, 43), target)
    if shift_timer > 0:
        draw_text("TIME DISTORTION", TINY_FONT, PURPLE, (WIDTH//2, 91), target)

def draw_overlay(title, lines):
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((5, 15, 25, 185))
    screen.blit(overlay, (0,0))
    panel = pygame.Rect(30, 205, WIDTH-60, 300)
    pygame.draw.rect(screen, PANEL, panel, border_radius=20)
    pygame.draw.rect(screen, BRASS, panel, 2, border_radius=20)
    pygame.draw.line(screen, TEAL, (panel.left+25,panel.top+12),(panel.right-25,panel.top+12),3)
    draw_text(title, BIG_FONT, BRASS_LIGHT, (WIDTH//2, 260))
    for i, line in enumerate(lines):
        draw_text(line, SMALL_FONT, MUTED, (WIDTH//2, 318+i*30))

def draw_hud():
    score_panel = pygame.Rect(WIDTH//2-34, 22, 68, 48)
    pygame.draw.rect(screen, PANEL, score_panel, border_radius=14)
    pygame.draw.rect(screen, BRASS, score_panel, 2, border_radius=14)
    draw_text(score, BIG_FONT, WHITE, (WIDTH//2,46))
    draw_energy_meter(screen)
    draw_text(ZONES[zone_index]["name"], TINY_FONT, BRASS_LIGHT, (WIDTH//2, 83))
    draw_text(f"GEARS {run_gears}", TINY_FONT, WHITE, (WIDTH-55, 66))
    if mission_timer > 0 and mission_text:
        draw_text(mission_text, TINY_FONT, BRASS_LIGHT, (WIDTH//2, HEIGHT- GROUND_HEIGHT-18))

def draw_particles(target):
    for p in particles:
        alpha = max(0, min(255, int(255 * p["life"] / p["max_life"])))
        radius = max(1, int(p["radius"] * p["life"] / p["max_life"]))
        pygame.draw.circle(target, p["color"], (int(p["x"]), int(p["y"])), radius)

def update_particles(dt):
    for p in particles:
        p["x"] += p["vx"] * dt
        p["y"] += p["vy"] * dt
        p["life"] -= dt
        p["vx"] *= 0.98
        p["vy"] *= 0.98
    particles[:] = [p for p in particles if p["life"] > 0]

def show_mission(text):
    global mission_text, mission_timer
    mission_text = text
    mission_timer = 3.0

def draw_button(label, rect, active=True, target=None, accent=BRASS):
    target = target or screen
    fill = (38, 69, 83) if active else (35, 48, 57)
    pygame.draw.rect(target, fill, rect, border_radius=12)
    pygame.draw.rect(target, accent if active else MUTED, rect, 2, border_radius=12)
    draw_text(label, SMALL_FONT, WHITE if active else MUTED, rect.center, target)


def draw_brand_background():
    screen.blit(backgrounds[0], (0, 0))
    # Decorative gear rings frame the title without distracting from buttons.
    pygame.draw.circle(screen, (49, 88, 101), (45, 125), 33, 2)
    pygame.draw.circle(screen, BRASS_DARK, (45, 125), 22, 2)
    pygame.draw.circle(screen, (49, 88, 101), (438, 190), 45, 2)
    pygame.draw.circle(screen, BRASS_DARK, (438, 190), 31, 2)
    draw_ground(screen, 0)


def draw_main_menu():
    global menu_buttons
    draw_brand_background()
    draw_text("GEARWING", BIG_FONT, BRASS_LIGHT, (WIDTH // 2, 118))
    draw_text("FLIGHT PROTOCOL", FONT, TEAL, (WIDTH // 2, 157))
    draw_text("GEAR + FLIGHT ARCADE", TINY_FONT, MUTED, (WIDTH // 2, 190))
    # Animated-looking decorative bird preview.
    preview_y = 265 + math.sin(pygame.time.get_ticks() / 360) * 7
    pygame.draw.circle(screen, (23, 54, 67), (WIDTH // 2, int(preview_y)), 49, 2)
    pygame.draw.circle(screen, BRASS_DARK, (WIDTH // 2, int(preview_y)), 39, 1)
    skin = next((item for item in SKINS if item["id"] == equipped_skin), SKINS[0])
    px, py = WIDTH // 2, int(preview_y)
    pygame.draw.polygon(screen, skin["wing"], [(px-14, py+2), (px-34, py-12), (px-29, py+10)])
    pygame.draw.ellipse(screen, skin["body"], (px-22, py-17, 44, 34))
    pygame.draw.ellipse(screen, skin["highlight"], (px-13, py-12, 23, 9))
    pygame.draw.circle(screen, skin["eye"], (px+11, py-6), 7)
    pygame.draw.circle(screen, WHITE, (px+12, py-7), 2)
    pygame.draw.polygon(screen, BRASS_LIGHT, [(px+19, py-1), (px+34, py+4), (px+19, py+8)])
    draw_text(f"BEST FLIGHT  {best_score}", SMALL_FONT, WHITE, (WIDTH // 2, 340))
    draw_text(f"GEAR WALLET  {wallet_gears}", SMALL_FONT, BRASS_LIGHT, (WIDTH // 2, 371))
    menu_buttons = {
        "play": pygame.Rect(82, 410, WIDTH - 164, 52),
        "garage": pygame.Rect(82, 476, WIDTH - 164, 48),
        "quit": pygame.Rect(82, 538, WIDTH - 164, 42),
    }
    draw_button("PLAY", menu_buttons["play"], accent=TEAL)
    draw_button("SKIN GARAGE", menu_buttons["garage"], accent=BRASS)
    draw_button("QUIT", menu_buttons["quit"], accent=RED)
    draw_text("SPACE / CLICK TO FLY  •  E BOOST  •  Q GEAR SHIFT", TINY_FONT, MUTED, (WIDTH // 2, 610))


def draw_skin_garage():
    global shop_buttons
    draw_brand_background()
    draw_text("SKIN GARAGE", BIG_FONT, BRASS_LIGHT, (WIDTH // 2, 58))
    draw_text(f"YOUR GEARS: {wallet_gears}", SMALL_FONT, TEAL, (WIDTH // 2, 96))
    shop_buttons = {"back": pygame.Rect(20, 22, 86, 35)}
    draw_button("BACK", shop_buttons["back"], accent=TEAL)
    card_y = 125
    for index, skin in enumerate(SKINS):
        y = card_y + index * 119
        card = pygame.Rect(22, y, WIDTH - 44, 105)
        pygame.draw.rect(screen, PANEL, card, border_radius=14)
        pygame.draw.rect(screen, BRASS_DARK, card, 1, border_radius=14)
        # Preview the skin's palette.
        cx, cy = 65, y + 51
        pygame.draw.circle(screen, DARK, (cx, cy), 25)
        pygame.draw.ellipse(screen, skin["body"], (cx - 19, cy - 14, 38, 28))
        pygame.draw.ellipse(screen, skin["highlight"], (cx - 10, cy - 10, 18, 7))
        pygame.draw.polygon(screen, skin["wing"], [(cx - 10, cy + 1), (cx - 21, cy - 8), (cx - 20, cy + 8)])
        pygame.draw.circle(screen, skin["eye"], (cx + 10, cy - 5), 5)
        draw_text(skin["name"], SMALL_FONT, WHITE, (225, y + 25))
        if skin["id"] == equipped_skin:
            label, active, accent = "EQUIPPED", False, TEAL
        elif skin["id"] in unlocked_skins:
            label, active, accent = "EQUIP", True, TEAL
        else:
            label, active, accent = f"BUY  {skin['cost']} GEARS", wallet_gears >= skin["cost"], BRASS
        button = pygame.Rect(143, y + 48, 190, 37)
        shop_buttons[skin["id"]] = button
        draw_button(label, button, active=active, accent=accent)
    draw_text("Collect gears during flights to unlock new looks", TINY_FONT, MUTED, (WIDTH // 2, 617))


def handle_menu_click(position):
    global screen_state, running
    if menu_buttons.get("play") and menu_buttons["play"].collidepoint(position):
        reset_game()
        screen_state = "game"
    elif menu_buttons.get("garage") and menu_buttons["garage"].collidepoint(position):
        screen_state = "shop"
    elif menu_buttons.get("quit") and menu_buttons["quit"].collidepoint(position):
        running = False


def handle_shop_click(position):
    global screen_state, wallet_gears, unlocked_skins, equipped_skin
    if shop_buttons.get("back") and shop_buttons["back"].collidepoint(position):
        screen_state = "menu"
        return
    for skin in SKINS:
        rect = shop_buttons.get(skin["id"])
        if rect and rect.collidepoint(position):
            skin_id = skin["id"]
            if skin_id in unlocked_skins:
                equipped_skin = skin_id
            elif wallet_gears >= skin["cost"]:
                wallet_gears -= skin["cost"]
                unlocked_skins.append(skin_id)
                equipped_skin = skin_id
            save_progress()
            return


running = True
while running:
    dt = min(clock.tick(FPS) / 1000.0, 0.033)
    world_dt = dt * (0.32 if shift_timer > 0 else 1.0)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if screen_state == "shop":
                    screen_state = "menu"
                elif screen_state == "game":
                    screen_state = "menu"
                    game_state = "ready"
                    shake_timer = 0.0
                    shake_strength = 0
                else:
                    running = False
            elif screen_state == "game":
                if event.key == pygame.K_SPACE:
                    if game_state == "gameover":
                        reset_game()
                    else:
                        flap()
                elif event.key == pygame.K_e:
                    activate_boost()
                elif event.key == pygame.K_q:
                    activate_gear_shift()
            elif screen_state == "menu" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                reset_game()
                screen_state = "game"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if screen_state == "menu":
                handle_menu_click(event.pos)
            elif screen_state == "shop":
                handle_shop_click(event.pos)
            elif screen_state == "game":
                if game_state == "gameover":
                    if gameover_buttons.get("retry") and gameover_buttons["retry"].collidepoint(event.pos):
                        reset_game()
                    elif gameover_buttons.get("menu") and gameover_buttons["menu"].collidepoint(event.pos):
                        screen_state = "menu"
                        game_state = "ready"
                    else:
                        reset_game()
                else:
                    flap()

    if screen_state == "game":
        # Screen shake must decay even after a collision changes the state to gameover.
        if shake_timer > 0:
            shake_timer = max(0.0, shake_timer - dt)
            if shake_timer == 0:
                shake_strength = 0

        if game_state == "playing":
            if boost_timer > 0:
                boost_timer = max(0.0, boost_timer - dt)
                bird_velocity -= 850 * dt
            if shift_timer > 0:
                shift_timer = max(0.0, shift_timer - dt)
            if shift_cooldown > 0:
                shift_cooldown = max(0.0, shift_cooldown - dt)
            if mission_timer > 0:
                mission_timer = max(0.0, mission_timer - dt)

            bird_velocity += GRAVITY * dt
            bird_y += bird_velocity * dt
            ground_offset = (ground_offset + BASE_PIPE_SPEED * world_dt) % WIDTH
            gear_rotation = (gear_rotation + 100 * world_dt) % 360
            pipe_timer += BASE_PIPE_SPEED * world_dt

            if pipe_timer >= PIPE_INTERVAL:
                create_pipe()
                pipe_timer -= PIPE_INTERVAL

            # Slightly increase difficulty as score rises.
            pipe_speed = min(BASE_PIPE_SPEED + score * 2.0, 255)
            for pipe in pipes:
                pipe["x"] -= pipe_speed * world_dt
                if pipe["moving"]:
                    pipe["gap_y"] = pipe["base_gap_y"] + math.sin(pygame.time.get_ticks() / 450 + pipe["phase"]) * 38
                    pipe["gap_y"] = max(205, min(510, pipe["gap_y"]))
                if not pipe["scored"] and pipe["x"] + PIPE_WIDTH < BIRD_X:
                    pipe["scored"] = True
                    score += 1
                    if score % 5 == 0:
                        zone_index = min(2, score // 5)
                        show_mission(f"ZONE UNLOCKED: {ZONES[zone_index]['name']}")
                    if score % 10 == 0:
                        show_mission("MISSION COMPLETE: +25 CORE")
                        flight_energy = min(MAX_ENERGY, flight_energy + 25)

            pipes[:] = [p for p in pipes if p["x"] > -PIPE_WIDTH - 10]

            # Move collectible gears and detect collection.
            bird_rect = pygame.Rect(BIRD_X-BIRD_RADIUS, int(bird_y)-BIRD_RADIUS, BIRD_RADIUS*2, BIRD_RADIUS*2)
            for gear in collectibles:
                gear["x"] -= pipe_speed * world_dt
                gear["rotation"] = (gear["rotation"] + 180 * dt) % 360
                gear_rect = pygame.Rect(int(gear["x"])-12, int(gear["y"])-12, 24, 24)
                if not gear["collected"] and bird_rect.colliderect(gear_rect):
                    gear["collected"] = True
                    run_gears += 1
                    total_gears_saved += 1
                    wallet_gears += 1
                    flight_energy = min(MAX_ENERGY, flight_energy + 20)
                    add_particles(gear["x"], gear["y"], BRASS_LIGHT, 15, 160)
                    show_mission("GEAR COLLECTED: +20 CORE")
                    if run_gears == 5:
                        show_mission("MISSION COMPLETE: 5 GEARS!")
                    save_progress()
            collectibles[:] = [g for g in collectibles if g["x"] > -30 and not g["collected"]]

            # Mission hint.
            if run_gears < 5 and mission_timer <= 0:
                mission_text = "MISSION: COLLECT 5 GEARS"
                mission_timer = 0.01

            # Collision checks.
            if bird_y - BIRD_RADIUS <= 0 or bird_y + BIRD_RADIUS >= PLAY_HEIGHT:
                end_game()
            else:
                for pipe in pipes:
                    x = int(pipe["x"])
                    gy = int(pipe["gap_y"])
                    top = pygame.Rect(x, 0, PIPE_WIDTH, gy - PIPE_GAP//2)
                    bottom = pygame.Rect(x, gy + PIPE_GAP//2, PIPE_WIDTH, PLAY_HEIGHT-(gy+PIPE_GAP//2))
                    if bird_rect.colliderect(top) or bird_rect.colliderect(bottom):
                        end_game()
                        break

            # Continuous flight trail.
            if random.random() < (0.65 if boost_timer > 0 else 0.18):
                color = BRASS_LIGHT if boost_timer > 0 else TEAL
                particles.append({
                    "x": BIRD_X-18.0, "y": bird_y+random.randint(-5,5),
                    "vx": random.uniform(-100,-35), "vy": random.uniform(-35,35),
                    "life": .22, "max_life": .22, "radius": random.randint(2,4), "color": color
                })

        update_particles(dt)

    if screen_state == "game":
        # Render gameplay and the game-over controls.
        scene = pygame.Surface((WIDTH, HEIGHT))
        scene.blit(backgrounds[zone_index], (0, 0))
        for gear in collectibles:
            gx, gy = int(gear["x"]), int(gear["y"])
            draw_gear(scene, gx, gy, 11, gear["rotation"], BRASS_LIGHT)
            pygame.draw.circle(scene, TEAL, (gx, gy), 17, 1)
        for pipe in pipes:
            draw_pipe(pipe, scene)
        draw_ground(scene, ground_offset)
        draw_bird(scene)
        draw_particles(scene)
        if shake_timer > 0:
            ox = random.randint(-shake_strength, shake_strength)
            oy = random.randint(-shake_strength, shake_strength)
        else:
            ox = oy = 0
        screen.fill(DARK)
        screen.blit(scene, (ox, oy))
        draw_hud()
        gameover_buttons = {}
        if game_state == "ready":
            draw_overlay("GEARWING 3.0", [
                "FLIGHT PROTOCOL", "SPACE / CLICK: FLY",
                "E: BOOST  |  Q: GEAR SHIFT", "COLLECT GEARS TO POWER UP",
            ])
        elif game_state == "gameover":
            draw_overlay("FLIGHT FAILED", [
                f"FLIGHT SCORE: {score}", f"BEST SCORE: {best_score}",
                f"GEARS THIS RUN: {run_gears}",
            ])
            gameover_buttons = {
                "retry": pygame.Rect(56, 438, 166, 45),
                "menu": pygame.Rect(239, 438, 166, 45),
            }
            draw_button("RETRY", gameover_buttons["retry"], accent=TEAL)
            draw_button("MAIN MENU", gameover_buttons["menu"], accent=BRASS)
        draw_text("ESC: MAIN MENU", TINY_FONT, MUTED, (WIDTH // 2, HEIGHT - 17))
    elif screen_state == "menu":
        draw_main_menu()
    elif screen_state == "shop":
        draw_skin_garage()

    pygame.display.flip()

pygame.quit()
