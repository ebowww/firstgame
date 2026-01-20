import pygame
import math
import time
import random

# Initialize Pygame
pygame.init()

# --- FULLSCREEN SETUP ---
screen_info = pygame.display.Info()
WIDTH, HEIGHT = screen_info.current_w, screen_info.current_h
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("florr.io Clone - Fully Restored")
clock = pygame.time.Clock()

# --- FONTS ---
font_sm = pygame.font.SysFont("Arial", 11, bold=True)
font_md = pygame.font.SysFont("Arial", 18, bold=True)
font_lg = pygame.font.SysFont("Arial", 48, bold=True)

# --- CONSTANTS ---
MAP_GREEN, GRID_COLOR = (34, 139, 34), (30, 120, 30)
PLAYER_COLOR = (255, 220, 100)
BASIC_COLOR, LIGHT_COLOR, GLASS_COLOR = (0, 200, 255), (255, 255, 200), (230, 245, 255)
STINGER_COLOR = (255, 140, 0)
EYE_WHITE, EYE_BLACK = (255, 255, 255), (0, 0, 0)
BEE_YELLOW, BEE_STRIPE = (255, 215, 0), (40, 40, 40)
COOLDOWN_OVERLAY = (50, 50, 50, 180)

WORLD_SIZE = 3500 
RADAR_RANGE = 2000 
BEE_COUNT = 30 
BEE_RESPAWN_TIME = 15.0
QUEEN_RESPAWN_TIME = 60.0
MISSILE_RANGE = 600

# Game States
STATE_GAME, STATE_INVENTORY, STATE_DEAD, STATE_BUFFS = 0, 1, 2, 3
current_state = STATE_GAME

# --- CLASSES ---

class QueenMissile:
    def __init__(self, x, y, target_pos):
        self.pos = [x, y]
        self.speed = 7.5
        dx, dy = target_pos[0] - x, target_pos[1] - y
        dist = math.hypot(dx, dy)
        self.vel = [(dx/dist)*self.speed, (dy/dist)*self.speed]
        self.angle = math.atan2(dy, dx)
        self.damage = 15
        self.alive = True
        self.spawn_time = time.time()

    def update(self):
        self.pos[0] += self.vel[0]
        self.pos[1] += self.vel[1]
        if time.time() - self.spawn_time > 4.0: self.alive = False

    def draw(self, surface, cam_x, cam_y):
        sx, sy = self.pos[0] - cam_x, self.pos[1] - cam_y
        p1 = (sx + math.cos(self.angle)*15, sy + math.sin(self.angle)*15)
        p2 = (sx + math.cos(self.angle + 2.5)*10, sy + math.sin(self.angle + 2.5)*10)
        p3 = (sx + math.cos(self.angle - 2.5)*10, sy + math.sin(self.angle - 2.5)*10)
        pygame.draw.polygon(surface, (255, 50, 50), [p1, p2, p3])
        pygame.draw.polygon(surface, (255, 255, 255), [p1, p2, p3], 1)

class Petal:
    def __init__(self, name, color, damage=20, shape="circle", cooldown=3.0):
        self.name, self.color, self.damage, self.shape = name, color, damage, shape
        self.cooldown_time = cooldown
        self.last_hit_time, self.is_active = 0, True
        self.radius = 12
    def update(self):
        if not self.is_active and time.time() - self.last_hit_time >= self.cooldown_time:
            self.is_active = True
    def trigger_cooldown(self):
        self.is_active, self.last_hit_time = False, time.time()

class DroppedPetal:
    def __init__(self, x, y, petal_type):
        self.pos, self.type = [x, y], petal_type
        if petal_type == "Basic": self.color, self.shape, self.dmg, self.cd = BASIC_COLOR, "circle", 20, 3.0
        elif petal_type == "Light": self.color, self.shape, self.dmg, self.cd = LIGHT_COLOR, "circle", 20, 1.5
        elif petal_type == "Glass": self.color, self.shape, self.dmg, self.cd = GLASS_COLOR, "square", 40, 3.0
        elif petal_type == "Stinger": self.color, self.shape, self.dmg, self.cd = STINGER_COLOR, "circle", 80, 6.0
        self.radius = 10
    def draw(self, surface, cam_x, cam_y):
        sx, sy = int(self.pos[0] - cam_x), int(self.pos[1] - cam_y)
        if self.shape == "square":
            pygame.draw.rect(surface, self.color, (sx-10, sy-10, 20, 20))
            pygame.draw.rect(surface, (255, 255, 255), (sx-10, sy-10, 20, 20), 2)
        else:
            pygame.draw.circle(surface, self.color, (sx, sy), self.radius)
            pygame.draw.circle(surface, (255, 255, 255), (sx, sy), self.radius, 2)
        txt = font_sm.render(self.type, True, (255, 255, 255))
        surface.blit(txt, (sx - txt.get_width()//2, sy + 15))

class BeeMob:
    def __init__(self, x, y, is_queen=False):
        self.is_queen = is_queen
        self.radius = 75 if is_queen else 25
        self.max_health = 500 if is_queen else 100
        self.health = self.max_health
        self.pos = [x, y]
        self.last_hit_time, self.is_aggressive, self.dropped_loot = 0, False, False
        self.death_time = 0
        self.last_missile_time = 0
    def take_damage(self, amount):
        self.health -= amount
        self.last_hit_time, self.is_aggressive = time.time(), True
        if self.health <= 0: self.death_time = time.time()
    def respawn(self):
        self.health = self.max_health
        self.pos = [random.randint(-WORLD_SIZE+100, WORLD_SIZE-100), random.randint(-WORLD_SIZE+100, WORLD_SIZE-100)]
        self.is_aggressive, self.dropped_loot, self.death_time = False, False, 0
    def update(self, p_pos):
        if self.health > 0:
            speed = 3.2 if self.is_queen else 1.6
            if self.is_aggressive:
                dx, dy = p_pos[0] - self.pos[0], p_pos[1] - self.pos[1]
                dist = math.hypot(dx, dy)
                if dist > 0:
                    self.pos[0] += (dx/dist) * speed
                    self.pos[1] += (dy/dist) * speed
            self.pos[0] = max(-WORLD_SIZE, min(WORLD_SIZE, self.pos[0]))
            self.pos[1] = max(-WORLD_SIZE, min(WORLD_SIZE, self.pos[1]))
    def draw(self, surface, cam_x, cam_y):
        if self.health <= 0: return
        sx, sy = int(self.pos[0]-cam_x), int(self.pos[1]-cam_y)
        is_f = (time.time() - self.last_hit_time) < 0.1
        pygame.draw.circle(surface, (255, 150, 150) if is_f else BEE_YELLOW, (sx, sy), self.radius)
        pygame.draw.rect(surface, BEE_STRIPE, (sx-self.radius*0.4, sy-self.radius*0.7, self.radius*0.25, self.radius*1.4))
        pygame.draw.rect(surface, BEE_STRIPE, (sx+self.radius*0.1, sy-self.radius*0.7, self.radius*0.25, self.radius*1.4))
        if self.is_queen:
            pygame.draw.polygon(surface, (255, 215, 0), [(sx-20, sy-self.radius), (sx-10, sy-self.radius-20), (sx, sy-self.radius), (sx+10, sy-self.radius-20), (sx+20, sy-self.radius)])
        pygame.draw.circle(surface, (0, 0, 0), (sx, sy), self.radius, 2)
        # Restore Bee Labels
        name_txt = font_sm.render("Queen Bee" if self.is_queen else "Bee", True, (255, 255, 255))
        surface.blit(name_txt, (sx - name_txt.get_width()//2, sy - self.radius - 35))
        pygame.draw.rect(surface, (50, 0, 0), (sx-self.radius, sy-self.radius-15, self.radius*2, 8))
        pygame.draw.rect(surface, (255, 50, 50), (sx-self.radius, sy-self.radius-15, int((max(0, self.health)/self.max_health)*(self.radius*2)), 8))

# --- PERSISTENT DATA ---
p_lvl, p_xp, p_lvl_points = 1, 0, 0
p_rotation_speed, p_petal_range = 0.04, 85
hotbar = [Petal("Basic", BASIC_COLOR) for _ in range(5)]
stored_petals = []

# --- TRANSIENT DATA ---
player_w_pos = [0, 0]
p_health, p_hit_time = 100, 0
p_last_attack_time, p_last_regen_time = 0, 0  
dropped_items, bees, queen_missiles = [], [], []
queen_bee = None
orbit_angle, selected_for_swap_idx = 0, None

# UI Rects
quit_btn_rect = pygame.Rect(20, 20, 100, 40)
inv_btn_rect = pygame.Rect(20, HEIGHT - 110, 100, 30)
buffs_btn_rect = pygame.Rect(20, HEIGHT - 150, 100, 30)
respawn_btn_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 20, 200, 60)

# --- CORE FUNCTIONS ---

def reset_game():
    global p_health, player_w_pos, bees, queen_bee, dropped_items, current_state, orbit_angle, p_last_attack_time, p_last_regen_time, queen_missiles
    p_health, player_w_pos, orbit_angle, p_last_attack_time, p_last_regen_time = 100, [0, 0], 0, 0, 0
    dropped_items, queen_missiles = [], []
    bees = [BeeMob(random.randint(-WORLD_SIZE+100, WORLD_SIZE-100), random.randint(-WORLD_SIZE+100, WORLD_SIZE-100)) for _ in range(BEE_COUNT)]
    queen_bee = BeeMob(random.randint(-WORLD_SIZE+500, WORLD_SIZE-500), random.randint(-WORLD_SIZE+500, WORLD_SIZE-500), is_queen=True)
    current_state = STATE_GAME

def add_xp(amount):
    global p_xp, p_lvl, p_lvl_points
    p_xp += amount
    req = 100 + (p_lvl - 1) * 50
    if p_xp >= req: p_xp -= req; p_lvl += 1; p_lvl_points += 1

def add_to_inventory(p_name, p_color, p_dmg, p_shape, p_cd):
    for entry in stored_petals:
        if entry[0].name == p_name: entry[1] += 1; return
    stored_petals.append([Petal(p_name, p_color, p_dmg, p_shape, p_cd), 1])

# --- RENDERING HELPERS ---



def draw_player_hud_restored(surface, px, py, angle, health, hit_time, lvl):
    is_f = (time.time() - hit_time) < 0.1
    pygame.draw.circle(surface, (255, 100, 100) if is_f else PLAYER_COLOR, (px, py), 25)
    pygame.draw.circle(surface, (0, 0, 0), (px, py), 25, 2)
    # Restore Face
    for side in [-1, 1]:
        sa = angle + (side * 0.55)
        sx, sy = px + math.cos(sa)*12, py + math.sin(sa)*12
        eye_surf = pygame.Surface((10, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(eye_surf, EYE_WHITE, (0, 0, 10, 14))
        rot_eye = pygame.transform.rotate(eye_surf, -math.degrees(angle) - 90)
        surface.blit(rot_eye, rot_eye.get_rect(center=(int(sx), int(sy))))
        pygame.draw.circle(surface, EYE_BLACK, (int(sx+math.cos(angle)*3), int(sy+math.sin(angle)*3)), 3)
    pygame.draw.arc(surface, EYE_BLACK, (px-9, py-9, 18, 18), -angle-0.8, -angle+0.8, 3)
    # Restore HUD labels
    pygame.draw.rect(surface, (50, 0, 0), (px-30, py+35, 60, 8))
    pygame.draw.rect(surface, (50, 255, 50), (px-30, py+35, int((max(0,health)/100)*60), 8))
    lvl_txt = font_sm.render(f"Lvl: {lvl}", True, (255, 255, 255))
    surface.blit(lvl_txt, (px - lvl_txt.get_width()//2, py + 45))

def draw_minimap(surface, p_pos, bees, queen):
    map_w, map_h = 180, 180
    map_x, map_y = WIDTH - map_w - 30, 30
    radar_surf = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
    radar_surf.fill((30, 30, 30, 200))
    scale, cx, cy = map_w / RADAR_RANGE, map_w / 2, map_h / 2
    ox, oy = cx - (p_pos[0] * scale), cy - (p_pos[1] * scale)
    pygame.draw.rect(radar_surf, (255, 255, 255), (ox-(WORLD_SIZE*scale), oy-(WORLD_SIZE*scale), (WORLD_SIZE*2)*scale, (WORLD_SIZE*2)*scale), 1)
    for b in bees:
        if b.health > 0:
            bx, by = cx + (b.pos[0]-p_pos[0])*scale, cy + (b.pos[1]-p_pos[1])*scale
            if 0 < bx < map_w and 0 < by < map_h: pygame.draw.circle(radar_surf, (255, 50, 50), (int(bx), int(by)), 2)
    if queen and queen.health > 0:
        qx, qy = cx + (queen.pos[0]-p_pos[0])*scale, cy + (queen.pos[1]-p_pos[1])*scale
        if 0 < qx < map_w and 0 < qy < map_h: pygame.draw.circle(radar_surf, (255, 215, 0), (int(qx), int(qy)), 4)
    pygame.draw.circle(radar_surf, (255, 255, 0), (int(cx), int(cy)), 3)
    surface.blit(radar_surf, (map_x, map_y))
    pygame.draw.rect(surface, (100, 100, 100), (map_x, map_y, map_w, map_h), 2)

def draw_xp_tracker(surface, lvl, xp):
    map_w, map_x, tracker_y = 180, WIDTH - 180 - 30, 225
    req = 100 + (lvl - 1) * 50
    pygame.draw.rect(surface, (40, 40, 40, 180), (map_x, tracker_y, map_w, 50))
    pygame.draw.rect(surface, (100, 100, 100), (map_x, tracker_y, map_w, 50), 2)
    surface.blit(font_sm.render(f"LEVEL {lvl}", True, (255, 255, 255)), (map_x + 10, tracker_y + 8))
    xp_txt = font_sm.render(f"{xp} / {req} XP", True, (200, 200, 200))
    surface.blit(xp_txt, (map_x + map_w - xp_txt.get_width() - 10, tracker_y + 8))
    pygame.draw.rect(surface, (20, 20, 20), (map_x + 10, tracker_y + 28, map_w - 20, 10))
    pygame.draw.rect(surface, (0, 255, 100), (map_x + 10, tracker_y + 28, int((xp/req)*(map_w-20)), 10))

# --- MAIN LOOP ---
reset_game()
running = True
while running:
    mx, my = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE: running = False 
        if event.type == pygame.MOUSEBUTTONDOWN:
            if quit_btn_rect.collidepoint(mx, my): running = False
            if current_state == STATE_GAME:
                if inv_btn_rect.collidepoint(mx, my): current_state = STATE_INVENTORY
                elif buffs_btn_rect.collidepoint(mx, my): current_state = STATE_BUFFS
                elif selected_for_swap_idx is not None:
                    for i in range(5):
                        if pygame.Rect(20+(i*60), HEIGHT-70, 50, 50).collidepoint(mx, my):
                            old_p = hotbar[i]; add_to_inventory(old_p.name, old_p.color, old_p.damage, old_p.shape, old_p.cooldown_time)
                            entry = stored_petals[selected_for_swap_idx]
                            hotbar[i] = Petal(entry[0].name, entry[0].color, entry[0].damage, entry[0].shape, entry[0].cooldown_time)
                            entry[1] -= 1
                            if entry[1] <= 0: stored_petals.pop(selected_for_swap_idx)
                            selected_for_swap_idx = None
            elif current_state == STATE_DEAD and respawn_btn_rect.collidepoint(mx, my): reset_game()

    if current_state == STATE_GAME:
        if p_health <= 0: current_state = STATE_DEAD; continue
        if time.time() - p_last_attack_time > 2.0 and time.time() - p_last_regen_time > 2.0:
            p_health = min(100, p_health + 2); p_last_regen_time = time.time()
        
        cam_x, cam_y = player_w_pos[0]-WIDTH//2, player_w_pos[1]-HEIGHT//2
        player_w_pos[0] += (mx + cam_x - player_w_pos[0]) * 0.025
        player_w_pos[1] += (my + cam_y - player_w_pos[1]) * 0.025
        player_w_pos[0], player_w_pos[1] = max(-WORLD_SIZE, min(WORLD_SIZE, player_w_pos[0])), max(-WORLD_SIZE, min(WORLD_SIZE, player_w_pos[1]))
        
        # Missiles
        for m in queen_missiles[:]:
            m.update()
            if math.hypot(player_w_pos[0]-m.pos[0], player_w_pos[1]-m.pos[1]) < 30:
                p_health -= m.damage; m.alive = False; p_hit_time = time.time()
            if not m.alive: queen_missiles.remove(m)

        # Queen
        if queen_bee.health <= 0:
            if not queen_bee.dropped_loot:
                add_xp(250)
                dropped_items.extend([DroppedPetal(queen_bee.pos[0]-30, queen_bee.pos[1], "Glass"), DroppedPetal(queen_bee.pos[0]+30, queen_bee.pos[1], "Glass"), DroppedPetal(queen_bee.pos[0], queen_bee.pos[1]+30, "Stinger")])
                queen_bee.dropped_loot = True
            if time.time() - queen_bee.death_time >= QUEEN_RESPAWN_TIME: queen_bee.respawn()
        else:
            queen_bee.update(player_w_pos)
            dq = math.hypot(player_w_pos[0]-queen_bee.pos[0], player_w_pos[1]-queen_bee.pos[1])
            if dq < MISSILE_RANGE and time.time() - queen_bee.last_missile_time > 2.0:
                queen_missiles.append(QueenMissile(queen_bee.pos[0], queen_bee.pos[1], player_w_pos)); queen_bee.last_missile_time = time.time()
            if dq < 100:
                player_w_pos[0] += ((player_w_pos[0]-queen_bee.pos[0])/max(1,dq))*60
                player_w_pos[1] += ((player_w_pos[1]-queen_bee.pos[1])/max(1,dq))*60
                if time.time()-p_hit_time > 0.3: p_health -= 30; p_hit_time = time.time()

        for bee in bees:
            if bee.health <= 0:
                if not bee.dropped_loot:
                    add_xp(25); roll = random.random()
                    loot = "Glass" if roll < 0.09 else ("Basic" if roll < 0.54 else "Light")
                    dropped_items.append(DroppedPetal(bee.pos[0], bee.pos[1], loot)); bee.dropped_loot = True
                if time.time() - bee.death_time >= BEE_RESPAWN_TIME: bee.respawn()
                continue
            bee.update(player_w_pos)
            db = math.hypot(player_w_pos[0]-bee.pos[0], player_w_pos[1]-bee.pos[1])
            if db < 50:
                player_w_pos[0] += ((player_w_pos[0]-bee.pos[0])/max(1,db))*45; player_w_pos[1] += ((player_w_pos[1]-bee.pos[1])/max(1,db))*45
                if time.time()-p_hit_time > 0.3: p_health -= 15; p_hit_time = time.time()

        for d in dropped_items[:]:
            if math.hypot(player_w_pos[0]-d.pos[0], player_w_pos[1]-d.pos[1]) < 35:
                add_to_inventory(d.type, d.color, d.dmg, d.shape, d.cd); dropped_items.remove(d)

        orbit_angle += p_rotation_speed
        angle_mouse = math.atan2(my-HEIGHT//2, mx-WIDTH//2)
        for i, p in enumerate(hotbar):
            p.update()
            if p.is_active:
                px_w, py_w = player_w_pos[0]+p_petal_range*math.cos(orbit_angle+(2*math.pi/5)*i), player_w_pos[1]+p_petal_range*math.sin(orbit_angle+(2*math.pi/5)*i)
                if queen_bee.health > 0 and math.hypot(px_w-queen_bee.pos[0], py_w-queen_bee.pos[1]) < 85:
                    queen_bee.take_damage(p.damage); p.trigger_cooldown(); p_last_attack_time = time.time()
                for bee in bees:
                    if bee.health > 0 and math.hypot(px_w-bee.pos[0], py_w-bee.pos[1]) < 37:
                        bee.take_damage(p.damage); p.trigger_cooldown(); p_last_attack_time = time.time()

    # RENDERING
    screen.fill(MAP_GREEN)
    cam_x, cam_y = player_w_pos[0]-WIDTH//2, player_w_pos[1]-HEIGHT//2
    for x in range(int(cam_x//100)*100, int(cam_x+WIDTH)+100, 100): pygame.draw.line(screen, GRID_COLOR, (x-cam_x, 0), (x-cam_x, HEIGHT))
    for y in range(int(cam_y//100)*100, int(cam_y+HEIGHT)+100, 100): pygame.draw.line(screen, GRID_COLOR, (0, y-cam_y), (WIDTH, y-cam_y))
    pygame.draw.rect(screen, (200, 200, 200), (-WORLD_SIZE-cam_x, -WORLD_SIZE-cam_y, WORLD_SIZE*2, WORLD_SIZE*2), 5)
    for d in dropped_items: d.draw(screen, cam_x, cam_y)
    for bee in bees: bee.draw(screen, cam_x, cam_y)
    queen_bee.draw(screen, cam_x, cam_y)
    for m in queen_missiles: m.draw(screen, cam_x, cam_y)
    for i, p in enumerate(hotbar):
        if p.is_active:
            px_w, py_w = player_w_pos[0]+p_petal_range*math.cos(orbit_angle+(2*math.pi/5)*i), player_w_pos[1]+p_petal_range*math.sin(orbit_angle+(2*math.pi/5)*i)
            if p.shape == "square": pygame.draw.rect(screen, p.color, (int(px_w-cam_x-12), int(py_w-cam_y-12), 24, 24))
            else: pygame.draw.circle(screen, p.color, (int(px_w-cam_x), int(py_w-cam_y)), 12)
    
    draw_player_hud_restored(screen, WIDTH//2, HEIGHT//2, angle_mouse if 'angle_mouse' in locals() else 0, p_health, p_hit_time, p_lvl)
    draw_minimap(screen, player_w_pos, bees, queen_bee); draw_xp_tracker(screen, p_lvl, p_xp)
    
    pygame.draw.rect(screen, (200, 50, 50), quit_btn_rect, border_radius=8); screen.blit(font_md.render("QUIT", True, (255, 255, 255)), (quit_btn_rect.centerx-20, quit_btn_rect.centery-10))
    pygame.draw.rect(screen, (80, 80, 80), inv_btn_rect, border_radius=5); screen.blit(font_sm.render("INVENTORY", True, (255, 255, 255)), (32, HEIGHT-102))
    pygame.draw.rect(screen, (80, 80, 80), buffs_btn_rect, border_radius=5); screen.blit(font_sm.render("BUFFS", True, (255, 255, 255)), (45, HEIGHT-142))
    
    for i, p in enumerate(hotbar):
        rx, ry = 20 + (i * 60), HEIGHT - 70
        pygame.draw.rect(screen, (50, 50, 50), (rx, ry, 50, 50), border_radius=8)
        if p.shape == "square": pygame.draw.rect(screen, p.color, (rx+15, ry+12, 20, 20))
        else: pygame.draw.circle(screen, p.color, (rx+25, ry+22), 10)
        p_name = font_sm.render(p.name, True, (200, 200, 200)); screen.blit(p_name, (rx + 25 - p_name.get_width()//2, ry + 36))
        if not p.is_active:
            ov = pygame.Surface((50, 50), pygame.SRCALPHA); ov.fill(COOLDOWN_OVERLAY); screen.blit(ov, (rx, ry))
    
    if current_state == STATE_INVENTORY:
        screen.fill((20, 20, 20))
        ex = pygame.Rect(WIDTH-150, 30, 120, 50); pygame.draw.rect(screen, (150, 50, 50), ex, border_radius=8)
        screen.blit(font_md.render("EXIT", True, (255, 255, 255)), (WIDTH-115, 42))
        slots = []
        for i, entry in enumerate(stored_petals):
            ix, iy = 150 + (i % 8) * 110, 150 + (i // 8) * 110
            r = pygame.Rect(ix, iy, 90, 90); pygame.draw.rect(screen, (60, 60, 60), r, border_radius=10)
            if entry[0].shape == "square": pygame.draw.rect(screen, entry[0].color, (ix+25, iy+15, 40, 40))
            else: pygame.draw.circle(screen, entry[0].color, (ix+45, iy+35), 25)
            screen.blit(font_sm.render(f"{entry[1]}x {entry[0].name}", True, (255, 255, 255)), (ix+5, iy+70)); slots.append((r, i))
        if pygame.mouse.get_pressed()[0]:
            if ex.collidepoint(mx, my): current_state = STATE_GAME; time.sleep(0.2)
            for r, idx in slots:
                if r.collidepoint(mx, my): selected_for_swap_idx = idx; current_state = STATE_GAME; time.sleep(0.2)

    if current_state == STATE_BUFFS:
        screen.fill((20, 25, 30)); ex = pygame.Rect(WIDTH-150, 30, 120, 50); pygame.draw.rect(screen, (150, 50, 50), ex, border_radius=8)
        screen.blit(font_md.render("EXIT", True, (255, 255, 255)), (WIDTH-115, 42))
        screen.blit(font_md.render(f"BUFFS - Points: {p_lvl_points}", True, (255, 255, 255)), (WIDTH//2-80, 50))
        bs = pygame.Rect(WIDTH//2-200, HEIGHT//2-75, 150, 150); pygame.draw.ellipse(screen, (0, 200, 100) if p_lvl_points >= 1 else (80, 80, 80), bs)
        screen.blit(font_sm.render("Speed +1", True, (255, 255, 255)), (bs.centerx-30, bs.centery-5))
        br = pygame.Rect(WIDTH//2+50, HEIGHT//2-75, 150, 150); pygame.draw.ellipse(screen, (0, 150, 255) if p_lvl_points >= 2 else (80, 80, 80), br)
        screen.blit(font_sm.render("Range +1", True, (255, 255, 255)), (br.centerx-30, br.centery-5))
        if pygame.mouse.get_pressed()[0]:
            if ex.collidepoint(mx, my): current_state = STATE_GAME; time.sleep(0.2)
            if bs.collidepoint(mx, my) and p_lvl_points >= 1: p_rotation_speed += 0.015; p_lvl_points -= 1; time.sleep(0.2)
            if br.collidepoint(mx, my) and p_lvl_points >= 2: p_petal_range += 20; p_lvl_points -= 2; time.sleep(0.2)

    if current_state == STATE_DEAD:
        ov = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); ov.fill((0, 0, 0, 180)); screen.blit(ov, (0, 0))
        pygame.draw.rect(screen, (50, 150, 50), respawn_btn_rect, border_radius=12); screen.blit(font_md.render("RESPAWN", True, (255, 255, 255)), (respawn_btn_rect.centerx-45, respawn_btn_rect.centery-10))

    pygame.display.flip(); clock.tick(60)
pygame.quit()
