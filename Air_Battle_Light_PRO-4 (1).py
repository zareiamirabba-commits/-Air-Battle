import pygame
import random
import math
import array

pygame.init()

# ---------------- SOUND ----------------
# Sounds are generated in code, so no extra MP3/WAV files are needed.
sound_enabled = False
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    sound_enabled = True
except Exception:
    sound_enabled = False

def make_tone(start_freq, end_freq, duration_ms, volume=0.25):
    if not sound_enabled:
        return None
    sample_rate = 22050
    count = max(1, int(sample_rate * duration_ms / 1000))
    samples = array.array("h")
    for i in range(count):
        t = i / sample_rate
        p = i / max(1, count - 1)
        freq = start_freq + (end_freq - start_freq) * p
        # Short fade in/out keeps Android speakers from clicking.
        fade = min(1.0, i / max(1, int(sample_rate * 0.008)))
        fade *= min(1.0, (count - i) / max(1, int(sample_rate * 0.012)))
        value = int(32767 * volume * fade * math.sin(2 * math.pi * freq * t))
        samples.append(value)
    try:
        return pygame.mixer.Sound(buffer=samples.tobytes())
    except Exception:
        return None

SND_FIRE = make_tone(900, 550, 70, 0.18)
SND_HIT = make_tone(180, 90, 120, 0.24)
SND_COIN = make_tone(700, 1200, 140, 0.22)
SND_DAMAGE = make_tone(160, 60, 180, 0.25)
SND_BUY = make_tone(500, 900, 120, 0.20)
SND_BOMB = make_tone(120, 40, 350, 0.35)
SND_MAGNET = make_tone(300, 900, 220, 0.22)
SND_ITEM = make_tone(800, 1400, 160, 0.20)

def play_sound(sound):
    if sound is not None:
        try:
            sound.play()
        except Exception:
            pass

# =========================================================
# AIR BATTLE
# Designed for Pydroid 3 / Android
# =========================================================

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Air Battle")
clock = pygame.time.Clock()

SAVE_FILE = "air_battle_save.txt"

# ---------------- COLORS ----------------
BG = (6, 9, 28)
WHITE = (245, 245, 245)
GRAY = (100, 100, 110)
RED = (235, 55, 55)
GREEN = (45, 220, 90)
BLUE = (60, 150, 255)
ORANGE = (255, 150, 40)
YELLOW = (255, 220, 50)
CYAN = (40, 225, 235)
PINK = (255, 70, 210)

# ---------------- FONTS ----------------
# English text is intentional: the normal Pygame font does not shape
# Persian/Arabic text correctly on many Android/Pydroid installations.
FONT_BIG = pygame.font.Font(None, max(54, WIDTH // 9))
FONT = pygame.font.Font(None, max(34, WIDTH // 18))
FONT_SMALL = pygame.font.Font(None, max(27, WIDTH // 25))

# =========================================================
# SAVE
# =========================================================
def load_coins():
    try:
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            return int(f.read().strip())
    except:
        return 0

def save_coins():
    try:
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            f.write(str(coins))
    except:
        pass

coins = load_coins()

# =========================================================
# UPGRADES
# =========================================================
player_speed = 7
max_hp = 2
bullet_level = 0

# Default = one bullet. The 10-shot burst is a paid upgrade.
SHOTS_PER_BURST = 1
TEN_SHOT_COST = 20
burst_unlocked = False

bullet_colors = [
    BLUE, RED, ORANGE, GREEN, PINK
]

bullet_names = [
    "BLUE", "RED", "ORANGE", "GREEN", "RAINBOW"
]

bullet_costs = [
    0, 10, 15, 20, 50
]

# =========================================================
# STAR BACKGROUND
# =========================================================
stars = []
for _ in range(45):
    stars.append([
        random.randint(0, WIDTH - 1),
        random.randint(0, HEIGHT - 1),
        random.randint(1, 3)
    ])

# =========================================================
# PLAYER
# =========================================================
PLAYER_W = max(48, WIDTH // 13)
PLAYER_H = max(60, HEIGHT // 17)

player = pygame.Rect(
    WIDTH // 2 - PLAYER_W // 2,
    HEIGHT - PLAYER_H - 35,
    PLAYER_W,
    PLAYER_H
)

# =========================================================
# TOUCH CONTROLS
# =========================================================
CONTROL = max(62, WIDTH // 10)
MARGIN = 18

left_btn = pygame.Rect(
    MARGIN,
    HEIGHT - CONTROL * 2 - MARGIN,
    CONTROL,
    CONTROL
)

right_btn = pygame.Rect(
    MARGIN + CONTROL * 2,
    HEIGHT - CONTROL * 2 - MARGIN,
    CONTROL,
    CONTROL
)

up_btn = pygame.Rect(
    MARGIN + CONTROL,
    HEIGHT - CONTROL * 3 - MARGIN,
    CONTROL,
    CONTROL
)

down_btn = pygame.Rect(
    MARGIN + CONTROL,
    HEIGHT - CONTROL - MARGIN,
    CONTROL,
    CONTROL
)

FIRE_W = max(125, WIDTH // 5)
FIRE_H = max(110, HEIGHT // 8)

fire_btn = pygame.Rect(
    WIDTH - FIRE_W - 22,
    HEIGHT - FIRE_H - 48,
    FIRE_W,
    FIRE_H
)

# =========================================================
# GAME STATE
# =========================================================
score = 0.0
hp = max_hp
level = 1

enemies = []
bullets = []
enemy_bullets = []
special_items = []
bomb_flash = 0
magnet_timer = 0

enemy_timer = 0
last_shot_time = 0
SHOT_DELAY = 160

# =========================================================
# BUTTON DRAW
# =========================================================
def draw_button(rect, text, color, size=None):
    pygame.draw.rect(screen, color, rect, border_radius=16)
    pygame.draw.rect(screen, WHITE, rect, 2, border_radius=16)

    use_font = FONT_SMALL if size is None else pygame.font.Font(None, size)
    image = use_font.render(text, True, WHITE)
    screen.blit(image, image.get_rect(center=rect.center))

# =========================================================
# LIGHTWEIGHT VISUAL POLISH
# =========================================================
def draw_light_glow(center, radius, color):
    # Small, cheap glow: only a few circles, no large surfaces.
    x, y = center
    pygame.draw.circle(screen, color, (x, y), radius, 2)
    if radius > 8:
        pygame.draw.circle(screen, color, (x, y), max(3, radius // 2), 1)

# =========================================================
# PLAYER DRAW
# =========================================================
def draw_player():
    x = player.centerx
    top = player.top
    bottom = player.bottom
    left = player.left
    right = player.right

    # Small engine flame (very cheap to render)
    flame_h = max(8, PLAYER_H // 7)
    pygame.draw.polygon(
        screen,
        ORANGE,
        [
            (x - 6, bottom - 2),
            (x + 6, bottom - 2),
            (x, bottom + flame_h)
        ]
    )

    pygame.draw.polygon(
        screen,
        CYAN,
        [
            (x, top),
            (right, bottom),
            (x, bottom - int(PLAYER_H * 0.28)),
            (left, bottom)
        ]
    )

    pygame.draw.polygon(
        screen,
        WHITE,
        [
            (x, top + 10),
            (x - 7, bottom - 16),
            (x + 7, bottom - 16)
        ]
    )

# =========================================================
# FIRE
# =========================================================
def fire():
    global last_shot_time

    now = pygame.time.get_ticks()

    if now - last_shot_time < SHOT_DELAY:
        return

    last_shot_time = now

    shot_count = 10 if burst_unlocked else 1
    play_sound(SND_FIRE)

    for i in range(shot_count):
        spread = (i - (shot_count - 1) / 2) * 3.2

        rect = pygame.Rect(
            player.centerx - 4,
            player.top - 20,
            8,
            20
        )

        bullets.append([rect, spread])

# =========================================================
# ENEMY
# =========================================================
def spawn_enemy():
    size = random.randint(38, 58)

    x = random.randint(
        10,
        max(10, WIDTH - size - 10)
    )

    speed = random.uniform(2.0, 3.4) + level * 0.20

    rect = pygame.Rect(
        x,
        -size,
        size,
        size
    )

    enemies.append([rect, speed])

def draw_enemy(rect):
    pygame.draw.polygon(
        screen,
        RED,
        [
            (rect.centerx, rect.bottom),
            (rect.left, rect.top),
            (rect.right, rect.top)
        ]
    )

    pygame.draw.rect(
        screen,
        ORANGE,
        (
            rect.centerx - 5,
            rect.top + 8,
            10,
            10
        )
    )

# =========================================================
# SPECIAL ITEMS
# =========================================================
def spawn_special_item(x, y):
    # Rare drops: BOMB or MAGNET
    if random.random() > 0.10:
        return
    kind = "BOMB" if random.random() < 0.5 else "MAGNET"
    rect = pygame.Rect(x - 18, y - 18, 36, 36)
    special_items.append([rect, kind, random.uniform(1.2, 2.0)])

def draw_special_item(rect, kind):
    if kind == "BOMB":
        pygame.draw.circle(screen, RED, rect.center, 17)
        pygame.draw.circle(screen, ORANGE, rect.center, 11)
        pygame.draw.line(screen, WHITE, (rect.centerx + 9, rect.top + 7),
                         (rect.right + 2, rect.top - 2), 4)
        label = FONT_SMALL.render("B", True, WHITE)
    else:
        pygame.draw.circle(screen, PINK, rect.center, 17, 4)
        pygame.draw.arc(screen, CYAN, rect.inflate(-10, -10), 0, math.pi, 4)
        label = FONT_SMALL.render("M", True, WHITE)
    screen.blit(label, label.get_rect(center=rect.center))

def use_bomb():
    global score, bomb_flash
    removed = len(enemies)
    if removed:
        score += removed * 2
        enemies.clear()
    enemy_bullets.clear()
    bomb_flash = 18
    play_sound(SND_BOMB)

# =========================================================
# SHOP
# =========================================================
def shop():
    global coins, player_speed, max_hp, bullet_level, burst_unlocked

    while True:
        screen.fill(BG)

        title = FONT_BIG.render("SHOP", True, CYAN)
        screen.blit(
            title,
            title.get_rect(center=(WIDTH // 2, 70))
        )

        coin_text = FONT.render(
            "COINS: " + str(coins),
            True,
            YELLOW
        )
        screen.blit(
            coin_text,
            coin_text.get_rect(center=(WIDTH // 2, 130))
        )

        hp_rect = pygame.Rect(
            WIDTH // 2 - 180,
            190,
            360,
            70
        )

        speed_rect = pygame.Rect(
            WIDTH // 2 - 180,
            280,
            360,
            70
        )

        draw_button(
            hp_rect,
            "HP +1   15 COINS",
            RED
        )

        draw_button(
            speed_rect,
            "SPEED +1   10 COINS",
            BLUE
        )

        # The 10-shot burst is a paid upgrade.
        free_rect = pygame.Rect(
            WIDTH // 2 - 180,
            370,
            360,
            70
        )

        burst_text = "10 SHOTS   OWNED" if burst_unlocked else "10 SHOTS   20 COINS"

        draw_button(
            free_rect,
            burst_text,
            GREEN
        )

        y = 460

        for i in range(1, 5):
            rect = pygame.Rect(
                WIDTH // 2 - 180,
                y,
                360,
                58
            )

            if bullet_level >= i:
                text = bullet_names[i] + "   OWNED"
            else:
                text = (
                    bullet_names[i]
                    + "   "
                    + str(bullet_costs[i])
                    + " COINS"
                )

            draw_button(
                rect,
                text,
                bullet_colors[i]
            )

            y += 68

        back_rect = pygame.Rect(
            WIDTH // 2 - 130,
            HEIGHT - 88,
            260,
            60
        )

        draw_button(
            back_rect,
            "BACK",
            GRAY
        )

        pygame.display.flip()

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                save_coins()
                pygame.quit()
                raise SystemExit

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    save_coins()
                    return

            if event.type == pygame.MOUSEBUTTONDOWN:
                pos = event.pos

                if hp_rect.collidepoint(pos):
                    if coins >= 15:
                        coins -= 15
                        max_hp += 1
                        save_coins()

                elif speed_rect.collidepoint(pos):
                    if coins >= 10:
                        coins -= 10
                        player_speed += 1
                        save_coins()

                elif free_rect.collidepoint(pos):
                    if not burst_unlocked and coins >= TEN_SHOT_COST:
                        coins -= TEN_SHOT_COST
                        burst_unlocked = True
                        save_coins()

                elif back_rect.collidepoint(pos):
                    save_coins()
                    return

                else:
                    for i in range(1, 5):
                        rect = pygame.Rect(
                            WIDTH // 2 - 180,
                            460 + (i - 1) * 68,
                            360,
                            58
                        )

                        if rect.collidepoint(pos):
                            if (
                                bullet_level < i
                                and coins >= bullet_costs[i]
                            ):
                                coins -= bullet_costs[i]
                                bullet_level = i
                                play_sound(SND_BUY)
                                save_coins()

# =========================================================
# START SCREEN
# =========================================================
def start_screen():
    while True:
        screen.fill(BG)

        for s in stars:
            pygame.draw.circle(
                screen,
                WHITE,
                (s[0], s[1]),
                s[2]
            )

        title = FONT_BIG.render(
            "AIR BATTLE",
            True,
            CYAN
        )
        screen.blit(
            title,
            title.get_rect(
                center=(WIDTH // 2, 125)
            )
        )

        coin_text = FONT.render(
            "COINS: " + str(coins),
            True,
            YELLOW
        )
        screen.blit(
            coin_text,
            coin_text.get_rect(
                center=(WIDTH // 2, 200)
            )
        )

        start_rect = pygame.Rect(
            WIDTH // 2 - 170,
            275,
            340,
            80
        )

        shop_rect = pygame.Rect(
            WIDTH // 2 - 170,
            385,
            340,
            80
        )

        exit_rect = pygame.Rect(
            WIDTH // 2 - 170,
            495,
            340,
            80
        )

        draw_button(
            start_rect,
            "START GAME",
            GREEN
        )

        draw_button(
            shop_rect,
            "SHOP",
            ORANGE
        )

        draw_button(
            exit_rect,
            "EXIT",
            RED
        )

        info = FONT_SMALL.render(
            "20 SCORE = 1 COIN",
            True,
            WHITE
        )

        screen.blit(
            info,
            info.get_rect(
                center=(WIDTH // 2, HEIGHT - 50)
            )
        )

        pygame.display.flip()

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                save_coins()
                pygame.quit()
                raise SystemExit

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    save_coins()
                    pygame.quit()
                    raise SystemExit

            if event.type == pygame.MOUSEBUTTONDOWN:

                if start_rect.collidepoint(event.pos):
                    return

                if shop_rect.collidepoint(event.pos):
                    shop()

                if exit_rect.collidepoint(event.pos):
                    save_coins()
                    pygame.quit()
                    raise SystemExit

# =========================================================
# GAME
# =========================================================
def play_game():
    global score, hp, level
    global enemy_timer, coins, bomb_flash, magnet_timer

    score = 0.0
    hp = max_hp
    level = 1

    enemies.clear()
    bullets.clear()
    enemy_bullets.clear()
    special_items.clear()
    bomb_flash = 0
    magnet_timer = 0

    player.centerx = WIDTH // 2
    player.bottom = HEIGHT - 45

    # Active touch/finger positions.
    # This is important for Android multitouch.
    fingers = {}

    enemy_timer = 0

    running = True

    while running:

        clock.tick(60)

        # ---------------------------------------------
        # Read controls every frame.
        # A finger stays active until FINGERUP.
        # ---------------------------------------------
        move_left = False
        move_right = False
        move_up = False
        move_down = False
        wants_fire = False

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                save_coins()
                pygame.quit()
                raise SystemExit

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

            # Mouse events are also used by Pydroid's touch layer.
            if event.type == pygame.MOUSEBUTTONDOWN:
                fingers["mouse"] = event.pos

                if fire_btn.collidepoint(event.pos):
                    wants_fire = True

            elif event.type == pygame.MOUSEMOTION:
                if "mouse" in fingers and event.buttons[0]:
                    fingers["mouse"] = event.pos

            elif event.type == pygame.MOUSEBUTTONUP:
                fingers.pop("mouse", None)

            # Real Android multitouch.
            elif event.type == pygame.FINGERDOWN:
                pos = (
                    int(event.x * WIDTH),
                    int(event.y * HEIGHT)
                )

                fingers[event.finger_id] = pos

                if fire_btn.collidepoint(pos):
                    wants_fire = True

            elif event.type == pygame.FINGERMOTION:
                fingers[event.finger_id] = (
                    int(event.x * WIDTH),
                    int(event.y * HEIGHT)
                )

            elif event.type == pygame.FINGERUP:
                fingers.pop(event.finger_id, None)

        # ---------------------------------------------
        # Convert active fingers into movement.
        # ---------------------------------------------
        for pos in fingers.values():

            if left_btn.collidepoint(pos):
                move_left = True

            if right_btn.collidepoint(pos):
                move_right = True

            if up_btn.collidepoint(pos):
                move_up = True

            if down_btn.collidepoint(pos):
                move_down = True

            if fire_btn.collidepoint(pos):
                wants_fire = True

        # Keyboard fallback.
        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move_left = True

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move_right = True

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            move_up = True

        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            move_down = True

        if keys[pygame.K_SPACE]:
            wants_fire = True

        # ---------------------------------------------
        # Movement
        # ---------------------------------------------
        if move_left:
            player.x -= player_speed

        if move_right:
            player.x += player_speed

        if move_up:
            player.y -= player_speed

        if move_down:
            player.y += player_speed

        # Keep player on screen.
        player.left = max(0, player.left)
        player.right = min(WIDTH, player.right)
        player.top = max(0, player.top)
        player.bottom = min(HEIGHT, player.bottom)

        # ---------------------------------------------
        # Shooting
        # ---------------------------------------------
        if wants_fire:
            fire()

        # ---------------------------------------------
        # Spawn enemies
        # ---------------------------------------------
        enemy_timer += clock.get_time()

        spawn_delay = max(
            300,
            900 - level * 35
        )

        if enemy_timer >= spawn_delay:
            enemy_timer = 0
            spawn_enemy()

        # ---------------------------------------------
        # Move player bullets
        # ---------------------------------------------
        for bullet in bullets[:]:

            rect, spread = bullet

            rect.y -= 14
            rect.x += int(spread * 0.30)

            if rect.bottom < 0:
                bullets.remove(bullet)

        # ---------------------------------------------
        # Move enemies
        # ---------------------------------------------
        for enemy in enemies[:]:

            rect, speed = enemy

            rect.y += speed

            # Enemy passed player.
            if rect.top > HEIGHT:
                enemies.remove(enemy)
                score += 0.5
                continue

            # Weak enemy bullets.
            if random.random() < 0.002:
                eb = pygame.Rect(
                    rect.centerx - 4,
                    rect.bottom,
                    8,
                    18
                )
                enemy_bullets.append(
                    [eb, 4.0 + level * 0.10]
                )

        # ---------------------------------------------
        # Move enemy bullets
        # ---------------------------------------------
        for eb in enemy_bullets[:]:

            rect, speed = eb

            rect.y += speed

            if rect.top > HEIGHT:
                enemy_bullets.remove(eb)

        # ---------------------------------------------
        # Bullet vs enemy
        # ---------------------------------------------
        for bullet in bullets[:]:

            rect, spread = bullet
            hit_enemy = None

            for enemy in enemies:
                enemy_rect, enemy_speed = enemy

                if rect.colliderect(enemy_rect):
                    hit_enemy = enemy
                    break

            if hit_enemy is not None:

                if bullet in bullets:
                    bullets.remove(bullet)

                if hit_enemy in enemies:
                    enemies.remove(hit_enemy)
                    spawn_special_item(hit_enemy[0].centerx, hit_enemy[0].centery)

                score += 2
                play_sound(SND_HIT)

        # ---------------------------------------------
        # Special items
        # ---------------------------------------------
        for item in special_items[:]:
            rect, kind, speed = item
            rect.y += speed

            # Magnet pulls special items toward the player.
            if magnet_timer > 0:
                dx = player.centerx - rect.centerx
                dy = player.centery - rect.centery
                dist = max(1, math.hypot(dx, dy))
                rect.x += int(dx / dist * 7)
                rect.y += int(dy / dist * 7)

            if rect.colliderect(player):
                if kind == "BOMB":
                    use_bomb()
                else:
                    magnet_timer = 8 * 60
                    play_sound(SND_MAGNET)
                special_items.remove(item)
                play_sound(SND_ITEM)
                continue

            if rect.top > HEIGHT + 30:
                special_items.remove(item)

        if magnet_timer > 0:
            magnet_timer -= 1

        # ---------------------------------------------
        # Enemy vs player
        # ---------------------------------------------
        for enemy in enemies[:]:

            rect, speed = enemy

            if rect.colliderect(player):

                if enemy in enemies:
                    enemies.remove(enemy)

                hp -= 1

        # ---------------------------------------------
        # Enemy bullet vs player
        # ---------------------------------------------
        for eb in enemy_bullets[:]:

            rect, speed = eb

            if rect.colliderect(player):

                if eb in enemy_bullets:
                    enemy_bullets.remove(eb)

                hp -= 1
                play_sound(SND_DAMAGE)

        # ---------------------------------------------
        # Level
        # ---------------------------------------------
        level = int(score // 20) + 1

        # ---------------------------------------------
        # Game over
        # ---------------------------------------------
        if hp <= 0 or score >= 200:

            if score > 200:
                score = 200

            earned_coins = int(score // 20)
            coins += earned_coins
            save_coins()

            running = False

        # ---------------------------------------------
        # DRAW
        # ---------------------------------------------
        screen.fill(BG)

        # Stars
        for s in stars:

            s[1] += s[2]

            if s[1] >= HEIGHT:
                s[1] = 0
                s[0] = random.randint(0, WIDTH - 1)

            pygame.draw.circle(
                screen,
                WHITE,
                (s[0], s[1]),
                s[2]
            )

        # Enemies
        for enemy in enemies:
            draw_enemy(enemy[0])

        # Bullets
        for bullet in bullets:

            rect, spread = bullet

            if bullet_level == 4:
                pygame.draw.rect(
                    screen,
                    RED,
                    rect
                )
                pygame.draw.rect(
                    screen,
                    YELLOW,
                    (
                        rect.x,
                        rect.y + 5,
                        rect.width,
                        5
                    )
                )
                pygame.draw.rect(
                    screen,
                    GREEN,
                    (
                        rect.x,
                        rect.y + 10,
                        rect.width,
                        5
                    )
                )
            else:
                pygame.draw.rect(
                    screen,
                    bullet_colors[bullet_level],
                    rect
                )

        # Enemy bullets
        for eb in enemy_bullets:
            pygame.draw.rect(
                screen,
                RED,
                eb[0]
            )

        # Special items
        for item in special_items:
            draw_special_item(item[0], item[1])

        # Magnet indicator
        if magnet_timer > 0:
            pygame.draw.circle(screen, PINK, player.center, 48, 3)
            magnet_text = FONT_SMALL.render("MAGNET", True, PINK)
            screen.blit(magnet_text, (player.centerx - magnet_text.get_width() // 2, player.top - 35))

        # Bomb flash
        if bomb_flash > 0:
            radius = 30 + (18 - bomb_flash) * 20
            pygame.draw.circle(screen, ORANGE, player.center, radius, 8)
            bomb_flash -= 1

        # Player
        draw_player()

        # Top HUD
        hud1 = FONT_SMALL.render(
            "SCORE: " + str(int(score)),
            True,
            WHITE
        )

        hud2 = FONT_SMALL.render(
            "LEVEL: " + str(level),
            True,
            WHITE
        )

        hud3 = FONT_SMALL.render(
            "HP: " + str(hp) + "/" + str(max_hp),
            True,
            GREEN
        )

        hud4 = FONT_SMALL.render(
            "COINS: " + str(coins),
            True,
            YELLOW
        )

        screen.blit(hud1, (15, 15))
        screen.blit(hud2, (15, 48))
        screen.blit(hud3, (15, 81))
        screen.blit(hud4, (15, 114))

        item_hint = FONT_SMALL.render("BOMB: B   MAGNET: M", True, WHITE)
        screen.blit(item_hint, (15, 147))

        # Movement controls
        draw_button(left_btn, "<", GRAY)
        draw_button(right_btn, ">", GRAY)
        draw_button(up_btn, "^", GRAY)
        draw_button(down_btn, "v", GRAY)

        # Fire button
        draw_button(fire_btn, "FIRE", RED)

        pygame.display.flip()

# =========================================================
# MAIN LOOP
# =========================================================
while True:
    start_screen()
    play_game()
