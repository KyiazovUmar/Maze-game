import math
import random
import pygame

# Initialize Pygame
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("RetroRay // Horror Edition")
clock = pygame.time.Clock()

# Map Configuration (1 = Wall, 0 = Open Space, 2 = Exit Door)
world_map = [
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1],
    [1,0,0,0,0,0,1,0,0,0,0,0,0,0,0,1],
    [1,0,1,1,0,0,1,0,1,1,1,1,0,1,2,1],
    [1,0,1,0,0,0,0,0,0,0,0,1,0,1,0,1],
    [1,0,1,1,1,1,1,0,1,1,0,1,0,1,0,1],
    [1,0,0,0,0,0,1,0,1,0,0,0,0,0,0,1],
    [1,1,1,1,0,0,1,0,1,1,1,1,1,1,0,1],
    [1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
    [1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1]
]

# Player State
player_x = 1.5
player_y = 1.5
player_angle = 0.0
player_health = 100
FOV = math.pi / 3
HALF_FOV = FOV / 2
NUM_RAYS = 160
MAX_DEPTH = 16.0
DELTA_ANGLE = FOV / NUM_RAYS

# Depth Buffer for Wall Occlusion
z_buffer = [0.0] * WIDTH

# Entities (Aggressive Zombies placed safely inside open corridors)
zombies = [
    {"x": 3.5, "y": 1.5, "health": 50, "speed": 0.018, "is_fat": False},
    {"x": 8.5, "y": 5.5, "health": 50, "speed": 0.018, "is_fat": True},
    {"x": 13.5, "y": 7.5, "health": 50, "speed": 0.022, "is_fat": False}
]

# Particles for Blood Splatter
particles = []

# Weapon State
is_shooting = False
shoot_timer = 0

def render_scene():
    global player_x, player_y, player_angle, z_buffer

    # Dark, atmospheric horror fog for ceiling/floor
    screen.fill((8, 5, 8), (0, 0, WIDTH, HEIGHT // 2))       # Dark Ceiling
    screen.fill((12, 3, 3), (0, HEIGHT // 2, WIDTH, HEIGHT // 2)) # Dark Blood Floor

    # Cast Rays for Walls and Populate Z-Buffer
    ray_angle = player_angle - HALF_FOV
    column_width = WIDTH / NUM_RAYS
    
    for ray in range(NUM_RAYS):
        sin_a = math.sin(ray_angle)
        cos_a = math.cos(ray_angle)

        depth = 0.0
        hit_wall = False
        wall_type = 1
        while not hit_wall and depth < MAX_DEPTH:
            depth += 0.04
            test_x = int(player_x + cos_a * depth)
            test_y = int(player_y + sin_a * depth)

            if test_x < 0 or test_x >= len(world_map[0]) or test_y < 0 or test_y >= len(world_map):
                hit_wall = True
                depth = MAX_DEPTH
            elif world_map[test_y][test_x] > 0:
                hit_wall = True
                wall_type = world_map[test_y][test_x]

        # Fish-eye correction
        fish_eye_correction = depth * math.cos(player_angle - ray_angle)
        wall_height = min(HEIGHT, int((1.0 / (fish_eye_correction + 0.0001)) * 350))
        
        if wall_type == 2:
            shade = max(30, min(200, int(200 - (depth / MAX_DEPTH) * 150)))
            wall_color = (0, shade, 0)
        else:
            shade = max(10, min(120, int(120 - (depth / MAX_DEPTH) * 100)))
            wall_color = (shade // 3, shade // 5, shade // 5)

        wall_top = (HEIGHT // 2) - (wall_height // 2)
        start_x = int(ray * column_width)
        end_x = int((ray + 1) * column_width)
        
        pygame.draw.rect(screen, wall_color, (start_x, wall_top, end_x - start_x, wall_height))

        # Fill Z-Buffer for occlusion checks safely within screen bounds
        for x_col in range(start_x, min(WIDTH, end_x)):
            if 0 <= x_col < WIDTH:
                z_buffer[x_col] = fish_eye_correction

        ray_angle += DELTA_ANGLE

    # Render Blood Particles on Floor/World (with Z-buffer check)
    for p in particles:
        dx = p["x"] - player_x
        dy = p["y"] - player_y
        dist = math.hypot(dx, dy)
        if dist < 0.2:
            continue
        angle_to_p = math.atan2(dy, dx) - player_angle
        while angle_to_p < -math.pi: angle_to_p += 2 * math.pi
        while angle_to_p > math.pi: angle_to_p -= 2 * math.pi

        if -HALF_FOV < angle_to_p < HALF_FOV:
            px = int((WIDTH // 2) + (angle_to_p / HALF_FOV) * (WIDTH // 2))
            if 0 <= px < WIDTH and dist < z_buffer[px]:
                py = (HEIGHT // 2) + int((p["z"] / (dist + 0.0001)) * 200)
                p_size = max(2, int(14 / (dist + 0.1)))
                pygame.draw.circle(screen, (230, 10, 10), (px, py), p_size)

    # Render Extremely Terrifying, Nightmarish Zombies with Safe Z-Buffer Occlusion
    for z in sorted(zombies, key=lambda zombie: math.hypot(zombie["x"] - player_x, zombie["y"] - player_y), reverse=True):
        if z["health"] <= 0:
            continue
        
        dx = z["x"] - player_x
        dy = z["y"] - player_y
        distance = math.hypot(dx, dy)

        if distance < 0.2:
            continue

        angle_to_zombie = math.atan2(dy, dx) - player_angle
        while angle_to_zombie < -math.pi: angle_to_zombie += 2 * math.pi
        while angle_to_zombie > math.pi: angle_to_zombie -= 2 * math.pi

        if -HALF_FOV < angle_to_zombie < HALF_FOV:
            screen_x = (WIDTH // 2) + (angle_to_zombie / HALF_FOV) * (WIDTH // 2)
            
            # Safe occlusion check against walls
            int_sx = int(screen_x)
            if 0 <= int_sx < WIDTH and distance > z_buffer[int_sx] + 0.2:
                continue # Hidden behind a wall

            sprite_height = min(HEIGHT, int((1.0 / (distance + 0.0001)) * 350))
            sprite_width = sprite_height // (1.1 if z["is_fat"] else 1.5)
            
            # Unsettling horror twitch & lurching animation
            twitch_x = int(math.sin(pygame.time.get_ticks() * 0.04 + z["x"]) * 6)
            bob_offset = int(abs(math.sin(pygame.time.get_ticks() * 0.02 + z["y"])) * (sprite_height * 0.08))
            center_x = int(screen_x) + twitch_x
            center_y = HEIGHT // 2 + bob_offset
            
            # Torso: Decaying dark blue jacket & visceral gore
            torso_w = int(sprite_width * (0.85 if z["is_fat"] else 0.6))
            torso_h = int(sprite_height * 0.42)
            torso_rect = pygame.Rect(center_x - torso_w // 2, center_y - torso_h // 4, torso_w, torso_h)
            pygame.draw.rect(screen, (20, 35, 60), torso_rect)
            
            # Deep gore and blood splatters across chest
            pygame.draw.circle(screen, (170, 10, 10), (center_x - torso_w // 4, center_y), max(5, torso_w // 6))
            pygame.draw.circle(screen, (120, 5, 5), (center_x + torso_w // 4, center_y + 10), max(4, torso_w // 6))
            
            # White shirt opening & Blood-soaked red tie hanging torn
            shirt_w = max(5, torso_w // 3)
            pygame.draw.rect(screen, (190, 190, 190), (center_x - shirt_w // 2, center_y - torso_h // 4, shirt_w, torso_h // 2))
            pygame.draw.rect(screen, (230, 20, 20), (center_x - 3, center_y - torso_h // 4, 6, torso_h // 2))

            # Reaching Bony, Blood-Dripping Claws
            hand_size = max(8, int(sprite_height * 0.15))
            pygame.draw.circle(screen, (75, 110, 55), (center_x - torso_w // 2 - hand_size // 2, center_y + 15), hand_size)
            pygame.draw.circle(screen, (75, 110, 55), (center_x + torso_w // 2 + hand_size // 2, center_y + 15), hand_size)
            pygame.draw.circle(screen, (10, 10, 10), (center_x - torso_w // 2 - hand_size // 2 - 2, center_y + 19), hand_size // 3)
            pygame.draw.circle(screen, (10, 10, 10), (center_x + torso_w // 2 + hand_size // 2 + 2, center_y + 19), hand_size // 3)

            # Tattered Pants
            leg_w = max(6, torso_w // 3)
            leg_h = int(sprite_height * 0.32)
            pygame.draw.rect(screen, (35, 35, 40), (center_x - leg_w - 2, center_y + torso_h * 3 // 4, leg_w, leg_h))
            pygame.draw.rect(screen, (35, 35, 40), (center_x + 2, center_y + torso_h * 3 // 4, leg_w, leg_h))

            # Sinister, Demonic Rotten Green Head with Glowing Red Eyes
            head_size = int(sprite_height * 0.34)
            head_y = center_y - torso_h // 4 - head_size
            pygame.draw.rect(screen, (75, 110, 45), (center_x - head_size // 2, head_y, head_size, head_size))

            # Dark Messy Hair Swoop
            hair_rect = pygame.Rect(center_x - head_size // 2 - 5, head_y - 8, head_size + 10, head_size // 2)
            pygame.draw.ellipse(screen, (25, 18, 15), hair_rect)

            # Glowing Madness Eyes
            eye_w = max(6, head_size // 3)
            eye_h = max(6, head_size // 2.5)
            pygame.draw.ellipse(screen, (255, 230, 100), (center_x - head_size // 3 - 3, head_y + head_size // 3, eye_w, eye_h))
            pygame.draw.ellipse(screen, (255, 230, 100), (center_x + 2, head_y + head_size // 3, eye_w, eye_h))
            pygame.draw.circle(screen, (220, 10, 10), (center_x - head_size // 6, head_y + head_size // 2), max(2, head_size // 11))
            pygame.draw.circle(screen, (220, 10, 10), (center_x + head_size // 5, head_y + head_size // 2), max(2, head_size // 11))

            # Gaping, Bleeding Scream Jaw
            jaw_rect = pygame.Rect(center_x - head_size // 3, head_y + head_size * 2 // 3, head_size * 2 // 3, head_size // 3)
            pygame.draw.rect(screen, (35, 5, 5), jaw_rect)
            pygame.draw.line(screen, (255, 255, 255), (center_x - 4, head_y + head_size * 2 // 3), (center_x - 4, head_y + head_size - 2), 2)
            pygame.draw.line(screen, (255, 255, 255), (center_x + 4, head_y + head_size * 2 // 3), (center_x + 4, head_y + head_size - 2), 2)

    # Render 2D Gun HUD with Massive Orange-Red Shot Fire
    gun_base_x = WIDTH // 2 + 70
    gun_base_y = HEIGHT - 220
    if is_shooting:
        pygame.draw.circle(screen, (255, 60, 0), (gun_base_x - 50, gun_base_y - 120), 75)
        pygame.draw.circle(screen, (255, 140, 0), (gun_base_x - 50, gun_base_y - 120), 50)
        pygame.draw.circle(screen, (255, 255, 100), (gun_base_x - 50, gun_base_y - 120), 25)
        pygame.draw.rect(screen, (65, 70, 80), (gun_base_x - 25, gun_base_y - 40, 70, 220))
        pygame.draw.rect(screen, (30, 35, 40), (gun_base_x - 35, gun_base_y + 70, 85, 100))
    else:
        pygame.draw.rect(screen, (55, 60, 70), (gun_base_x - 25, gun_base_y, 70, 220))
        pygame.draw.rect(screen, (25, 30, 35), (gun_base_x - 35, gun_base_y + 90, 85, 100))
        pygame.draw.line(screen, (20, 20, 25), (gun_base_x, gun_base_y), (gun_base_x, gun_base_y + 110), 6)

    # Render UI Overlay
    font = pygame.font.SysFont(None, 24)
    health_text = font.render(f"HEALTH: {player_health}", True, (255, 50, 50))
    objective_text = font.render("OBJECTIVE: Find the Green Exit Door", True, (0, 255, 255))
    screen.blit(health_text, (20, 20))
    screen.blit(objective_text, (20, 50))

# Main Game Loop
running = True
game_over = False
win = False

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN or (event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE):
            if not game_over and not win:
                is_shooting = True
                shoot_timer = 6
                
                # Check hits & spawn extreme blood fountain explosion
                for z in zombies:
                    if z["health"] > 0:
                        dx = z["x"] - player_x
                        dy = z["y"] - player_y
                        angle_to_z = math.atan2(dy, dx) - player_angle
                        while angle_to_z < -math.pi: angle_to_z += 2 * math.pi
                        while angle_to_z > math.pi: angle_to_z -= 2 * math.pi
                        if abs(angle_to_z) < 0.35 and math.hypot(dx, dy) < 7.0:
                            z["health"] -= 50
                            for _ in range(150):
                                p_angle = random.uniform(0, 2 * math.pi)
                                p_speed = random.uniform(0.02, 0.1)
                                particles.append({
                                    "x": z["x"] + math.cos(p_angle) * 0.2,
                                    "y": z["y"] + math.sin(p_angle) * 0.2,
                                    "z": random.uniform(-0.4, 0.6),
                                    "vx": math.cos(p_angle) * p_speed,
                                    "vy": math.sin(p_angle) * p_speed,
                                    "life": 240
                                })

    # Update Particles Safely
    for p in particles[:]:
        p["x"] += p["vx"]
        p["y"] += p["vy"]
        p["life"] -= 1
        if p["life"] <= 0:
            particles.remove(p)

    if not game_over and not win:
        if is_shooting:
            shoot_timer -= 1
            if shoot_timer <= 0:
                is_shooting = False

        keys = pygame.key.get_pressed()
        move_speed = 0.04
        rot_speed = 0.04

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            player_angle -= rot_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            player_angle += rot_speed

        dx = math.cos(player_angle) * move_speed
        dy = math.sin(player_angle) * move_speed

        # Safe player map boundary checks to prevent crashes out of bounds
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            new_x = player_x + dx
            new_y = player_y + dy
            if 0 <= int(new_x) < len(world_map[0]) and world_map[int(player_y)][int(new_x)] != 1: player_x = new_x
            if 0 <= int(new_y) < len(world_map) and world_map[int(new_y)][int(player_x)] != 1: player_y = new_y
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            new_x = player_x - dx
            new_y = player_y - dy
            if 0 <= int(new_x) < len(world_map[0]) and world_map[int(player_y)][int(new_x)] != 1: player_x = new_x
            if 0 <= int(new_y) < len(world_map) and world_map[int(new_y)][int(player_x)] != 1: player_y = new_y

        if 0 <= int(player_y) < len(world_map) and 0 <= int(player_x) < len(world_map[0]):
            if world_map[int(player_y)][int(player_x)] == 2:
                win = True

        # Robust Zombie Tracking AI with Safe Map Bounds Checks
        for z in zombies:
            if z["health"] > 0:
                z_dx = player_x - z["x"]
                z_dy = player_y - z["y"]
                z_dist = math.hypot(z_dx, z_dy)
                
                if z_dist > 0.45:
                    move_x = (z_dx / z_dist) * z["speed"]
                    move_y = (z_dy / z_dist) * z["speed"]
                    
                    next_x = z["x"] + move_x
                    next_y = z["y"] + move_y
                    
                    # Prevent array index out of bounds crashes
                    if 0 <= int(z["y"]) < len(world_map) and 0 <= int(next_x) < len(world_map[0]):
                        if world_map[int(z["y"])][int(next_x)] != 1:
                            z["x"] = next_x
                    if 0 <= int(next_y) < len(world_map) and 0 <= int(z["x"]) < len(world_map[0]):
                        if world_map[int(next_y)][int(z["x"])] != 1:
                            z["y"] = next_y
                else:
                    player_health -= 1
                    if player_health <= 0:
                        game_over = True
                        for _ in range(300):
                            p_angle = random.uniform(0, 2 * math.pi)
                            p_speed = random.uniform(0.01, 0.1)
                            particles.append({
                                "x": player_x + math.cos(p_angle) * 0.1,
                                "y": player_y + math.sin(p_angle) * 0.1,
                                "z": random.uniform(-0.3, 0.5),
                                "vx": math.cos(p_angle) * p_speed,
                                "vy": math.sin(p_angle) * p_speed,
                                "life": 350
                            })

        render_scene()
    else:
        screen.fill((15, 2, 2))
        for p in particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 1
            if p["life"] <= 0:
                particles.remove(p)

        font_large = pygame.font.SysFont(None, 64)
        font_sub = pygame.font.SysFont(None, 24)
        if win:
            msg = font_large.render("YOU ESCAPED!", True, (0, 255, 0))
            sub = font_sub.render("PRESS ESC TO QUIT", True, (200, 200, 200))
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 40))
            screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 + 20))
        else:
            msg = font_large.render("YOU DIED", True, (255, 10, 10))
            sub = font_sub.render("PRESS ESC TO QUIT", True, (200, 200, 200))
            screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, HEIGHT // 2 - 40))
            screen.blit(sub, (WIDTH // 2 - sub.get_width() // 2, HEIGHT // 2 + 20))
        
        keys = pygame.key.get_pressed()
        if keys[pygame.K_ESCAPE]:
            running = False

    pygame.display.flip()
    clock.tick(60)

pygame.quit()