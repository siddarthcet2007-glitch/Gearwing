
import pygame
import random
import math
from pathlib import Path

pygame.init()

# --------------------------------------------------
# GEARWING: FLIGHT PROTOCOL
# Theme: Gear + Flight
# --------------------------------------------------

WIDTH, HEIGHT = 480, 700
FPS = 60
GROUND_HEIGHT = 85

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("GEARWING: Flight Protocol")
clock = pygame.time.Clock()

# Fonts
FONT = pygame.font.SysFont("arial", 24, bold=True)
BIG_FONT = pygame.font.SysFont("arial", 40, bold=True)
SMALL_FONT = pygame.font.SysFont("arial", 16, bold=True)

# Color palette
WHITE = (245, 249, 245)
DARK = (20, 35, 48)
SKY_TOP = (16, 37, 58)
SKY_BOTTOM = (36, 91, 105)

BRASS = (218, 163, 73)
BRASS_LIGHT = (255, 207, 112)
BRASS_DARK = (132, 83, 42)

TEAL = (45, 196, 177)
TEAL_DARK = (21, 113, 113)
PANEL = (24, 49, 65)
MUTED = (164, 190, 194)

# --------------------------------------------------
# BACKGROUND
# --------------------------------------------------

background = pygame.Surface((WIDTH, HEIGHT))

for y in range(HEIGHT):
    t = y / HEIGHT
    color = tuple(
        int(SKY_TOP[i] * (1 - t) + SKY_BOTTOM[i] * t)
        for i in range(3)
    )
    pygame.draw.line(background, color, (0, y), (WIDTH, y))

# Background clouds
for x, y, scale in [
    (65, 130, 1.0),
    (360, 220, 0.8),
    (260, 390, 0.65),
]:
    for dx, dy, radius in [
        (-22, 5, 19),
        (0, -5, 25),
        (23, 6, 18),
    ]:
        pygame.draw.circle(
            background,
            (76, 121, 135),
            (
                int(x + dx * scale),
                int(y + dy * scale),
            ),
            int(radius * scale),
        )

# Subtle mechanical sky decorations
for x, y, radius in [
    (420, 115, 24),
    (45, 330, 15),
    (385, 440, 19),
]:
    pygame.draw.circle(
        background, (46, 91, 103), (x, y), radius, 2
    )
    pygame.draw.circle(
        background, BRASS_DARK, (x, y), 4
    )

# --------------------------------------------------
# MECHANICAL GROUND
# --------------------------------------------------

ground = pygame.Surface((WIDTH, GROUND_HEIGHT))
ground.fill((28, 43, 53))

pygame.draw.rect(ground, TEAL, (0, 0, WIDTH, 5))
pygame.draw.rect(ground, BRASS_DARK, (0, 5, WIDTH, 4))

for x in range(0, WIDTH, 40):
    pygame.draw.line(
        ground, (65, 87, 92),
        (x, 18), (x, GROUND_HEIGHT), 1
    )
    pygame.draw.circle(
        ground, BRASS, (x + 8, 27), 2
    )

# --------------------------------------------------
# GAME SETTINGS
# --------------------------------------------------

BIRD_X = 115
BIRD_RADIUS = 17

GRAVITY = 1350
FLAP_VELOCITY = -390

PIPE_WIDTH = 72
PIPE_GAP = 190
PIPE_SPEED = 185
PIPE_INTERVAL = 245

MAX_ENERGY = 100
BOOST_COST = 50
BOOST_VELOCITY = -570
BOOST_DURATION = 0.22

bird_y = HEIGHT * 0.43
bird_velocity = 0.0

pipes = []
score = 0
best_score = 0
game_state = "ready"

ground_offset = 0.0
pipe_timer = 0.0

flight_energy = 0
boost_timer = 0.0
gear_rotation = 0.0

score_file = Path(__file__).with_name("best_score.txt")

try:
    best_score = int(score_file.read_text().strip())
except (OSError, ValueError):
    best_score = 0

# --------------------------------------------------
# GAME FUNCTIONS
# --------------------------------------------------

def reset_game():
    global bird_y, bird_velocity, pipes
    global score, game_state
    global ground_offset, pipe_timer
    global flight_energy, boost_timer, gear_rotation

    bird_y = HEIGHT * 0.43
    bird_velocity = 0.0
    pipes = []

    score = 0
    flight_energy = 0
    boost_timer = 0.0
    ground_offset = 0.0
    pipe_timer = 0.0
    gear_rotation = 0.0

    game_state = "playing"


def flap():
    global bird_velocity, game_state

    if game_state == "ready":
        reset_game()

    if game_state == "playing":
        bird_velocity = FLAP_VELOCITY


def activate_boost():
    global flight_energy, bird_velocity, boost_timer

    if game_state != "playing":
        return

    if flight_energy >= BOOST_COST:
        flight_energy -= BOOST_COST
        bird_velocity = BOOST_VELOCITY
        boost_timer = BOOST_DURATION


def create_pipe():
    return {
        "x": float(WIDTH + 20),
        "gap_y": random.randint(215, 495),
        "scored": False,
    }


def end_game():
    global game_state, best_score

    if game_state != "playing":
        return

    game_state = "gameover"

    if score > best_score:
        best_score = score

        try:
            score_file.write_text(str(best_score))
        except OSError:
            pass


def draw_text(text, font, color, center):
    image = font.render(text, True, color)
    screen.blit(image, image.get_rect(center=center))


# --------------------------------------------------
# MECHANICAL BIRD
# --------------------------------------------------

def draw_bird():
    x = BIRD_X
    y = int(bird_y)

    # Boost glow
    if boost_timer > 0:
        pygame.draw.circle(
            screen, TEAL, (x, y), 29, 3
        )
        pygame.draw.circle(
            screen, (89, 240, 210), (x, y), 23, 1
        )

    # Tail stabilizer
    pygame.draw.polygon(
        screen, TEAL,
        [
            (x - 15, y - 3),
            (x - 29, y - 12),
            (x - 25, y + 3),
        ],
    )

    # Main body
    pygame.draw.ellipse(
        screen, DARK,
        (x - 21, y - 17, 43, 35),
    )

    pygame.draw.ellipse(
        screen, BRASS,
        (x - 19, y - 15, 39, 30),
    )

    # Body highlight
    pygame.draw.ellipse(
        screen, BRASS_LIGHT,
        (x - 12, y - 11, 22, 9),
    )

    # Wing changes angle with flight velocity
    wing_angle = max(
        -8, min(12, int(bird_velocity / 30))
    )

    wing_points = [
        (x - 13, y + 1),
        (x - 8, y - 9 + wing_angle),
        (x + 7, y - 2 + wing_angle),
        (x + 4, y + 8),
    ]

    pygame.draw.polygon(
        screen, TEAL_DARK, wing_points
    )
    pygame.draw.line(
        screen, TEAL,
        (x - 8, y - 1 + wing_angle // 2),
        (x + 3, y + 3),
        3,
    )

    # Eye housing
    pygame.draw.circle(
        screen, BRASS_DARK, (x + 9, y - 6), 9
    )
    pygame.draw.circle(
        screen, TEAL, (x + 9, y - 6), 6
    )
    pygame.draw.circle(
        screen, WHITE, (x + 10, y - 7), 2
    )

    # Front beak / nose
    pygame.draw.polygon(
        screen, BRASS_LIGHT,
        [
            (x + 16, y - 1),
            (x + 30, y + 3),
            (x + 16, y + 7),
        ],
    )

    # Rivets
    pygame.draw.circle(
        screen, BRASS_DARK, (x - 9, y + 7), 2
    )


# --------------------------------------------------
# GEAR OBSTACLES
# --------------------------------------------------

def draw_gear(cx, cy, radius, rotation=0):
    # Draw gear teeth
    for angle in range(0, 360, 45):
        a = math.radians(angle + rotation)

        tx = cx + math.cos(a) * (radius - 1)
        ty = cy + math.sin(a) * (radius - 1)

        tooth = pygame.Rect(
            int(tx) - 4, int(ty) - 4, 8, 8
        )

        pygame.draw.rect(
            screen, BRASS, tooth, border_radius=2
        )

    # Gear rings
    pygame.draw.circle(
        screen, BRASS_DARK, (cx, cy), radius
    )
    pygame.draw.circle(
        screen, BRASS, (cx, cy), radius - 4
    )
    pygame.draw.circle(
        screen, DARK, (cx, cy), max(3, radius // 3)
    )
    pygame.draw.circle(
        screen, TEAL, (cx, cy), 3
    )


def draw_pipe(pipe):
    x = int(pipe["x"])
    gap_y = pipe["gap_y"]

    top = pygame.Rect(
        x, 0, PIPE_WIDTH,
        gap_y - PIPE_GAP // 2,
    )

    bottom = pygame.Rect(
        x,
        gap_y + PIPE_GAP // 2,
        PIPE_WIDTH,
        HEIGHT - GROUND_HEIGHT
        - (gap_y + PIPE_GAP // 2),
    )

    # Mechanical columns
    for rect in (top, bottom):
        pygame.draw.rect(
            screen, TEAL_DARK, rect
        )
        pygame.draw.rect(
            screen, BRASS, rect, 3
        )

        if rect.height > 20:
            pygame.draw.rect(
                screen, TEAL,
                (rect.x + 9, rect.y, 5, rect.height),
            )
            pygame.draw.rect(
                screen, BRASS_DARK,
                (rect.right - 14, rect.y, 5, rect.height),
            )

        # Decorative rivets
        for ry in range(rect.top + 25, rect.bottom - 8, 35):
            pygame.draw.circle(
                screen, BRASS_LIGHT,
                (rect.x + 29, ry), 3,
            )

       # Draw a rotating gear inside the pipe section
        if rect.height > 85:
            gear_rotation =int(pygame.time.get_ticks() * 0.05)

            draw_gear(
                rect.centerx,
                rect.centery,
                17,
                gear_rotation,
            )

    # Metal rims around the gap
    lip_height = 18

    pygame.draw.rect(
        screen, BRASS,
        (
            x - 5,
            top.bottom - lip_height,
            PIPE_WIDTH + 10,
            lip_height,
        ),
        border_radius=3,
    )

    pygame.draw.rect(
        screen, BRASS,
        (
            x - 5,
            bottom.top,
            PIPE_WIDTH + 10,
            lip_height,
        ),
        border_radius=3,
    )

    pygame.draw.line(
        screen, TEAL,
        (x, top.bottom - 4),
        (x + PIPE_WIDTH, top.bottom - 4),
        3,
    )

    pygame.draw.line(
        screen, TEAL,
        (x, bottom.top + 4),
        (x + PIPE_WIDTH, bottom.top + 4),
        3,
    )


# --------------------------------------------------
# UI AND GROUND
# --------------------------------------------------

def draw_ground():
    offset = int(ground_offset)

    screen.blit(
        ground,
        (-offset, HEIGHT - GROUND_HEIGHT),
    )

    screen.blit(
        ground,
        (WIDTH - offset, HEIGHT - GROUND_HEIGHT),
    )


def draw_energy_meter():
    x, y = 18, 22
    bar_width, bar_height = 110, 15

    draw_text(
        "FLIGHT CORE",
        SMALL_FONT, WHITE,
        (x + bar_width // 2, y - 2),
    )

    bar_y = y + 12

    pygame.draw.rect(
        screen, DARK,
        (x, bar_y, bar_width, bar_height),
        border_radius=5,
    )

    fill_width = int(
        bar_width * flight_energy / MAX_ENERGY
    )

    if fill_width > 0:
        pygame.draw.rect(
            screen, TEAL,
            (x, bar_y, fill_width, bar_height),
            border_radius=5,
        )

    if flight_energy >= BOOST_COST:
        draw_text(
            "E: BOOST",
            SMALL_FONT, BRASS_LIGHT,
            (WIDTH - 66, 40),
        )
    else:
        draw_text(
            "E: CHARGING",
            SMALL_FONT, MUTED,
            (WIDTH - 78, 40),
        )


def draw_overlay(title, lines):
    overlay = pygame.Surface(
        (WIDTH, HEIGHT), pygame.SRCALPHA
    )
    overlay.fill((5, 15, 25, 180))
    screen.blit(overlay, (0, 0))

    panel = pygame.Rect(
        35, 225, WIDTH - 70, 255
    )

    pygame.draw.rect(
        screen, PANEL, panel, border_radius=20
    )
    pygame.draw.rect(
        screen, BRASS, panel, 2, border_radius=20
    )

    pygame.draw.line(
        screen, TEAL,
        (panel.left + 25, panel.top + 12),
        (panel.right - 25, panel.top + 12),
        3,
    )

    draw_text(
        title, BIG_FONT, BRASS_LIGHT,
        (WIDTH // 2, 285),
    )

    for index, line in enumerate(lines):
        draw_text(
            line, SMALL_FONT, MUTED,
            (WIDTH // 2, 345 + index * 30),
        )


# --------------------------------------------------
# MAIN GAME LOOP
# --------------------------------------------------

running = True

while running:
    dt = min(clock.tick(FPS) / 1000.0, 0.033)

    # Input handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            elif event.key == pygame.K_SPACE:
                if game_state == "gameover":
                    reset_game()
                else:
                    flap()

            elif event.key == pygame.K_e:
                activate_boost()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                if game_state == "gameover":
                    reset_game()
                else:
                    flap()

    # Update world
    if game_state == "playing":
        bird_velocity += GRAVITY * dt

        if boost_timer > 0:
            bird_velocity -= 850 * dt
            boost_timer = max(0.0, boost_timer - dt)

        bird_y += bird_velocity * dt

        ground_offset = (
            ground_offset + PIPE_SPEED * dt
        ) % WIDTH

        gear_rotation = (gear_rotation + 100 * dt) % 360

        pipe_timer += PIPE_SPEED * dt

        if pipe_timer >= PIPE_INTERVAL:
            pipes.append(create_pipe())
            pipe_timer -= PIPE_INTERVAL

        # Move pipes and reward successful passage
        for pipe in pipes:
            pipe["x"] -= PIPE_SPEED * dt

            if (
                not pipe["scored"]
                and pipe["x"] + PIPE_WIDTH < BIRD_X
            ):
                pipe["scored"] = True
                score += 1

                flight_energy = min(
                    MAX_ENERGY,
                    flight_energy + 25,
                )

        pipes = [
            pipe for pipe in pipes
            if pipe["x"] > -PIPE_WIDTH - 10
        ]

        # Bird collision box
        bird_rect = pygame.Rect(
            BIRD_X - BIRD_RADIUS,
            int(bird_y) - BIRD_RADIUS,
            BIRD_RADIUS * 2,
            BIRD_RADIUS * 2,
        )

        # Ceiling and ground collision
        if (
            bird_y - BIRD_RADIUS <= 0
            or bird_y + BIRD_RADIUS >= HEIGHT - GROUND_HEIGHT
        ):
            end_game()

        # Pipe collision
        for pipe in pipes:
            x = int(pipe["x"])
            gap_y = pipe["gap_y"]

            top = pygame.Rect(
                x, 0, PIPE_WIDTH,
                gap_y - PIPE_GAP // 2,
            )

            bottom = pygame.Rect(
                x,
                gap_y + PIPE_GAP // 2,
                PIPE_WIDTH,
                HEIGHT - GROUND_HEIGHT
                - (gap_y + PIPE_GAP // 2),
            )

            if (
                bird_rect.colliderect(top)
                or bird_rect.colliderect(bottom)
            ):
                end_game()
                break

    # --------------------------------------------------
    # RENDER FRAME
    # --------------------------------------------------

    screen.blit(background, (0, 0))

    for pipe in pipes:
        draw_pipe(pipe)

    draw_ground()
    draw_bird()

    # Score display
    score_panel = pygame.Rect(
        WIDTH // 2 - 34, 22, 68, 48
    )

    pygame.draw.rect(
        screen, PANEL, score_panel,
        border_radius=14,
    )

    pygame.draw.rect(
        screen, BRASS, score_panel, 2,
        border_radius=14,
    )

    draw_text(
        str(score), BIG_FONT, WHITE,
        (WIDTH // 2, 46),
    )

    draw_energy_meter()

    # Game state overlays
    if game_state == "ready":
        draw_overlay(
            "GEARWING",
            [
                "FLIGHT PROTOCOL",
                "SPACE / CLICK TO FLY",
                "PASS GEARS TO CHARGE YOUR CORE",
            ],
        )

    elif game_state == "gameover":
        draw_overlay(
            "FLIGHT FAILED",
            [
                f"FLIGHT SCORE: {score}",
                f"BEST SCORE: {best_score}",
                "SPACE / CLICK TO RETRY",
            ],
        )

    pygame.display.flip()

pygame.quit()
