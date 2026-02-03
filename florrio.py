import pygame
import math
import time
import random
import json
import os
import hashlib

pygame.init()

# --- FULLSCREEN SETUP ---
screen_info = pygame.display.Info()
WIDTH, HEIGHT = screen_info.current_w, screen_info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("FLORio")
clock = pygame.time.Clock()

# --- FONTS ---
font_sm = pygame.font.SysFont("Arial", 11, bold=True)
font_md = pygame.font.SysFont("Arial", 18, bold=True)
font_lg = pygame.font.SysFont("Arial", 48, bold=True)
font_xl = pygame.font.SysFont("Arial", 120, bold=True)

# --- CONSTANTS ---
MAP_GREEN, GRID_COLOR = (34, 139, 34), (30, 120, 30)
MAP_GREY, GRID_GREY = (211, 211, 211), (180, 180, 180)
PLAYER_COLOR = (255, 220, 100)
BASIC_COLOR, LIGHT_COLOR, GLASS_COLOR = (0, 200, 255), (255, 255, 200), (230, 245, 255)
STINGER_COLOR, LEAF_COLOR, ROCK_COLOR = (255, 140, 0), (50, 255, 50), (120, 120, 120)
BEE_YELLOW, BEE_STRIPE = (255, 215, 0), (40, 40, 40)
ANT_COLOR, SPIDER_COLOR = (80, 80, 80), (40, 0, 80)
COOLDOWN_OVERLAY = (50, 50, 50, 180)

WORLD_SIZE = 3500
RADAR_RANGE = 2000
BEE_COUNT, ANT_COUNT, SPIDER_COUNT = 30, 20, 10
BEE_RESPAWN_TIME, ANT_RESPAWN_TIME, SPIDER_RESPAWN_TIME = 15.0, 20.0, 15.0
MISSILE_RANGE = 600

PORTAL_TO_WORLD2 = [WORLD_SIZE - 200, 0]
PORTAL_TO_WORLD1 = [-WORLD_SIZE + 200, 0]

STATE_MENU, STATE_GAME, STATE_INVENTORY, STATE_DEAD, STATE_BUFFS, STATE_UPGRADE, STATE_ACCOUNT_CREATE, STATE_ACCOUNT_LOGIN = range(8)

SAVE_VERSION = 1
ACCOUNTS_FILE = "accounts.json"

def clamp(v, mn, mx):
    return max(mn, min(mx, v))

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def now():
    return time.time()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# -----------------------------
# ENTITIES
# -----------------------------
class Entity:
    def __init__(self, x, y, radius, max_health, aggro_range=0):
        self.pos = [x, y]
        self.radius = radius
        self.max_health = max_health
        self.health = max_health
        self.last_hit_time = 0
        self.death_time = 0
        self.dropped_loot = False
        self.aggro_range = aggro_range
        self.angle = random.uniform(0, math.pi * 2)

    def take_damage(self, amount):
        self.health -= amount
        self.last_hit_time = now()
        if self.health <= 0:
            self.death_time = now()

    def is_alive(self):
        return self.health > 0

    def respawn(self, rng):
        self.health = self.max_health
        self.dropped_loot = False
        self.death_time = 0
        self.pos = [random.randint(-rng, rng), random.randint(-rng, rng)]

    def draw_healthbar(self, surface, sx, sy):
        pygame.draw.rect(surface, (50, 0, 0), (sx - self.radius, sy - self.radius - 15, self.radius * 2, 6))
        pygame.draw.rect(surface, (255, 50, 50),
                         (sx - self.radius, sy - self.radius - 15,
                          int((max(0, self.health) / self.max_health) * (self.radius * 2)), 6))

    def draw_name(self, surface, sx, sy, name):
        name_txt = font_sm.render(name, True, (255, 255, 255))
        surface.blit(name_txt, (sx - name_txt.get_width() // 2, sy - self.radius - 35))

class SpiderMob(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 20, 250, aggro_range=700)

    def update(self, player_pos):
        if not self.is_alive():
            return
        dx, dy = player_pos[0] - self.pos[0], player_pos[1] - self.pos[1]
        dist_p = math.hypot(dx, dy)
        if dist_p < self.aggro_range and dist_p > 0:
            speed = 3.6
            self.angle = math.atan2(dy, dx)
            self.pos[0] += (dx / dist_p) * speed
            self.pos[1] += (dy / dist_p) * speed
        self.pos[0] = clamp(self.pos[0], -WORLD_SIZE, WORLD_SIZE)
        self.pos[1] = clamp(self.pos[1], -WORLD_SIZE, WORLD_SIZE)

    def draw(self, surface, cam_x, cam_y):
        if not self.is_alive():
            return
        sx, sy = int(self.pos[0] - cam_x), int(self.pos[1] - cam_y)
        is_f = (now() - self.last_hit_time) < 0.1
        main_c = (255, 150, 150) if is_f else SPIDER_COLOR
        for i in range(8):
            a = self.angle + (i * (math.pi / 4))
            pygame.draw.line(surface, (20, 20, 20), (sx, sy), (sx + math.cos(a) * 35, sy + math.sin(a) * 35), 3)
        pygame.draw.circle(surface, main_c, (sx, sy), self.radius)
        pygame.draw.circle(surface, (0, 0, 0), (sx, sy), self.radius, 2)
        self.draw_name(surface, sx, sy, "Spider")
        self.draw_healthbar(surface, sx, sy)

class AntMob(Entity):
    def __init__(self, x, y):
        super().__init__(x, y, 22, 400, aggro_range=600)

    def update(self, player_pos):
        if not self.is_alive():
            return
        dx, dy = player_pos[0] - self.pos[0], player_pos[1] - self.pos[1]
        dist_p = math.hypot(dx, dy)
        if dist_p < self.aggro_range and dist_p > 0:
            speed = 2.4
            self.angle = math.atan2(dy, dx)
            self.pos[0] += (dx / dist_p) * speed
            self.pos[1] += (dy / dist_p) * speed
        self.pos[0] = clamp(self.pos[0], -WORLD_SIZE, WORLD_SIZE)
        self.pos[1] = clamp(self.pos[1], -WORLD_SIZE, WORLD_SIZE)

    def draw(self, surface, cam_x, cam_y):
        if not self.is_alive():
            return
        sx, sy = int(self.pos[0] - cam_x), int(self.pos[1] - cam_y)
        is_f = (now() - self.last_hit_time) < 0.1
        main_c = (255, 150, 150) if is_f else ANT_COLOR
        for i in range(3, 0, -1):
            seg_x = sx - math.cos(self.angle) * (i * 18)
            seg_y = sy - math.sin(self.angle) * (i * 18)
            pygame.draw.circle(surface, main_c, (int(seg_x), int(seg_y)), self.radius - (i * 2))
            pygame.draw.circle(surface, (0, 0, 0), (int(seg_x), int(seg_y)), self.radius - (i * 2), 2)
        pygame.draw.circle(surface, main_c, (sx, sy), self.radius)
        pygame.draw.circle(surface, (0, 0, 0), (sx, sy), self.radius, 2)
        self.draw_name(surface, sx, sy, "Ant")
        self.draw_healthbar(surface, sx, sy)

class BeeMob(Entity):
    def __init__(self, x, y, is_queen=False):
        radius = 75 if is_queen else 25
        max_health = 500 if is_queen else 100
        super().__init__(x, y, radius, max_health)
        self.is_queen = is_queen
        self.is_aggressive = False
        self.last_missile_time = 0

    def take_damage(self, amount):
        super().take_damage(amount)
        self.is_aggressive = True

    def update(self, player_pos):
        if not self.is_alive():
            return
        speed = 3.2 if self.is_queen else 1.6
        if self.is_aggressive:
            dx, dy = player_pos[0] - self.pos[0], player_pos[1] - self.pos[1]
            dist_p = math.hypot(dx, dy)
            if dist_p > 0:
                self.pos[0] += (dx / dist_p) * speed
                self.pos[1] += (dy / dist_p) * speed
        self.pos[0] = clamp(self.pos[0], -WORLD_SIZE, WORLD_SIZE)
        self.pos[1] = clamp(self.pos[1], -WORLD_SIZE, WORLD_SIZE)

    def draw(self, surface, cam_x, cam_y):
        if not self.is_alive():
            return
        sx, sy = int(self.pos[0] - cam_x), int(self.pos[1] - cam_y)
        is_f = (now() - self.last_hit_time) < 0.1
        pygame.draw.circle(surface, (255, 150, 150) if is_f else BEE_YELLOW, (sx, sy), self.radius)
        pygame.draw.rect(surface, BEE_STRIPE, (sx - self.radius * 0.4, sy - self.radius * 0.7, self.radius * 0.25, self.radius * 1.4))
        pygame.draw.rect(surface, BEE_STRIPE, (sx + self.radius * 0.1, sy - self.radius * 0.7, self.radius * 0.25, self.radius * 1.4))
        if self.is_queen:
            pygame.draw.polygon(surface, (255, 215, 0), [(sx - 20, sy - self.radius), (sx - 10, sy - self.radius - 20),
                                                         (sx, sy - self.radius), (sx + 10, sy - self.radius - 20),
                                                         (sx + 20, sy - self.radius)])
        pygame.draw.circle(surface, (0, 0, 0), (sx, sy), self.radius, 2)
        self.draw_name(surface, sx, sy, "Queen Bee" if self.is_queen else "Bee")
        self.draw_healthbar(surface, sx, sy)

class Petal:
    def __init__(self, name, color, damage=20, shape="circle", cooldown=3.0):
        self.name = name
        self.color = color
        self.damage = damage
        self.shape = shape
        self.cooldown_time = cooldown
        self.last_hit_time = 0
        self.is_active = True
        self.hits_left = 2 if "Rock" in name else 1

    def update(self):
        if not self.is_active and now() - self.last_hit_time >= self.cooldown_time:
            self.is_active = True
            self.hits_left = 2 if "Rock" in self.name else 1

    def trigger_cooldown(self):
        self.hits_left -= 1
        if self.hits_left <= 0:
            self.is_active = False
            self.last_hit_time = now()

    def to_dict(self):
        return {"name": self.name, "color": self.color, "damage": self.damage, "shape": self.shape, "cooldown": self.cooldown_time}

class DroppedPetal:
    def __init__(self, x, y, petal_type):
        self.pos = [x, y]
        self.type = petal_type
        self.radius = 10

        if petal_type == "Basic":
            self.color, self.shape, self.dmg, self.cd = BASIC_COLOR, "circle", 20, 3.0
        elif petal_type == "Light":
            self.color, self.shape, self.dmg, self.cd = LIGHT_COLOR, "circle", 20, 1.5
        elif petal_type == "Glass":
            self.color, self.shape, self.dmg, self.cd = GLASS_COLOR, "square", 40, 3.0
        elif petal_type == "Stinger":
            self.color, self.shape, self.dmg, self.cd = STINGER_COLOR, "circle", 80, 6.0
        elif petal_type == "Leaf":
            self.color, self.shape, self.dmg, self.cd = LEAF_COLOR, "circle", 80, 3.0
        elif petal_type == "Rock":
            self.color, self.shape, self.dmg, self.cd = ROCK_COLOR, "square", 80, 3.0

    def draw(self, surface, cam_x, cam_y):
        sx, sy = int(self.pos[0] - cam_x), int(self.pos[1] - cam_y)
        if self.shape == "square":
            pygame.draw.rect(surface, self.color, (sx - 10, sy - 10, 20, 20))
            pygame.draw.rect(surface, (255, 255, 255), (sx - 10, sy - 10, 20, 20), 2)
        else:
            pygame.draw.circle(surface, self.color, (sx, sy), self.radius)
            pygame.draw.circle(surface, (255, 255, 255), (sx, sy), self.radius, 2)

        label = font_sm.render(self.type, True, (255, 255, 255))
        surface.blit(label, (sx - label.get_width() // 2, sy + 15))

class Missile:
    def __init__(self, x, y, target_pos):
        self.pos = [x, y]
        self.target = target_pos
        self.speed = 8
        self.radius = 8
        dx, dy = target_pos[0] - x, target_pos[1] - y
        d = math.hypot(dx, dy) or 1
        self.dir = [dx / d, dy / d]

    def update(self):
        self.pos[0] += self.dir[0] * self.speed
        self.pos[1] += self.dir[1] * self.speed

    def draw(self, surface, cam_x, cam_y):
        sx, sy = int(self.pos[0] - cam_x), int(self.pos[1] - cam_y)
        pygame.draw.circle(surface, (255, 0, 0), (sx, sy), self.radius)
        pygame.draw.circle(surface, (0, 0, 0), (sx, sy), self.radius, 2)

# -----------------------------
# GAME
# -----------------------------
class Game:
    def __init__(self):
        self.current_state = STATE_MENU
        self.current_world = 0

        # Player
        self.player_w_pos = [0, 0]
        self.p_health = 100
        self.p_max_health = 100
        self.p_hit_time = 0
        self.p_poison_until = 0
        self.p_poison_tick_dmg = 0
        self.p_last_poison_tick = 0
        self.p_last_attack_time = 0
        self.p_last_regen_time = 0
        self.player_radius = 25

        # Progression
        self.p_lvl, self.p_xp, self.p_lvl_points = 1, 0, 0
        self.p_rotation_speed = 0.04
        self.p_petal_range = 85
        self.p_queen_killed = False

        # Inventory
        self.hotbar = [Petal("Basic", BASIC_COLOR) for _ in range(5)]
        self.stored_petals = []

        # Entities
        self.dropped_items = []
        self.bees = []
        self.ants = []
        self.spiders = []
        self.queen_bee = None
        self.missiles = []
        self.orbit_angle = 0
        self.selected_for_swap_idx = None

        # UI
        self.quit_btn_rect = pygame.Rect(20, 20, 100, 40)
        self.inv_btn_rect = pygame.Rect(20, HEIGHT - 110, 100, 30)
        self.buffs_btn_rect = pygame.Rect(20, HEIGHT - 150, 100, 30)
        self.upgrade_btn_rect = pygame.Rect(20, HEIGHT - 190, 100, 30)
        self.respawn_btn_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 20, 200, 60)

        # MENU - aligned to far right
        margin = 40
        btn_w, btn_h = 300, 80
        right_x = WIDTH - btn_w - margin

        self.menu_play_rect = pygame.Rect(right_x, HEIGHT // 2 - 50, btn_w, btn_h)
        self.menu_quit_rect = pygame.Rect(right_x, HEIGHT // 2 + 70, btn_w, btn_h)
        self.menu_create_rect = pygame.Rect(right_x, HEIGHT // 2 - 150, btn_w, 60)
        self.menu_login_rect = pygame.Rect(right_x, HEIGHT // 2 - 230, btn_w, 60)

        self.click_cooldown = 0.15
        self.last_click_time = 0

        # Account fields
        self.accounts = {}
        self.current_account = None
        self.account_username = ""
        self.account_password = ""
        self.account_message = ""
        self.account_focus = "username"

        self.load_accounts()
        self.reset_game()

    # --------------------
    # Accounts
    # --------------------
    def load_accounts(self):
        if os.path.exists(ACCOUNTS_FILE):
            with open(ACCOUNTS_FILE, "r") as f:
                self.accounts = json.load(f)

    def save_accounts(self):
        with open(ACCOUNTS_FILE, "w") as f:
            json.dump(self.accounts, f)

    def create_account(self, username, password):
        if username in self.accounts:
            return False, "Username already exists."
        if len(username) < 3 or len(password) < 3:
            return False, "Username and password must be at least 3 characters."
        self.accounts[username] = {
            "password": hash_password(password),
            "data": self.game_state_dict()
        }
        self.save_accounts()
        return True, "Account created successfully."

    def login(self, username, password):
        if username not in self.accounts:
            return False, "Account does not exist."
        if self.accounts[username]["password"] != hash_password(password):
            return False, "Incorrect password."
        self.current_account = username
        self.load_game_data(self.accounts[username]["data"])
        return True, "Logged in successfully."

    def save_to_account(self):
        if not self.current_account:
            return False
        self.accounts[self.current_account]["data"] = self.game_state_dict()
        self.save_accounts()
        return True

    # --------------------
    # Save / Load
    # --------------------
    def game_state_dict(self):
        return {
            "version": SAVE_VERSION,
            "level": self.p_lvl,
            "xp": self.p_xp,
            "points": self.p_lvl_points,
            "rotation": self.p_rotation_speed,
            "range": self.p_petal_range,
            "queen_killed": self.p_queen_killed,
            "hotbar": [p.to_dict() for p in self.hotbar],
            "inventory": [[entry[0].to_dict(), entry[1]] for entry in self.stored_petals],
            "player": {
                "health": self.p_health,
                "max_health": self.p_max_health,
                "pos": self.player_w_pos
            }
        }

    def load_game_data(self, data):
        if data.get("version", 0) != SAVE_VERSION:
            return False

        self.p_lvl = data["level"]
        self.p_xp = data["xp"]
        self.p_lvl_points = data["points"]
        self.p_rotation_speed = data["rotation"]
        self.p_petal_range = data["range"]
        self.p_queen_killed = data["queen_killed"]
        self.hotbar = [Petal(d["name"], d["color"], d["damage"], d["shape"], d["cooldown"]) for d in data["hotbar"]]
        self.stored_petals = [
            [Petal(e[0]["name"], e[0]["color"], e[0]["damage"], e[0]["shape"], e[0]["cooldown"]), e[1]]
            for e in data["inventory"]
        ]
        self.p_health = data["player"]["health"]
        self.p_max_health = data["player"]["max_health"]
        self.player_w_pos = data["player"]["pos"]
        return True

    # --------------------
    # Game Logic
    # --------------------
    def reset_game(self):
        self.p_health, self.p_max_health = 100, 100
        self.player_w_pos = [0, 0]
        self.orbit_angle = 0
        self.p_last_attack_time = 0
        self.p_last_regen_time = 0
        self.p_poison_until = 0
        self.current_world = 0
        self.dropped_items = []
        self.missiles = []
        self.queen_bee = BeeMob(random.randint(-WORLD_SIZE + 500, WORLD_SIZE - 500),
                                 random.randint(-WORLD_SIZE + 500, WORLD_SIZE - 500), is_queen=True)
        self.bees = [BeeMob(random.randint(-WORLD_SIZE + 100, WORLD_SIZE - 100),
                            random.randint(-WORLD_SIZE + 100, WORLD_SIZE - 100)) for _ in range(BEE_COUNT)]
        self.ants = [AntMob(random.randint(-WORLD_SIZE + 100, WORLD_SIZE - 100),
                            random.randint(-WORLD_SIZE + 100, WORLD_SIZE - 100)) for _ in range(ANT_COUNT)]
        self.spiders = [SpiderMob(random.randint(-WORLD_SIZE + 100, WORLD_SIZE - 100),
                                  random.randint(-WORLD_SIZE + 100, WORLD_SIZE - 100)) for _ in range(SPIDER_COUNT)]
        self.current_state = STATE_MENU

    def add_xp(self, amount):
        self.p_xp += amount
        req = 100 + (self.p_lvl - 1) * 50
        if self.p_xp >= req:
            self.p_xp -= req
            self.p_lvl += 1
            self.p_lvl_points += 1
            self.p_max_health += 25
            self.p_health = self.p_max_health

    def add_to_inventory(self, name, color, dmg, shape, cd):
        for entry in self.stored_petals:
            if entry[0].name == name:
                entry[1] += 1
                return
        self.stored_petals.append([Petal(name, color, dmg, shape, cd), 1])

    # --------------------
    # GAME UPDATE
    # --------------------
    def player_enemy_collision(self, player_pos, player_radius, enemy, knockback_strength):
        d = dist(player_pos, enemy.pos)
        if d < player_radius + enemy.radius:
            overlap = (player_radius + enemy.radius) - d
            dx, dy = player_pos[0] - enemy.pos[0], player_pos[1] - enemy.pos[1]
            if d == 0:
                dx, dy = random.uniform(-1, 1), random.uniform(-1, 1)
                d = math.hypot(dx, dy) or 1
            nx, ny = dx / d, dy / d

            player_pos[0] += nx * overlap
            player_pos[1] += ny * overlap
            player_pos[0] += nx * knockback_strength
            player_pos[1] += ny * knockback_strength

            self.p_health -= 20
            self.p_hit_time = now()

    def update_game(self, mx, my, clicked):
        if self.p_health <= 0:
            self.current_state = STATE_DEAD
            return

        if now() < self.p_poison_until and now() - self.p_last_poison_tick >= 1.0:
            self.p_health -= self.p_poison_tick_dmg
            self.p_last_poison_tick = now()
            self.p_hit_time = now()

        if now() - self.p_last_attack_time > 2.0 and now() - self.p_last_regen_time > 2.0:
            self.p_health = min(self.p_max_health, self.p_health + 2)
            self.p_last_regen_time = now()

        cam_x, cam_y = self.player_w_pos[0] - WIDTH // 2, self.player_w_pos[1] - HEIGHT // 2
        self.player_w_pos[0] += (mx + cam_x - self.player_w_pos[0]) * 0.025
        self.player_w_pos[1] += (my + cam_y - self.player_w_pos[1]) * 0.025
        self.player_w_pos[0] = clamp(self.player_w_pos[0], -WORLD_SIZE, WORLD_SIZE)
        self.player_w_pos[1] = clamp(self.player_w_pos[1], -WORLD_SIZE, WORLD_SIZE)

        # WORLD LOGIC (unchanged)
        if self.current_world == 0:
            self.queen_bee.update(self.player_w_pos)

            if self.queen_bee.is_alive():
                dq = dist(self.player_w_pos, self.queen_bee.pos)
                if dq < MISSILE_RANGE and now() - self.queen_bee.last_missile_time > 2.0:
                    self.queen_bee.last_missile_time = now()
                    self.missiles.append(Missile(self.queen_bee.pos[0], self.queen_bee.pos[1], self.player_w_pos[:]))

                if dq < 100:
                    self.player_enemy_collision(self.player_w_pos, self.player_radius, self.queen_bee, 60)

            for b in self.bees:
                if b.is_alive():
                    b.update(self.player_w_pos)
                    self.player_enemy_collision(self.player_w_pos, self.player_radius, b, 45)
                elif now() - b.death_time >= BEE_RESPAWN_TIME:
                    b.respawn(WORLD_SIZE - 200)

            if dist(self.player_w_pos, PORTAL_TO_WORLD2) < 100:
                if self.p_lvl >= 8 and self.p_queen_killed:
                    self.current_world = 1
                    self.player_w_pos = [-WORLD_SIZE + 400, 0]
                    self.dropped_items = []

        else:
            for a in self.ants:
                if a.is_alive():
                    a.update(self.player_w_pos)
                    self.player_enemy_collision(self.player_w_pos, self.player_radius, a, 55)
                elif now() - a.death_time >= ANT_RESPAWN_TIME:
                    a.respawn(WORLD_SIZE - 200)

            for s in self.spiders:
                if s.is_alive():
                    s.update(self.player_w_pos)
                    self.player_enemy_collision(self.player_w_pos, self.player_radius, s, 50)
                    if dist(self.player_w_pos, s.pos) < 40 and now() - self.p_hit_time > 0.3:
                        self.p_poison_until = now() + 2.0
                        self.p_poison_tick_dmg = 10
                        self.p_last_poison_tick = now()
                elif now() - s.death_time >= SPIDER_RESPAWN_TIME:
                    s.respawn(WORLD_SIZE - 200)

            if dist(self.player_w_pos, PORTAL_TO_WORLD1) < 100:
                self.current_world = 0
                self.player_w_pos = [WORLD_SIZE - 400, 0]
                self.dropped_items = []

        for d in self.dropped_items[:]:
            if dist(self.player_w_pos, d.pos) < 35:
                self.add_to_inventory(d.type, d.color, d.dmg, d.shape, d.cd)
                self.dropped_items.remove(d)

        self.orbit_angle += self.p_rotation_speed
        for i, p in enumerate(self.hotbar):
            p.update()
            if not p.is_active:
                continue
            n = len(self.hotbar)
            px_w = self.player_w_pos[0] + self.p_petal_range * math.cos(self.orbit_angle + (2 * math.pi / n) * i)
            py_w = self.player_w_pos[1] + self.p_petal_range * math.sin(self.orbit_angle + (2 * math.pi / n) * i)

            targets = (self.bees + [self.queen_bee]) if self.current_world == 0 else (self.ants + self.spiders)
            for t in targets:
                if not t.is_alive():
                    continue
                if dist([px_w, py_w], t.pos) < (t.radius + 15):
                    t.take_damage(p.damage)
                    dx, dy = self.player_w_pos[0] - t.pos[0], self.player_w_pos[1] - t.pos[1]
                    d = math.hypot(dx, dy)
                    self.player_w_pos[0] += (dx / max(1, d)) * 15
                    self.player_w_pos[1] += (dy / max(1, d)) * 15

                    if p.name == "Leaf":
                        self.p_health = min(self.p_max_health, self.p_health + 10)

                    if t.health <= 0 and not t.dropped_loot:
                        if isinstance(t, BeeMob) and getattr(t, "is_queen", False):
                            self.p_queen_killed = True
                            self.add_xp(250)
                            self.dropped_items.append(DroppedPetal(t.pos[0] - 30, t.pos[1], "Glass"))
                            self.dropped_items.append(DroppedPetal(t.pos[0] + 30, t.pos[1], "Stinger"))
                        elif isinstance(t, SpiderMob):
                            self.add_xp(80)
                            roll = random.random()
                            self.dropped_items.append(DroppedPetal(t.pos[0], t.pos[1], "Stinger"))
                            self.dropped_items.append(DroppedPetal(t.pos[0] + 25, t.pos[1], "Leaf" if roll < 0.25 else "Rock"))
                        else:
                            self.add_xp(25)
                            roll = random.random()
                            loot = "Glass" if roll < 0.09 else ("Basic" if roll < 0.54 else "Light")
                            self.dropped_items.append(DroppedPetal(t.pos[0], t.pos[1], loot))
                        t.dropped_loot = True

                    p.trigger_cooldown()
                    self.p_last_attack_time = now()
                    break

        for m in self.missiles[:]:
            m.update()
            if dist(m.pos, self.player_w_pos) < self.player_radius + m.radius:
                self.p_health -= 35
                self.p_hit_time = now()
                self.missiles.remove(m)
            elif dist(m.pos, self.queen_bee.pos) > MISSILE_RANGE * 2:
                self.missiles.remove(m)

    # --------------------
    # Rendering
    # --------------------
    def draw_player_hud(self, surface, mx, my, player_w_pos, health, max_health):
        # Health Bar
        bar_w, bar_h = 300, 25
        x, y = 20, 20
        pygame.draw.rect(surface, (40, 40, 40), (x, y, bar_w, bar_h), border_radius=8)
        pygame.draw.rect(surface, (255, 50, 50), (x + 4, y + 4, int((health / max_health) * (bar_w - 8)), bar_h - 8), border_radius=6)

        # Player Icon
        pygame.draw.circle(surface, PLAYER_COLOR, (x + 20, y + 12), 10)
        pygame.draw.circle(surface, (0, 0, 0), (x + 20, y + 12), 10, 2)

        # World Position
        pos_txt = font_sm.render(f"X: {int(player_w_pos[0])}  Y: {int(player_w_pos[1])}", True, (255, 255, 255))
        surface.blit(pos_txt, (x, y + 40))

    def draw_minimap(self, surface):
        size = 160
        x, y = WIDTH - size - 20, 20
        pygame.draw.rect(surface, (20, 20, 20), (x, y, size, size), border_radius=8)
        pygame.draw.rect(surface, (80, 80, 80), (x + 5, y + 5, size - 10, size - 10), border_radius=6)

        # Scale factor
        scale = (size - 20) / (RADAR_RANGE * 2)

        def map_to_minimap(wx, wy):
            dx = wx - self.player_w_pos[0]
            dy = wy - self.player_w_pos[1]
            if abs(dx) > RADAR_RANGE or abs(dy) > RADAR_RANGE:
                return None
            return x + size // 2 + int(dx * scale), y + size // 2 + int(dy * scale)

        # Player dot
        pygame.draw.circle(surface, (255, 255, 255), (x + size // 2, y + size // 2), 5)

        # Enemies
        targets = (self.bees + [self.queen_bee]) if self.current_world == 0 else (self.ants + self.spiders)
        for t in targets:
            if not t.is_alive():
                continue
            pt = map_to_minimap(t.pos[0], t.pos[1])
            if pt:
                pygame.draw.circle(surface, (255, 0, 0), pt, 3)

        # Portal
        portal = PORTAL_TO_WORLD2 if self.current_world == 0 else PORTAL_TO_WORLD1
        pt = map_to_minimap(portal[0], portal[1])
        if pt:
            pygame.draw.circle(surface, (0, 255, 255), pt, 4)

    def draw_xp_tracker(self, surface):
        x, y = 20, 80
        pygame.draw.rect(surface, (20, 20, 20), (x, y, 250, 30), border_radius=8)
        req = 100 + (self.p_lvl - 1) * 50
        pct = self.p_xp / req if req > 0 else 0
        pygame.draw.rect(surface, (50, 150, 255), (x + 4, y + 4, int(pct * 242), 22), border_radius=6)

        txt = font_sm.render(f"LVL {self.p_lvl}   XP {self.p_xp}/{req}", True, (255, 255, 255))
        surface.blit(txt, (x + 10, y + 5))

    def draw_player(self, surface, cam_x, cam_y):
        px, py = int(self.player_w_pos[0] - cam_x), int(self.player_w_pos[1] - cam_y)
        pygame.draw.circle(surface, PLAYER_COLOR, (px, py), self.player_radius)
        pygame.draw.circle(surface, (0, 0, 0), (px, py), self.player_radius, 2)

        # Face (eyes)
        pygame.draw.circle(surface, (0, 0, 0), (px - 10, py - 5), 4)
        pygame.draw.circle(surface, (0, 0, 0), (px + 10, py - 5), 4)
        pygame.draw.arc(surface, (0, 0, 0), (px - 15, py - 5, 30, 20), math.pi, 2 * math.pi, 2)

    def draw_game(self, mx, my):
        cam_x, cam_y = self.player_w_pos[0] - WIDTH // 2, self.player_w_pos[1] - HEIGHT // 2

        screen.fill(MAP_GREEN if self.current_world == 0 else MAP_GREY)
        for x in range(int(cam_x // 100) * 100, int(cam_x + WIDTH) + 100, 100):
            pygame.draw.line(screen, GRID_COLOR if self.current_world == 0 else GRID_GREY, (x - cam_x, 0), (x - cam_x, HEIGHT))
        for y in range(int(cam_y // 100) * 100, int(cam_y + HEIGHT) + 100, 100):
            pygame.draw.line(screen, GRID_COLOR if self.current_world == 0 else GRID_GREY, (0, y - cam_y), (WIDTH, y - cam_y))
        pygame.draw.rect(screen, (200, 200, 200), (-WORLD_SIZE - cam_x, -WORLD_SIZE - cam_y, WORLD_SIZE * 2, WORLD_SIZE * 2), 5)

        for d in self.dropped_items:
            d.draw(screen, cam_x, cam_y)

        if self.current_world == 0:
            sx_p, sy_p = PORTAL_TO_WORLD2[0] - cam_x, PORTAL_TO_WORLD2[1] - cam_y
            pygame.draw.circle(screen, (255, 255, 255), (int(sx_p), int(sy_p)), 60)
            pygame.draw.circle(screen, (200, 240, 255), (int(sx_p), int(sy_p)), 60, 4)
            if dist(self.player_w_pos, PORTAL_TO_WORLD2) < 100:
                if self.p_lvl < 8:
                    screen.blit(font_md.render("REACH LVL 8", True, (255, 50, 50)), (WIDTH // 2 - 50, HEIGHT // 2 - 100))
                if not self.p_queen_killed:
                    screen.blit(font_md.render("KILL QUEEN BEE", True, (255, 50, 50)), (WIDTH // 2 - 60, HEIGHT // 2 - 130))
            self.queen_bee.draw(screen, cam_x, cam_y)
            for b in self.bees:
                b.draw(screen, cam_x, cam_y)
        else:
            sx_p, sy_p = PORTAL_TO_WORLD1[0] - cam_x, PORTAL_TO_WORLD1[1] - cam_y
            pygame.draw.circle(screen, (255, 255, 255), (int(sx_p), int(sy_p)), 60)
            pygame.draw.circle(screen, (200, 240, 255), (int(sx_p), int(sy_p)), 60, 4)
            for a in self.ants:
                a.draw(screen, cam_x, cam_y)
            for s in self.spiders:
                s.draw(screen, cam_x, cam_y)

        for m in self.missiles:
            m.draw(screen, cam_x, cam_y)

        # Player draw (restored)
        self.draw_player(screen, cam_x, cam_y)

        # Petals
        for i, p in enumerate(self.hotbar):
            if not p.is_active:
                continue
            n = len(self.hotbar)
            px_w = self.player_w_pos[0] + self.p_petal_range * math.cos(self.orbit_angle + (2 * math.pi / n) * i)
            py_w = self.player_w_pos[1] + self.p_petal_range * math.sin(self.orbit_angle + (2 * math.pi / n) * i)
            if p.shape == "square":
                pygame.draw.rect(screen, p.color, (int(px_w - cam_x - 12), int(py_w - cam_y - 12), 24, 24))
            else:
                pygame.draw.circle(screen, p.color, (int(px_w - cam_x), int(py_w - cam_y)), 12)

        self.draw_player_hud(screen, mx, my, self.player_w_pos, self.p_health, self.p_max_health)
        self.draw_minimap(screen)
        self.draw_xp_tracker(screen)

        pygame.draw.rect(screen, (200, 50, 50), self.quit_btn_rect, border_radius=8)
        screen.blit(font_md.render("QUIT", True, (255, 255, 255)), (self.quit_btn_rect.centerx - 20, self.quit_btn_rect.centery - 10))
        pygame.draw.rect(screen, (80, 80, 80), self.inv_btn_rect, border_radius=5)
        screen.blit(font_sm.render("INVENTORY", True, (255, 255, 255)), (32, HEIGHT - 102))
        pygame.draw.rect(screen, (80, 80, 80), self.buffs_btn_rect, border_radius=5)
        screen.blit(font_sm.render("BUFFS", True, (255, 255, 255)), (45, HEIGHT - 142))
        pygame.draw.rect(screen, (80, 80, 80), self.upgrade_btn_rect, border_radius=5)
        screen.blit(font_sm.render("UPGRADE", True, (255, 255, 255)), (38, HEIGHT - 182))

        tooltip = None
        for i, p in enumerate(self.hotbar):
            rx, ry = 20 + (i * 60), HEIGHT - 70
            rect = pygame.Rect(rx, ry, 50, 50)
            pygame.draw.rect(screen, (50, 50, 50), rect, border_radius=8)
            pygame.draw.circle(screen, p.color, (rx + 25, ry + 22), 10)
            screen.blit(font_sm.render(p.name, True, (200, 200, 200)),
                        (rx + 25 - font_sm.size(p.name)[0] // 2, ry + 36))

            if not p.is_active:
                ov = pygame.Surface((50, 50), pygame.SRCALPHA)
                ov.fill(COOLDOWN_OVERLAY)
                screen.blit(ov, (rx, ry))

            if rect.collidepoint(pygame.mouse.get_pos()):
                tooltip = (p.name, p.damage, p.cooldown_time)

        if tooltip:
            tx, ty = pygame.mouse.get_pos()[0] + 15, pygame.mouse.get_pos()[1] - 60
            tip_surf = pygame.Surface((130, 55), pygame.SRCALPHA)
            tip_surf.fill((30, 30, 30, 230))
            screen.blit(tip_surf, (tx, ty))
            screen.blit(font_sm.render(tooltip[0], True, (255, 255, 0)), (tx + 10, ty + 5))
            screen.blit(font_sm.render(f"DMG: {tooltip[1]}", True, (255, 255, 255)), (tx + 10, ty + 20))
            screen.blit(font_sm.render(f"RELOAD: {tooltip[2]:.1f}s", True, (255, 255, 255)), (tx + 10, ty + 35))

    def menu_screen(self, mx, my, clicked):
        screen.fill((20, 100, 20))
        screen.blit(font_xl.render("FLORio", True, (255, 255, 255)), (WIDTH // 2 - 150, HEIGHT // 4))

        pygame.draw.rect(screen, (40, 180, 40), self.menu_play_rect, border_radius=15)
        screen.blit(font_lg.render("PLAY", True, (255, 255, 255)), (self.menu_play_rect.centerx - 60, self.menu_play_rect.centery - 25))

        pygame.draw.rect(screen, (40, 140, 180), self.menu_login_rect, border_radius=15)
        screen.blit(font_lg.render("LOGIN", True, (255, 255, 255)), (self.menu_login_rect.centerx - 60, self.menu_login_rect.centery - 25))

        pygame.draw.rect(screen, (180, 140, 40), self.menu_create_rect, border_radius=15)
        screen.blit(font_lg.render("CREATE", True, (255, 255, 255)), (self.menu_create_rect.centerx - 65, self.menu_create_rect.centery - 25))

        pygame.draw.rect(screen, (180, 40, 40), self.menu_quit_rect, border_radius=15)
        screen.blit(font_lg.render("QUIT", True, (255, 255, 255)), (self.menu_quit_rect.centerx - 60, self.menu_quit_rect.centery - 25))

        if clicked:
            if self.menu_play_rect.collidepoint(mx, my):
                self.reset_game()
                self.current_state = STATE_GAME
            elif self.menu_login_rect.collidepoint(mx, my):
                self.current_state = STATE_ACCOUNT_LOGIN
            elif self.menu_create_rect.collidepoint(mx, my):
                self.current_state = STATE_ACCOUNT_CREATE
            elif self.menu_quit_rect.collidepoint(mx, my):
                self.save_to_account()
                pygame.quit()
                exit()

    def inventory_screen(self, mx, my, clicked):
        screen.fill((20, 20, 20))
        ex = pygame.Rect(WIDTH - 150, 30, 120, 50)
        pygame.draw.rect(screen, (150, 50, 50), ex, border_radius=8)
        screen.blit(font_md.render("EXIT", True, (255, 255, 255)), (WIDTH - 115, 42))

        for i, entry in enumerate(self.stored_petals):
            ix, iy = 150 + (i % 8) * 110, 150 + (i // 8) * 110
            r = pygame.Rect(ix, iy, 90, 90)
            pygame.draw.rect(screen, (60, 60, 60), r, border_radius=10)
            pygame.draw.circle(screen, entry[0].color, (ix + 45, iy + 45), 25)
            screen.blit(font_sm.render(f"{entry[1]}x {entry[0].name}", True, (255, 255, 255)), (ix + 5, iy + 75))

            if clicked and r.collidepoint(mx, my):
                self.selected_for_swap_idx = i
                self.current_state = STATE_GAME

        if clicked and ex.collidepoint(mx, my):
            self.current_state = STATE_GAME

    def buffs_screen(self, mx, my, clicked):
        screen.fill((20, 25, 30))
        ex = pygame.Rect(WIDTH - 150, 30, 120, 50)
        pygame.draw.rect(screen, (150, 50, 50), ex, border_radius=8)
        screen.blit(font_md.render("EXIT", True, (255, 255, 255)), (WIDTH - 115, 42))

        bs = pygame.Rect(WIDTH // 2 - 250, HEIGHT // 2 - 75, 120, 120)
        br = pygame.Rect(WIDTH // 2 - 60, HEIGHT // 2 - 75, 120, 120)
        b_slot = pygame.Rect(WIDTH // 2 + 130, HEIGHT // 2 - 75, 120, 120)

        pygame.draw.ellipse(screen, (0, 200, 100) if self.p_lvl_points >= 1 else (80, 80, 80), bs)
        screen.blit(font_sm.render("Speed Cost 1", True, (255, 255, 255)), (bs.centerx - 35, bs.centery - 10))
        pygame.draw.ellipse(screen, (0, 150, 255) if self.p_lvl_points >= 2 else (80, 80, 80), br)
        screen.blit(font_sm.render("Range Cost 2", True, (255, 255, 255)), (br.centerx - 35, br.centery - 10))
        pygame.draw.ellipse(screen, (255, 200, 0) if self.p_lvl_points >= 3 else (80, 80, 80), b_slot)
        screen.blit(font_sm.render("Slot Cost 3", True, (255, 255, 255)), (b_slot.centerx - 30, b_slot.centery - 10))

        if clicked:
            if ex.collidepoint(mx, my):
                self.current_state = STATE_GAME
            elif bs.collidepoint(mx, my) and self.p_lvl_points >= 1:
                self.p_rotation_speed += 0.015
                self.p_lvl_points -= 1
            elif br.collidepoint(mx, my) and self.p_lvl_points >= 2:
                self.p_petal_range += 20
                self.p_lvl_points -= 2
            elif b_slot.collidepoint(mx, my) and self.p_lvl_points >= 3:
                self.hotbar.append(Petal("Basic", BASIC_COLOR))
                self.p_lvl_points -= 3

    def upgrade_screen(self, mx, my, clicked):
        screen.fill((30, 20, 40))
        ex = pygame.Rect(WIDTH - 150, 30, 120, 50)
        pygame.draw.rect(screen, (150, 50, 50), ex, border_radius=8)
        screen.blit(font_md.render("EXIT", True, (255, 255, 255)), (WIDTH - 115, 42))

        c = 0
        for i, entry in enumerate(self.stored_petals):
            if entry[1] >= 10:
                ix, iy = 150 + (c % 8) * 110, 150 + (c // 8) * 110
                r = pygame.Rect(ix, iy, 90, 90)
                pygame.draw.rect(screen, (80, 60, 100), r, border_radius=10)
                pygame.draw.circle(screen, entry[0].color, (ix + 45, iy + 45), 25)
                screen.blit(font_sm.render(f"{entry[1]}x {entry[0].name}", True, (255, 255, 255)), (ix + 5, iy + 75))

                if clicked and r.collidepoint(mx, my):
                    n = entry[0].name
                    d = entry[0].damage * 2
                    cd = entry[0].cooldown_time
                    if "Good" not in n and "Super" not in n:
                        new_n, cd = "Good " + n, cd * 0.85
                    elif "Good" in n:
                        new_n, cd = n.replace("Good", "Super"), cd * 0.70
                    else:
                        continue

                    entry[1] -= 10
                    self.add_to_inventory(new_n, entry[0].color, d, entry[0].shape, cd)
                    if entry[1] <= 0:
                        self.stored_petals.pop(i)
                c += 1

        if clicked and ex.collidepoint(mx, my):
            self.current_state = STATE_GAME

    def dead_screen(self, mx, my, clicked):
        screen.fill((0, 0, 0))
        pygame.draw.rect(screen, (50, 150, 50), self.respawn_btn_rect, border_radius=12)
        screen.blit(font_md.render("RESPAWN", True, (255, 255, 255)),
                    (self.respawn_btn_rect.centerx - 45, self.respawn_btn_rect.centery - 10))
        if clicked and self.respawn_btn_rect.collidepoint(mx, my):
            self.reset_game()

    # --------------------
    # Account Screens
    # --------------------
    def account_create_screen(self, mx, my, clicked):
        screen.fill((40, 40, 80))
        title = font_lg.render("Create Account", True, (255, 255, 255))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))

        uname_box = pygame.Rect(WIDTH // 2 - 200, 200, 400, 60)
        pwd_box = pygame.Rect(WIDTH // 2 - 200, 300, 400, 60)
        create_btn = pygame.Rect(WIDTH // 2 - 150, 420, 300, 70)
        back_btn = pygame.Rect(20, 20, 120, 50)

        pygame.draw.rect(screen, (80, 80, 80), uname_box, border_radius=10)
        pygame.draw.rect(screen, (80, 80, 80), pwd_box, border_radius=10)
        pygame.draw.rect(screen, (40, 180, 40), create_btn, border_radius=15)
        pygame.draw.rect(screen, (150, 50, 50), back_btn, border_radius=10)

        if self.account_focus == "username":
            pygame.draw.rect(screen, (255, 255, 255), uname_box, 3, border_radius=10)
        else:
            pygame.draw.rect(screen, (255, 255, 255), pwd_box, 3, border_radius=10)

        screen.blit(font_md.render("Username:", True, (255, 255, 255)), (uname_box.x + 10, uname_box.y - 25))
        screen.blit(font_md.render("Password:", True, (255, 255, 255)), (pwd_box.x + 10, pwd_box.y - 25))
        screen.blit(font_md.render("Create", True, (255, 255, 255)), (create_btn.centerx - 40, create_btn.centery - 15))
        screen.blit(font_md.render("Back", True, (255, 255, 255)), (back_btn.centerx - 30, back_btn.centery - 15))

        screen.blit(font_md.render(self.account_username, True, (255, 255, 255)), (uname_box.x + 15, uname_box.y + 15))
        screen.blit(font_md.render("*" * len(self.account_password), True, (255, 255, 255)), (pwd_box.x + 15, pwd_box.y + 15))

        if self.account_message:
            msg = font_md.render(self.account_message, True, (255, 255, 0))
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, 520))

        if clicked:
            if back_btn.collidepoint(mx, my):
                self.account_username = ""
                self.account_password = ""
                self.account_message = ""
                self.current_state = STATE_MENU
            elif create_btn.collidepoint(mx, my):
                success, msg = self.create_account(self.account_username, self.account_password)
                self.account_message = msg
                if success:
                    self.current_state = STATE_MENU
            elif uname_box.collidepoint(mx, my):
                self.account_focus = "username"
            elif pwd_box.collidepoint(mx, my):
                self.account_focus = "password"

    def account_login_screen(self, mx, my, clicked):
        screen.fill((40, 40, 80))
        title = font_lg.render("Login", True, (255, 255, 255))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))

        uname_box = pygame.Rect(WIDTH // 2 - 200, 200, 400, 60)
        pwd_box = pygame.Rect(WIDTH // 2 - 200, 300, 400, 60)
        login_btn = pygame.Rect(WIDTH // 2 - 150, 420, 300, 70)
        back_btn = pygame.Rect(20, 20, 120, 50)

        pygame.draw.rect(screen, (80, 80, 80), uname_box, border_radius=10)
        pygame.draw.rect(screen, (80, 80, 80), pwd_box, border_radius=10)
        pygame.draw.rect(screen, (40, 180, 40), login_btn, border_radius=15)
        pygame.draw.rect(screen, (150, 50, 50), back_btn, border_radius=10)

        if self.account_focus == "username":
            pygame.draw.rect(screen, (255, 255, 255), uname_box, 3, border_radius=10)
        else:
            pygame.draw.rect(screen, (255, 255, 255), pwd_box, 3, border_radius=10)

        screen.blit(font_md.render("Username:", True, (255, 255, 255)), (uname_box.x + 10, uname_box.y - 25))
        screen.blit(font_md.render("Password:", True, (255, 255, 255)), (pwd_box.x + 10, pwd_box.y - 25))
        screen.blit(font_md.render("Login", True, (255, 255, 255)), (login_btn.centerx - 30, login_btn.centery - 15))
        screen.blit(font_md.render("Back", True, (255, 255, 255)), (back_btn.centerx - 30, back_btn.centery - 15))

        screen.blit(font_md.render(self.account_username, True, (255, 255, 255)), (uname_box.x + 15, uname_box.y + 15))
        screen.blit(font_md.render("*" * len(self.account_password), True, (255, 255, 255)), (pwd_box.x + 15, pwd_box.y + 15))

        if self.account_message:
            msg = font_md.render(self.account_message, True, (255, 255, 0))
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, 520))

        if clicked:
            if back_btn.collidepoint(mx, my):
                self.account_username = ""
                self.account_password = ""
                self.account_message = ""
                self.current_state = STATE_MENU
            elif login_btn.collidepoint(mx, my):
                success, msg = self.login(self.account_username, self.account_password)
                self.account_message = msg
                if success:
                    self.current_state = STATE_GAME
            elif uname_box.collidepoint(mx, my):
                self.account_focus = "username"
            elif pwd_box.collidepoint(mx, my):
                self.account_focus = "password"

    # --------------------
    # UPDATE
    # --------------------
    def update(self, mx, my, clicked):
        if self.current_state == STATE_MENU:
            self.menu_screen(mx, my, clicked)

        elif self.current_state == STATE_GAME:
            self.update_game(mx, my, clicked)

            if clicked:
                if self.quit_btn_rect.collidepoint(mx, my):
                    self.save_to_account()
                    pygame.quit()
                    exit()
                elif self.inv_btn_rect.collidepoint(mx, my):
                    self.current_state = STATE_INVENTORY
                elif self.buffs_btn_rect.collidepoint(mx, my):
                    self.current_state = STATE_BUFFS
                elif self.upgrade_btn_rect.collidepoint(mx, my):
                    self.current_state = STATE_UPGRADE
                elif self.selected_for_swap_idx is not None:
                    for i in range(len(self.hotbar)):
                        if pygame.Rect(20 + (i * 60), HEIGHT - 70, 50, 50).collidepoint(mx, my):
                            old_p = self.hotbar[i]
                            self.add_to_inventory(old_p.name, old_p.color, old_p.damage, old_p.shape, old_p.cooldown_time)
                            entry = self.stored_petals[self.selected_for_swap_idx]
                            self.hotbar[i] = Petal(entry[0].name, entry[0].color, entry[0].damage, entry[0].shape,
                                                   entry[0].cooldown_time)
                            entry[1] -= 1
                            if entry[1] <= 0:
                                self.stored_petals.pop(self.selected_for_swap_idx)
                            self.selected_for_swap_idx = None

            self.draw_game(mx, my)

        elif self.current_state == STATE_INVENTORY:
            self.inventory_screen(mx, my, clicked)
        elif self.current_state == STATE_BUFFS:
            self.buffs_screen(mx, my, clicked)
        elif self.current_state == STATE_UPGRADE:
            self.upgrade_screen(mx, my, clicked)
        elif self.current_state == STATE_DEAD:
            self.dead_screen(mx, my, clicked)
        elif self.current_state == STATE_ACCOUNT_CREATE:
            self.account_create_screen(mx, my, clicked)
        elif self.current_state == STATE_ACCOUNT_LOGIN:
            self.account_login_screen(mx, my, clicked)

game = Game()

def main_loop():
    while True:
        mx, my = pygame.mouse.get_pos()
        clicked = False
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                clicked = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    exit()
                if game.current_state in [STATE_ACCOUNT_CREATE, STATE_ACCOUNT_LOGIN]:
                    if event.key == pygame.K_BACKSPACE:
                        if game.account_focus == "username":
                            game.account_username = game.account_username[:-1]
                        else:
                            game.account_password = game.account_password[:-1]
                    else:
                        char = event.unicode
                        if char.isprintable():
                            if game.account_focus == "username":
                                game.account_username += char
                            else:
                                game.account_password += char

        game.update(mx, my, clicked)
        pygame.display.flip()
        clock.tick(60)

main_loop()
