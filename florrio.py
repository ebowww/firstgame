import pygame
import math
import time
import random

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("florr.io Clone - Range & Speed Buffs")
clock = pygame.time.Clock()

# --- FONTS ---
font_sm = pygame.font.SysFont("Arial", 11, bold=True)
font_md = pygame.font.SysFont("Arial", 18, bold=True)
font_lg = pygame.font.SysFont("Arial", 48, bold=True)

# --- CONSTANTS ---
MAP_GREEN, GRID_COLOR = (34, 139, 34), (30, 120, 30)
PLAYER_COLOR = (255, 220, 100)
BASIC_COLOR, LIGHT_COLOR, GLASS_COLOR = (0, 200, 255), (255, 255, 200), (230, 245, 255)
EYE_WHITE, EYE_BLACK = (255, 255, 255), (0, 0, 0)
BEE_YELLOW, BEE_STRIPE = (255, 215, 0), (40, 40, 40)
COOLDOWN_OVERLAY = (50, 50, 50, 180)

WORLD_SIZE = 2500 
RADAR_RANGE = 1500 
BEE_COUNT = 20

# Game States
STATE_GAME, STATE_INVENTORY, STATE_DEAD, STATE_BUFFS = 0, 1, 2, 3
current_state = STATE_GAME

# --- CLASSES ---

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
        else: self.color, self.shape, self.dmg, self.cd = GLASS_COLOR, "square", 40, 3.0
        self.radius = 10
    def draw(self, surface, cam_x, cam_y):
        sx, sy = int(self.pos[0] - cam_x), int(self.pos[1] - cam_y)
        if self.shape == "square":
            pygame.draw.rect(surface, self.color, (sx-10, sy-10, 20, 20))
            pygame.draw.rect(surface, (255, 255, 255), (sx-10, sy-10, 20, 20), 2)
        else:
            pygame.draw.circle(surface, self.color, (sx, sy), self.radius)
            pygame.draw.circle(surface, (255, 255, 255), (sx, sy), self.radius, 2)

class BeeMob:
    def __init__(self, x, y):
        self.pos = [x, y]
        self.radius, self.max_health, self.health = 25, 100, 100
        self.last_hit_time, self.is_aggressive, self.dropped_loot = 0, False, False
    def take_damage(self, amount):
        self.health -= amount
        self.last_hit_time, self.is_aggressive = time.time(), True
    def update(self, p_pos):
        if self.health > 0:
            if self.is_aggressive:
                dx, dy = p_pos[0] - self.pos[0], p_pos[1] - self.pos[1]
                dist = math.hypot(dx, dy)
                if dist > 0:
                    self.pos[0] += (dx/dist) * 1.6
                    self.pos[1] += (dy/dist) * 1.6
            self.pos[0] = max(-WORLD_SIZE, min(WORLD_SIZE, self.pos[0]))
            self.pos[1] = max(-WORLD_SIZE, min(WORLD_SIZE, self.pos[1]))
    def draw(self, surface, cam_x, cam_y):
        if self.health <= 0: return
        sx, sy = int(self.pos[0]-cam_x), int(self.pos[1]-cam_y)
        is_f = (time.time() - self.last_hit_time) < 0.1
        c = (255, 150, 150) if is_f else BEE_YELLOW
        pygame.draw.circle(surface, c, (sx, sy), self.radius)
        pygame.draw.rect(surface, BEE_STRIPE, (sx-15, sy-20, 8, 40))
        pygame.draw.rect(surface, BEE_STRIPE, (sx+7, sy-20, 8, 40))
        pygame.draw.circle(surface, (0, 0, 0), (sx, sy), self.radius, 2)
        # Bee Labels
        name_txt = font_sm.render("Bee", True, (255, 255, 255))
        surface.blit(name_txt, (sx - name_txt.get_width()//2, sy - self.radius - 35))
        pygame.draw.rect(surface, (50, 0, 0), (sx-25, sy-40, 50, 6))
        pygame.draw.rect(surface, (255, 50, 50), (sx-25, sy-40, int((max(0, self.health)/100)*50), 6))

# --- PERSISTENT DATA ---
p_lvl, p_xp, p_lvl_points = 1, 0, 0
p_rotation_speed = 0.04
p_petal_range = 75 # NEW: Dynamic range
hotbar = [Petal("Basic", BASIC_COLOR) for _ in range(5)]
stored_petals = []

# --- TRANSIENT DATA ---
player_w_pos = [0, 0]
p_health, p_hit_time = 100, 0
dropped_items, bees = [], []
orbit_angle, selected_for_swap_idx = 0, None

# --- UI RECTS ---
inv_btn_rect = pygame.Rect(20, HEIGHT - 110, 100, 30)
buffs_btn_rect = pygame.Rect(20, HEIGHT - 150, 100, 30)
respawn_btn_rect = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 20, 200, 60)

# --- CORE FUNCTIONS ---

def reset_game():
    global p_health, player_w_pos, bees, dropped_items, current_state, orbit_angle
    p_health, player_w_pos, orbit_angle = 100, [0, 0], 0
    dropped_items = []
    bees = [BeeMob(random.randint(-WORLD_SIZE+100, WORLD_SIZE-100), 
                   random.randint(-WORLD_SIZE+100, WORLD_SIZE-100)) for _ in range(BEE_COUNT)]
    current_state = STATE_GAME

def add_xp(amount):
    global p_xp, p_lvl, p_lvl_points
    p_xp += amount
    req = 100 + (p_lvl - 1) * 50
    if p_xp >= req:
        p_xp -= req; p_lvl += 1; p_lvl_points += 1

def add_to_inventory(p_name, p_color, p_dmg, p_shape, p_cd):
    for entry in stored_petals:
        if entry[0].name == p_name: entry[1] += 1; return
    stored_petals.append([Petal(p_name, p_color, p_dmg, p_shape, p_cd), 1])

# --- DRAWING FUNCTIONS ---



def draw_buffs_screen(surface):
    surface.fill((20, 25, 30))
    title = font_md.render(f"BUFFS - Available Level Points: {p_lvl_points}", True, (255, 255, 255))
    surface.blit(title, (WIDTH//2 - title.get_width()//2, 50))
    
    exit_rect = pygame.Rect(WIDTH - 120, 20, 100, 40)
    pygame.draw.rect(surface, (150, 50, 50), exit_rect, border_radius=8)
    surface.blit(font_md.render("EXIT", True, (255, 255, 255)), (WIDTH-95, 28))
    
    # Buff 1: Rotation Speed
    btn_speed = pygame.Rect(WIDTH//2 - 150, HEIGHT//2 - 60, 120, 120)
    color1 = (0, 200, 100) if p_lvl_points >= 1 else (80, 80, 80)
    pygame.draw.ellipse(surface, color1, btn_speed)
    pygame.draw.ellipse(surface, (255, 255, 255), btn_speed, 2)
    t1 = font_sm.render("Rotation Speed +1", True, (255, 255, 255))
    c1 = font_sm.render("Cost: 1 Pt", True, (255, 255, 0))
    surface.blit(t1, (btn_speed.centerx - t1.get_width()//2, btn_speed.centery - 15))
    surface.blit(c1, (btn_speed.centerx - c1.get_width()//2, btn_speed.centery + 5))

    # Buff 2: Petal Range
    btn_range = pygame.Rect(WIDTH//2 + 30, HEIGHT//2 - 60, 120, 120)
    color2 = (0, 150, 255) if p_lvl_points >= 2 else (80, 80, 80)
    pygame.draw.ellipse(surface, color2, btn_range)
    pygame.draw.ellipse(surface, (255, 255, 255), btn_range, 2)
    t2 = font_sm.render("Petal Range +1", True, (255, 255, 255))
    c2 = font_sm.render("Cost: 2 Pts", True, (255, 255, 0))
    surface.blit(t2, (btn_range.centerx - t2.get_width()//2, btn_range.centery - 15))
    surface.blit(c2, (btn_range.centerx - c2.get_width()//2, btn_range.centery + 5))
    
    return exit_rect, btn_speed, btn_range

def draw_inventory_screen(surface, stored_petals):
    surface.fill((20, 20, 20))
    title = font_md.render("INVENTORY", True, (255, 255, 255))
    surface.blit(title, (WIDTH//2 - title.get_width()//2, 30))
    exit_rect = pygame.Rect(WIDTH - 120, 20, 100, 40)
    pygame.draw.rect(surface, (150, 50, 50), exit_rect, border_radius=8)
    surface.blit(font_md.render("EXIT", True, (255, 255, 255)), (WIDTH-95, 28))
    slots = []
    for i, entry in enumerate(stored_petals):
        p, count = entry[0], entry[1]
        ix, iy = 100 + (i % 5) * 80, 120 + (i // 5) * 80
        rect = pygame.Rect(ix, iy, 60, 60)
        pygame.draw.rect(surface, (60, 60, 60), rect, border_radius=10)
        if p.shape == "square": pygame.draw.rect(surface, p.color, (ix+18, iy+13, 24, 24))
        else: pygame.draw.circle(surface, p.color, (ix+30, iy+25), 15)
        if count > 1: surface.blit(font_sm.render(f"{count}x", True, (255, 255, 0)), (ix + 5, iy + 5))
        n_txt = font_sm.render(p.name, True, (200, 200, 200))
        surface.blit(n_txt, (ix + 30 - n_txt.get_width()//2, iy + 45))
        slots.append((rect, i))
    return slots, exit_rect

def draw_minimap(surface, p_pos, bees):
    map_w, map_h = 150, 150
    map_x, map_y = WIDTH - map_w - 20, 20
    radar_surf = pygame.Surface((map_w, map_h), pygame.SRCALPHA)
    radar_surf.fill((30, 30, 30, 200))
    scale = map_w / RADAR_RANGE
    cx, cy = map_w / 2, map_h / 2
    wall_dist = WORLD_SIZE * scale
    ox, oy = cx - (p_pos[0] * scale), cy - (p_pos[1] * scale)
    pygame.draw.rect(radar_surf, (255, 255, 255), (ox-wall_dist, oy-wall_dist, wall_dist*2, wall_dist*2), 1)
    for b in bees:
        if b.health > 0:
            bx, by = cx + (b.pos[0]-p_pos[0])*scale, cy + (b.pos[1]-p_pos[1])*scale
            pygame.draw.circle(radar_surf, (255, 50, 50), (int(bx), int(by)), 2)
    pygame.draw.circle(radar_surf, (255, 255, 0), (int(cx), int(cy)), 3)
    surface.blit(radar_surf, (map_x, map_y))
    pygame.draw.rect(surface, (100, 100, 100), (map_x, map_y, map_w, map_h), 2)

def draw_player_hud(surface, px, py, angle, health, hit_time, lvl):
    is_f = (time.time() - hit_time) < 0.1
    c = (255, 100, 100) if is_f else PLAYER_COLOR
    pygame.draw.circle(surface, c, (px, py), 25)
    pygame.draw.circle(surface, (0, 0, 0), (px, py), 25, 2)
    # Eyes & Smile
    for side in [-1, 1]:
        sa = angle + (side * 0.55)
        sx, sy = px + math.cos(sa)*12, py + math.sin(sa)*12
        eye_surf = pygame.Surface((10, 14), pygame.SRCALPHA)
        pygame.draw.ellipse(eye_surf, EYE_WHITE, (0, 0, 10, 14))
        rot_eye = pygame.transform.rotate(eye_surf, -math.degrees(angle) - 90)
        surface.blit(rot_eye, rot_eye.get_rect(center=(int(sx), int(sy))))
        pygame.draw.circle(surface, EYE_BLACK, (int(sx+math.cos(angle)*3), int(sy+math.sin(angle)*3)), 3)
    pygame.draw.arc(surface, EYE_BLACK, (px-9, py-9, 18, 18), -angle-0.8, -angle+0.8, 3)
    pygame.draw.rect(surface, (50, 0, 0), (px-30, py+35, 60, 8))
    pygame.draw.rect(surface, (50, 255, 50), (px-30, py+35, int((max(0,health)/100)*60), 8))
    lvl_txt = font_sm.render(f"Lvl: {lvl}", True, (255, 255, 255))
    surface.blit(lvl_txt, (px - lvl_txt.get_width()//2, py + 45))

# --- MAIN LOOP ---
reset_game()
running = True
while running:
    mx, my = pygame.mouse.get_pos()
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if current_state == STATE_GAME:
                if inv_btn_rect.collidepoint(mx, my): current_state = STATE_INVENTORY
                elif buffs_btn_rect.collidepoint(mx, my): current_state = STATE_BUFFS
                elif selected_for_swap_idx is not None:
                    for i in range(5):
                        h_rect = pygame.Rect(20+(i*60), HEIGHT-70, 50, 50)
                        if h_rect.collidepoint(mx, my):
                            old_p = hotbar[i]; add_to_inventory(old_p.name, old_p.color, old_p.damage, old_p.shape, old_p.cooldown_time)
                            entry = stored_petals[selected_for_swap_idx]
                            hotbar[i] = Petal(entry[0].name, entry[0].color, entry[0].damage, entry[0].shape, entry[0].cooldown_time)
                            entry[1] -= 1
                            if entry[1] <= 0: stored_petals.pop(selected_for_swap_idx)
                            selected_for_swap_idx = None
            elif current_state == STATE_DEAD and respawn_btn_rect.collidepoint(mx, my): reset_game()

    if current_state == STATE_GAME:
        if p_health <= 0: current_state = STATE_DEAD; continue
        cam_x, cam_y = player_w_pos[0]-WIDTH//2, player_w_pos[1]-HEIGHT//2
        player_w_pos[0] += (mx + cam_x - player_w_pos[0]) * 0.025
        player_w_pos[1] += (my + cam_y - player_w_pos[1]) * 0.025
        player_w_pos[0] = max(-WORLD_SIZE, min(WORLD_SIZE, player_w_pos[0]))
        player_w_pos[1] = max(-WORLD_SIZE, min(WORLD_SIZE, player_w_pos[1]))
        
        for bee in bees:
            bee.update(player_w_pos)
            if bee.health > 0:
                dist = math.hypot(player_w_pos[0]-bee.pos[0], player_w_pos[1]-bee.pos[1])
                if dist < 50:
                    player_w_pos[0] += ((player_w_pos[0]-bee.pos[0])/max(1,dist))*45
                    player_w_pos[1] += ((player_w_pos[1]-bee.pos[1])/max(1,dist))*45
                    if time.time()-p_hit_time > 0.3: p_health -= 15; p_hit_time = time.time()
            if bee.health <= 0 and not bee.dropped_loot:
                add_xp(25)
                roll = random.random()
                loot = "Glass" if roll < 0.09 else ("Basic" if roll < 0.54 else "Light")
                dropped_items.append(DroppedPetal(bee.pos[0], bee.pos[1], loot)); bee.dropped_loot = True

        for d in dropped_items[:]:
            if math.hypot(player_w_pos[0]-d.pos[0], player_w_pos[1]-d.pos[1]) < 35:
                add_to_inventory(d.type, d.color, d.dmg, d.shape, d.cd); dropped_items.remove(d)

        orbit_angle += p_rotation_speed
        angle_mouse = math.atan2(my-HEIGHT//2, mx-WIDTH//2)
        for i, p in enumerate(hotbar):
            p.update()
            if p.is_active:
                # Use p_petal_range here
                px_w = player_w_pos[0]+p_petal_range*math.cos(orbit_angle+(2*math.pi/5)*i)
                py_w = player_w_pos[1]+p_petal_range*math.sin(orbit_angle+(2*math.pi/5)*i)
                for bee in bees:
                    if bee.health > 0 and math.hypot(px_w-bee.pos[0], py_w-bee.pos[1]) < 37:
                        bee.take_damage(p.damage); p.trigger_cooldown()

    # RENDERING
    screen.fill(MAP_GREEN)
    cam_x, cam_y = player_w_pos[0]-WIDTH//2, player_w_pos[1]-HEIGHT//2
    for x in range(int(cam_x//100)*100, int(cam_x+WIDTH)+100, 100): pygame.draw.line(screen, GRID_COLOR, (x-cam_x, 0), (x-cam_x, HEIGHT))
    for y in range(int(cam_y//100)*100, int(cam_y+HEIGHT)+100, 100): pygame.draw.line(screen, GRID_COLOR, (0, y-cam_y), (WIDTH, y-cam_y))
    pygame.draw.rect(screen, (200, 200, 200), (-WORLD_SIZE-cam_x, -WORLD_SIZE-cam_y, WORLD_SIZE*2, WORLD_SIZE*2), 5)
    for d in dropped_items: d.draw(screen, cam_x, cam_y)
    for bee in bees: bee.draw(screen, cam_x, cam_y)
    for i, p in enumerate(hotbar):
        if p.is_active:
            px_w = player_w_pos[0]+p_petal_range*math.cos(orbit_angle+(2*math.pi/5)*i)
            py_w = player_w_pos[1]+p_petal_range*math.sin(orbit_angle+(2*math.pi/5)*i)
            if p.shape == "square": pygame.draw.rect(screen, p.color, (int(px_w-cam_x-12), int(py_w-cam_y-12), 24, 24))
            else: pygame.draw.circle(screen, p.color, (int(px_w-cam_x), int(py_w-cam_y)), 12)

    draw_player_hud(screen, WIDTH//2, HEIGHT//2, angle_mouse if 'angle_mouse' in locals() else 0, p_health, p_hit_time, p_lvl)
    draw_minimap(screen, player_w_pos, bees)
    
    # UI
    pygame.draw.rect(screen, (80, 80, 80), inv_btn_rect, border_radius=5)
    screen.blit(font_sm.render("INVENTORY", True, (255, 255, 255)), (32, HEIGHT-102))
    pygame.draw.rect(screen, (80, 80, 80), buffs_btn_rect, border_radius=5)
    screen.blit(font_sm.render("BUFFS", True, (255, 255, 255)), (45, HEIGHT-142))
    
    for i, p in enumerate(hotbar):
        rx, ry = 20 + (i * 60), HEIGHT - 70
        pygame.draw.rect(screen, (50, 50, 50), (rx, ry, 50, 50), border_radius=8)
        if p.shape == "square": pygame.draw.rect(screen, p.color, (rx+15, ry+12, 20, 20))
        else: pygame.draw.circle(screen, p.color, (rx+25, ry+22), 10)
        p_name = font_sm.render(p.name, True, (200, 200, 200))
        screen.blit(p_name, (rx + 25 - p_name.get_width()//2, ry + 36))
        if not p.is_active:
            overlay = pygame.Surface((50, 50), pygame.SRCALPHA); overlay.fill(COOLDOWN_OVERLAY); screen.blit(overlay, (rx, ry))

    if selected_for_swap_idx is not None:
        msg = font_md.render("CLICK A HOTBAR SLOT TO SWAP", True, (255, 255, 0))
        screen.blit(msg, (WIDTH//2 - msg.get_width()//2, HEIGHT-140))

    if current_state == STATE_INVENTORY:
        slots, ex_rect = draw_inventory_screen(screen, stored_petals)
        if pygame.mouse.get_pressed()[0]:
            if ex_rect.collidepoint(mx, my): current_state = STATE_GAME; time.sleep(0.2)
            for r, idx in slots:
                if r.collidepoint(mx, my): selected_for_swap_idx = idx; current_state = STATE_GAME; time.sleep(0.2)

    if current_state == STATE_BUFFS:
        ex_rect, b_speed, b_range = draw_buffs_screen(screen)
        if pygame.mouse.get_pressed()[0]:
            if ex_rect.collidepoint(mx, my): current_state = STATE_GAME; time.sleep(0.2)
            # Speed Buff (1 Point)
            if b_speed.collidepoint(mx, my) and p_lvl_points >= 1:
                p_rotation_speed += 0.015; p_lvl_points -= 1; time.sleep(0.2)
            # Range Buff (2 Points)
            if b_range.collidepoint(mx, my) and p_lvl_points >= 2:
                p_petal_range += 15; p_lvl_points -= 2; time.sleep(0.2)

    if current_state == STATE_DEAD:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, 180)); screen.blit(overlay, (0, 0))
        txt = font_lg.render("YOU DIED", True, (255, 50, 50))
        screen.blit(txt, (WIDTH//2 - txt.get_width()//2, HEIGHT//2 - 60))
        pygame.draw.rect(screen, (50, 150, 50), respawn_btn_rect, border_radius=12)
        r_txt = font_md.render("RESPAWN", True, (255, 255, 255))
        screen.blit(r_txt, (respawn_btn_rect.centerx - r_txt.get_width()//2, respawn_btn_rect.centery - r_txt.get_height()//2))

    pygame.display.flip()
    clock.tick(60)
pygame.quit()
