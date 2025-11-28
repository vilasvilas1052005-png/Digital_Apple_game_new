import math
import random
import sys
from pathlib import Path

import pygame
from pygame.math import Vector2

from model import AppleQualityClassifier

WIDTH, HEIGHT = 960, 600
FPS = 60
GROUND_Y = HEIGHT - 100
BOY_X = 150  # Fixed position on left side
SCROLL_SPEED = 180  # Background and apples scroll speed (slower)
BACKGROUND_IMAGE = Path("assets") / "jungle_bg.png"


def load_classifier():
    model_path = Path("models") / "apple_cnn.pth"
    if not model_path.exists():
        raise FileNotFoundError(
            f"Missing model file at {model_path}. Run `python train_model.py` first."
        )
    return AppleQualityClassifier(str(model_path))


class JungleBackground:
    """Realistic auto-scrolling forest background."""

    def __init__(self, width, height, scroll_speed):
        self.width = width
        self.height = height
        self.scroll_speed = scroll_speed
        self.offset = 0.0
        self.image = self._load_image(width, height)

    def _load_image(self, width, height):
        if BACKGROUND_IMAGE.exists():
            image = pygame.image.load(str(BACKGROUND_IMAGE)).convert()
            ratio = height / image.get_height()
            scaled_width = int(image.get_width() * ratio)
            scaled_height = height
            return pygame.transform.smoothscale(image, (scaled_width, scaled_height))
        
        # Create realistic forest background
        forest_width = width * 3
        forest = pygame.Surface((forest_width, height))
        
        # Sky gradient (light blue to light green)
        for y in range(height // 2):
            t = y / (height // 2)
            r = int(135 + (144 - 135) * t)
            g = int(206 + (238 - 206) * t)
            b = int(250 + (144 - 250) * t)
            pygame.draw.line(forest, (r, g, b), (0, y), (forest_width, y))
        
        # Forest canopy (darker green)
        canopy_height = height // 2
        for y in range(canopy_height, height):
            t = (y - canopy_height) / (height - canopy_height)
            r = int(34 + (20 - 34) * t)
            g = int(139 + (80 - 139) * t)
            b = int(34 + (20 - 34) * t)
            pygame.draw.line(forest, (r, g, b), (0, y), (forest_width, y))
        
        # Draw trees in layers (background to foreground)
        # Background trees (distant, darker)
        for i in range(20):
            x = (i * forest_width // 20) + random.randint(-100, 100)
            tree_w = random.randint(30, 60)
            tree_h = random.randint(80, 150)
            tree_y = GROUND_Y - tree_h
            # Trunk
            trunk_w = tree_w // 3
            pygame.draw.rect(forest, (45, 25, 15), (x + tree_w//2 - trunk_w//2, tree_y, trunk_w, tree_h))
            # Foliage
            for j in range(3):
                foliage_y = tree_y + j * (tree_h // 4)
                foliage_r = tree_w // 2 + random.randint(-10, 10)
                pygame.draw.circle(forest, (20, 60, 20), (x + tree_w//2, foliage_y), foliage_r)
        
        # Mid-ground trees
        for i in range(15):
            x = (i * forest_width // 15) + random.randint(-80, 80)
            tree_w = random.randint(50, 90)
            tree_h = random.randint(120, 200)
            tree_y = GROUND_Y - tree_h
            # Trunk
            trunk_w = tree_w // 2
            pygame.draw.rect(forest, (60, 35, 20), (x + tree_w//2 - trunk_w//2, tree_y, trunk_w, tree_h))
            # Foliage layers
            for j in range(4):
                foliage_y = tree_y + j * (tree_h // 5)
                foliage_r = tree_w // 2 + random.randint(-15, 15)
                pygame.draw.circle(forest, (25, 80, 25), (x + tree_w//2, foliage_y), foliage_r)
        
        # Ground layer
        ground_rect = pygame.Rect(0, GROUND_Y, forest_width, height - GROUND_Y)
        pygame.draw.rect(forest, (34, 139, 34), ground_rect)
        # Grass details
        for i in range(200):
            x = random.randint(0, forest_width)
            grass_h = random.randint(5, 15)
            pygame.draw.line(forest, (40, 150, 40), (x, GROUND_Y), (x, GROUND_Y - grass_h), 2)
        
        return forest

    def update(self, dt, game_speed):
        img_width = self.image.get_width()
        if img_width <= 0:
            return
        self.offset = (self.offset + game_speed * dt) % img_width

    def draw(self, target):
        img_width = self.image.get_width()
        x = -self.offset
        while x < self.width:
            target.blit(self.image, (x, 0))
            x += img_width


class Basket(pygame.sprite.Sprite):
    """Basket to show collected apples."""
    
    def __init__(self, x, y):
        super().__init__()
        self.image = self._create_sprite()
        self.rect = self.image.get_rect(center=(x, y))
        self.apple_count = 0
        
    def _create_sprite(self):
        surf = pygame.Surface((80, 60), pygame.SRCALPHA)
        # Basket body
        pygame.draw.ellipse(surf, (139, 90, 43), (10, 20, 60, 35))
        pygame.draw.ellipse(surf, (101, 67, 33), (10, 20, 60, 35), 3)
        # Basket handle
        pygame.draw.arc(surf, (101, 67, 33), (25, 5, 30, 25), 0, math.pi, 4)
        return surf
    
    def update_apples(self, count):
        """Update the visual representation of apples in basket."""
        self.apple_count = count
        self.image = self._create_sprite()
        # Draw apples in basket
        for i in range(min(count, 5)):  # Show up to 5 apples
            x = 20 + (i % 3) * 20
            y = 30 + (i // 3) * 15
            pygame.draw.circle(self.image, (220, 40, 40), (x, y), 8)
            pygame.draw.circle(self.image, (150, 0, 0), (x, y), 8, 1)


class AppleCollectEffect(pygame.sprite.Sprite):
    """Animation effect for apple flying to basket."""
    
    def __init__(self, start_pos, end_pos, apple_image):
        super().__init__()
        self.start_pos = Vector2(start_pos)
        self.end_pos = Vector2(end_pos)
        self.pos = Vector2(start_pos)
        self.image = apple_image
        self.rect = self.image.get_rect(center=start_pos)
        self.duration = 0.5  # seconds
        self.elapsed = 0.0
        
    def update(self, dt):
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.kill()
            return
        
        # Parabolic path to basket
        t = self.elapsed / self.duration
        self.pos = self.start_pos.lerp(self.end_pos, t)
        # Add arc (jump up then down)
        arc_height = 50 * math.sin(t * math.pi)
        self.rect.center = (int(self.pos.x), int(self.pos.y - arc_height))


class Boy(pygame.sprite.Sprite):
    """Boy character fixed on left side, can jump."""

    def __init__(self):
        super().__init__()
        self.animation_state = "idle"  # idle, picking, jumping
        self.animation_timer = 0.0
        self.image = self._create_sprite("idle")
        self.rect = self.image.get_rect(midbottom=(BOY_X, GROUND_Y))
        self.vel_y = 0.0
        self.on_ground = True
        self.jump_power = -820  # taller jump so he can clearly clear rotten apples
        self.gravity = 1750     # slightly stronger gravity to keep arc snappy

    def _create_sprite(self, state="idle"):
        """Draw a beautiful animated character - clean, modern, appealing design."""
        width, height = 100, 160
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        cx = width // 2

        # Head - smooth, round, appealing
        pygame.draw.circle(surf, (255, 220, 177), (cx, 35), 30)
        
        # Hair - stylish, modern cut
        hair_points = [
            (cx - 25, 20), (cx - 15, 5), (cx - 5, 0), (cx + 5, 0),
            (cx + 15, 5), (cx + 25, 20), (cx + 28, 35), (cx - 28, 35)
        ]
        pygame.draw.polygon(surf, (60, 40, 25), hair_points)
        pygame.draw.ellipse(surf, (60, 40, 25), (cx - 30, 0, 60, 40))
        
        # Eyes - large, expressive
        if state == "picking":
            # Eyes look happy/excited when picking
            pygame.draw.ellipse(surf, (255, 255, 255), (cx - 18, 28, 12, 16))
            pygame.draw.ellipse(surf, (255, 255, 255), (cx + 6, 28, 12, 16))
            pygame.draw.circle(surf, (50, 120, 200), (cx - 12, 36), 6)  # Slightly larger
            pygame.draw.circle(surf, (50, 120, 200), (cx + 12, 36), 6)
            pygame.draw.circle(surf, (20, 20, 20), (cx - 12, 36), 3)
            pygame.draw.circle(surf, (20, 20, 20), (cx + 12, 36), 3)
            pygame.draw.circle(surf, (255, 255, 255), (cx - 11, 35), 1)
            pygame.draw.circle(surf, (255, 255, 255), (cx + 13, 35), 1)
            # Bigger smile
            pygame.draw.arc(surf, (200, 100, 100), (cx - 12, 48, 24, 14), 0, math.pi, 3)
        else:
            pygame.draw.ellipse(surf, (255, 255, 255), (cx - 18, 28, 12, 16))
            pygame.draw.ellipse(surf, (255, 255, 255), (cx + 6, 28, 12, 16))
            pygame.draw.circle(surf, (50, 120, 200), (cx - 12, 36), 5)
            pygame.draw.circle(surf, (50, 120, 200), (cx + 12, 36), 5)
            pygame.draw.circle(surf, (20, 20, 20), (cx - 12, 36), 3)
            pygame.draw.circle(surf, (20, 20, 20), (cx + 12, 36), 3)
            pygame.draw.circle(surf, (255, 255, 255), (cx - 11, 35), 1)
            pygame.draw.circle(surf, (255, 255, 255), (cx + 13, 35), 1)
            # Normal smile
            pygame.draw.arc(surf, (200, 100, 100), (cx - 10, 48, 20, 12), 0, math.pi, 2)
        
        # Eyebrows
        pygame.draw.arc(surf, (40, 25, 15), (cx - 20, 24, 14, 8), math.pi / 6, math.pi - math.pi / 6, 2)
        pygame.draw.arc(surf, (40, 25, 15), (cx + 6, 24, 14, 8), math.pi / 6, math.pi - math.pi / 6, 2)
        
        # Nose - subtle
        pygame.draw.ellipse(surf, (240, 200, 160), (cx - 3, 42, 6, 8))
        
        # Cheeks - subtle blush
        pygame.draw.circle(surf, (255, 180, 180, 100), (cx - 20, 45), 6)
        pygame.draw.circle(surf, (255, 180, 180, 100), (cx + 20, 45), 6)
        
        # Body - modern t-shirt
        pygame.draw.rect(surf, (70, 130, 200), (cx - 28, 65, 56, 50), border_radius=12)
        # Collar/shirt detail
        pygame.draw.arc(surf, (50, 110, 180), (cx - 28, 65, 56, 20), 0, math.pi, 2)
        
        # Arms - different positions based on state
        if state == "picking":
            # Right arm extended forward to pick apple
            pygame.draw.ellipse(surf, (255, 220, 177), (cx - 40, 70, 18, 35))  # Left arm normal
            # Right arm extended
            arm_angle = -math.pi / 4  # 45 degrees forward
            arm_end_x = cx + 22 + int(25 * math.cos(arm_angle))
            arm_end_y = 70 + int(25 * math.sin(arm_angle))
            pygame.draw.line(surf, (255, 220, 177), (cx + 22, 70), (arm_end_x, arm_end_y), 18)
            pygame.draw.circle(surf, (255, 220, 177), (arm_end_x, arm_end_y), 8)  # Hand reaching
        elif state == "jumping":
            # Arms up when jumping
            pygame.draw.ellipse(surf, (255, 220, 177), (cx - 40, 60, 18, 30))
            pygame.draw.ellipse(surf, (255, 220, 177), (cx + 22, 60, 18, 30))
            pygame.draw.circle(surf, (255, 220, 177), (cx - 32, 85), 8)
            pygame.draw.circle(surf, (255, 220, 177), (cx + 32, 85), 8)
        else:
            # Normal arms
            pygame.draw.ellipse(surf, (255, 220, 177), (cx - 40, 70, 18, 35))
            pygame.draw.ellipse(surf, (255, 220, 177), (cx + 22, 70, 18, 35))
            pygame.draw.circle(surf, (255, 220, 177), (cx - 32, 100), 8)
            pygame.draw.circle(surf, (255, 220, 177), (cx + 32, 100), 8)
        
        # Pants
        pygame.draw.rect(surf, (50, 50, 50), (cx - 20, 115, 18, 40), border_radius=4)
        pygame.draw.rect(surf, (50, 50, 50), (cx + 2, 115, 18, 40), border_radius=4)
        
        # Shoes
        pygame.draw.ellipse(surf, (30, 30, 30), (cx - 24, 150, 20, 10))
        pygame.draw.ellipse(surf, (30, 30, 30), (cx + 4, 150, 20, 10))
        
        return surf

    def update(self, dt):
        keys = pygame.key.get_pressed()
        
        # Update animation timer
        self.animation_timer += dt
        
        # Jump
        if (keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]) and self.on_ground:
            self.vel_y = self.jump_power
            self.on_ground = False
            self.animation_state = "jumping"
            self.animation_timer = 0.0

        # Apply gravity
        self.vel_y += self.gravity * dt
        self.rect.y += self.vel_y * dt

        # Ground collision
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.vel_y = 0.0
            self.on_ground = True
            if self.animation_state == "jumping":
                self.animation_state = "idle"
                self.animation_timer = 0.0
        
        # Update animation state
        if self.animation_state == "picking" and self.animation_timer > 0.3:
            self.animation_state = "idle"
            self.animation_timer = 0.0
        elif self.animation_state == "jumping" and self.on_ground:
            self.animation_state = "idle"
            self.animation_timer = 0.0
        
        # Update sprite based on animation state
        self.image = self._create_sprite(self.animation_state)
    
    def play_pick_animation(self):
        """Trigger picking animation."""
        self.animation_state = "picking"
        self.animation_timer = 0.0


class Apple(pygame.sprite.Sprite):
    """Apples that scroll from right to left."""

    def __init__(self, x_position):
        super().__init__()
        self.quality = "good" if random.random() < 0.65 else "damaged"
        self.base_image = self._create_surface(self.quality)
        self.image = self.base_image
        self.rect = self.image.get_rect(midbottom=(x_position, GROUND_Y))
        self.angle = 0.0
        self.spin = random.choice([-1, 1]) * random.uniform(15, 35)
        self.pulse = random.uniform(0.9, 1.05)

    def _create_surface(self, quality):
        radius = random.randint(24, 34)
        surf = pygame.Surface((radius * 2 + 20, radius * 2 + 30), pygame.SRCALPHA)  # Larger surface for rotten
        center = (surf.get_width() // 2, surf.get_height() // 2)
        base_red = 220 + random.randint(-10, 10)
        
        if quality == "damaged":
            # Rotten apple - dark green base with patches, looks like actual apple
            # Base apple shape (slightly oval to look more realistic)
            base_color = (40, 80, 30)  # Dark green
            pygame.draw.ellipse(surf, base_color, (center[0] - radius, center[1] - radius, radius * 2, radius * 2.2))
            
            # Darker green patches (rotten spots)
            for _ in range(random.randint(4, 6)):
                patch_radius = random.randint(radius // 3, radius // 2)
                patch_center = (
                    center[0] + random.randint(-radius // 2, radius // 2),
                    center[1] + random.randint(-radius // 2, radius // 2),
                )
                # Dark green/brown patches
                pygame.draw.ellipse(surf, (25, 50, 15), 
                                  (patch_center[0] - patch_radius, patch_center[1] - patch_radius, 
                                   patch_radius * 2, patch_radius * 2.2))
                pygame.draw.ellipse(surf, (15, 30, 10), 
                                  (patch_center[0] - patch_radius, patch_center[1] - patch_radius, 
                                   patch_radius * 2, patch_radius * 2.2), 2)
            
            # Add some lighter green areas for texture
            for _ in range(2):
                light_spot = (
                    center[0] + random.randint(-radius // 3, radius // 3),
                    center[1] + random.randint(-radius // 3, radius // 3),
                )
                pygame.draw.circle(surf, (60, 100, 40), light_spot, radius // 4)
            
            # Highlight to make it look 3D like a real apple
            highlight = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
            pygame.draw.ellipse(highlight, (80, 120, 60, 100), 
                              (center[0] - radius // 2, center[1] - radius, radius, radius // 2))
            surf.blit(highlight, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            
            # Stem (brown)
            stem_top = (center[0], center[1] - radius - 5)
            stem_bottom = (center[0], center[1] - radius)
            pygame.draw.line(surf, (80, 50, 20), stem_top, stem_bottom, 3)
            pygame.draw.circle(surf, (80, 50, 20), stem_top, 2)
            
            # Wilted leaf (brown/yellow)
            leaf_start = (center[0] + 3, center[1] - radius - 3)
            leaf_end = (leaf_start[0] + 8, leaf_start[1] - 10)
            pygame.draw.line(surf, (100, 80, 30), leaf_start, leaf_end, 3)
            pygame.draw.ellipse(surf, (100, 80, 30), (leaf_end[0] - 4, leaf_end[1] - 3, 6, 4))
            
            # Outline to make it stand out
            pygame.draw.ellipse(surf, (20, 50, 15), 
                              (center[0] - radius, center[1] - radius, radius * 2, radius * 2.2), 2)
        else:
            # Good apple - bright red
            color = (base_red, 40 + random.randint(-5, 5), 40 + random.randint(-5, 5))
            pygame.draw.circle(surf, color, center, radius)
            pygame.draw.circle(surf, (150, 0, 0), center, radius, 3)
            # Fresh green leaf
            leaf_start = (center[0], center[1] - radius)
            leaf_end = (leaf_start[0] + 12, leaf_start[1] - 15)
            pygame.draw.line(surf, (40, 120, 40), leaf_start, leaf_end, 4)
            pygame.draw.circle(surf, (40, 120, 40), leaf_end, 6)
        
        return surf

    def update(self, dt, scroll_speed):
        # Scroll from right to left
        self.rect.x -= scroll_speed * dt
        # Rotate and pulse animation
        self.angle = (self.angle + self.spin * dt) % 360
        pulse = 1 + (self.pulse - 1) * math.sin(pygame.time.get_ticks() * 0.005)
        self.image = pygame.transform.rotozoom(self.base_image, self.angle, pulse)
        self.rect = self.image.get_rect(center=self.rect.center)
        # Remove if off-screen
        if self.rect.right < -50:
            self.kill()

    def capture_surface(self):
        return self.base_image.copy()


class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Jungle Apple Runner")
        self.clock = pygame.time.Clock()
        self.background = JungleBackground(WIDTH, HEIGHT, SCROLL_SPEED)
        self.all_sprites = pygame.sprite.Group()
        self.apples = pygame.sprite.Group()
        self.effects = pygame.sprite.Group()  # For apple collection animations
        self.font_large = pygame.font.SysFont("arial", 48, bold=True)
        self.font_medium = pygame.font.SysFont("arial", 28)
        self.font_small = pygame.font.SysFont("arial", 20)
        self.classifier = load_classifier()
        self.state = "playing"
        self.reset()

    def reset(self):
        self.all_sprites.empty()
        self.apples.empty()
        self.effects.empty()
        self.boy = Boy()
        self.all_sprites.add(self.boy)
        # Create basket in top-left corner
        self.basket = Basket(60, 50)
        self.all_sprites.add(self.basket)
        self.total = 0
        self.good = 0
        self.points = 0
        self.elapsed = 0.0
        self.next_apple_spawn = 0.0
        self.game_speed = SCROLL_SPEED
        self.state = "playing"

    def spawn_apple(self):
        apple = Apple(WIDTH + 50)
        self.apples.add(apple)
        self.all_sprites.add(apple)

    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if self.state == "ended" and event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.reset()
                    elif event.key in (pygame.K_ESCAPE, pygame.K_q):
                        running = False

            if self.state == "playing":
                self.elapsed += dt
                # Spawn apples at intervals
                if self.elapsed >= self.next_apple_spawn:
                    self.spawn_apple()
                    # Random interval between apples
                    self.next_apple_spawn = self.elapsed + random.uniform(1.2, 2.5)
                    # Gradually increase game speed (much slower increase)
                    self.game_speed = SCROLL_SPEED + (self.elapsed * 5)

                self.boy.update(dt)
                # Update apples with scroll speed
                for apple in self.apples:
                    apple.update(dt, self.game_speed)
                # Update effects
                self.effects.update(dt)
                self.background.update(dt, self.game_speed)
                self.handle_collisions()
                # Update basket display
                self.basket.update_apples(self.good)

            self.draw()
        pygame.quit()
        sys.exit()

    def handle_collisions(self):
        # Check if boy collides with any apple
        for apple in list(self.apples):
            if self.boy.rect.colliderect(apple.rect):
                is_rotten = apple.quality == "damaged"
                apple_pos = apple.rect.center
                apple_image = apple.base_image.copy()

                if not is_rotten:
                    # Good apple - collect it with animation
                    self.boy.play_pick_animation()
                    # Create flying apple effect to basket
                    effect = AppleCollectEffect(
                        apple_pos,
                        self.basket.rect.center,
                        apple_image
                    )
                    self.effects.add(effect)
                    self.all_sprites.add(effect)
                    
                    apple.kill()
                    self.total += 1
                    self.good += 1
                    self.points += 10
                else:
                    # Rotten apple
                    apple.kill()
                    # Rotten apple only ends run if the boy is on the ground (not jumping)
                    boy_on_ground = self.boy.on_ground and self.boy.rect.bottom >= GROUND_Y - 5

                    if boy_on_ground:
                        self.state = "ended"
                        return
                    # If he is airborne, he successfully avoided it (like jumping over a cactus)

    def draw(self):
        # Draw background
        self.background.draw(self.screen)
        # Draw ground line
        pygame.draw.line(self.screen, (139, 69, 19), (0, GROUND_Y), (WIDTH, GROUND_Y), 3)
        # Draw sprites
        self.all_sprites.draw(self.screen)

        if self.state == "playing":
            # Score display (top right, like dinosaur game)
            score_text = self.font_medium.render(str(self.points), True, (100, 100, 100))
            score_rect = score_text.get_rect(topright=(WIDTH - 20, 20))
            self.screen.blit(score_text, score_rect)
            
            # Instructions (small, bottom)
            inst_text = self.font_small.render("Press SPACE to jump over rotten apples!", True, (200, 200, 200))
            inst_rect = inst_text.get_rect(center=(WIDTH // 2, HEIGHT - 30))
            self.screen.blit(inst_text, inst_rect)

        if self.state == "ended":
            self.draw_game_over()

        pygame.display.flip()

    def draw_game_over(self):
        # Semi-transparent overlay (exactly like dinosaur game)
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((255, 255, 255, 200))
        self.screen.blit(overlay, (0, 0))

        # GAME OVER text (centered, large, dark gray like dinosaur game)
        game_over_text = self.font_large.render("GAME OVER", True, (83, 83, 83))
        game_over_rect = game_over_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60))
        self.screen.blit(game_over_text, game_over_rect)

        # Score display (centered, below GAME OVER, like dinosaur game)
        score_text = self.font_medium.render(f"SCORE: {self.points}", True, (83, 83, 83))
        score_rect = score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20))
        self.screen.blit(score_text, score_rect)

        # Restart instruction (centered, at bottom, like dinosaur game)
        restart_text = self.font_medium.render("Press SPACE to restart", True, (83, 83, 83))
        restart_rect = restart_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 80))
        self.screen.blit(restart_text, restart_rect)


if __name__ == "__main__":
    Game().run()
