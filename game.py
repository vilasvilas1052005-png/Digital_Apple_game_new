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
BOY_SPEED = 300  # Walking speed left/right
APPLE_FALL_SPEED = 200  # Speed at which apples fall
APPLE_SPAWN_RATE = 1.5  # Seconds between apple spawns
LIFELINES = 3  # Number of lifelines
BACKGROUND_IMAGE = Path("assets") / "jungle_bg.png"


def load_classifier():
    model_path = Path("models") / "apple_cnn.pth"
    if not model_path.exists():
        raise FileNotFoundError(
            f"Missing model file at {model_path}. Run `python train_model.py` first."
        )
    return AppleQualityClassifier(str(model_path))


class ForestBackground:
    """Static forest background."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.image = self._load_image(width, height)

    def _load_image(self, width, height):
        if BACKGROUND_IMAGE.exists():
            image = pygame.image.load(str(BACKGROUND_IMAGE)).convert()
            return pygame.transform.smoothscale(image, (width, height))
        
        # Create realistic forest background
        forest = pygame.Surface((width, height))
        
        # Sky gradient
        for y in range(height // 2):
            t = y / (height // 2)
            r = int(135 + (144 - 135) * t)
            g = int(206 + (238 - 206) * t)
            b = int(250 + (144 - 250) * t)
            pygame.draw.line(forest, (r, g, b), (0, y), (width, y))
        
        # Forest canopy
        canopy_height = height // 2
        for y in range(canopy_height, height):
            t = (y - canopy_height) / (height - canopy_height)
            r = int(34 + (20 - 34) * t)
            g = int(139 + (80 - 139) * t)
            b = int(34 + (20 - 34) * t)
            pygame.draw.line(forest, (r, g, b), (0, y), (width, y))
        
        # Draw trees
        for i in range(15):
            x = (i * width // 15) + random.randint(-50, 50)
            tree_w = random.randint(50, 90)
            tree_h = random.randint(120, 200)
            tree_y = GROUND_Y - tree_h
            # Trunk
            trunk_w = tree_w // 2
            pygame.draw.rect(forest, (60, 35, 20), (x + tree_w//2 - trunk_w//2, tree_y, trunk_w, tree_h))
            # Foliage
            for j in range(4):
                foliage_y = tree_y + j * (tree_h // 5)
                foliage_r = tree_w // 2 + random.randint(-15, 15)
                pygame.draw.circle(forest, (25, 80, 25), (x + tree_w//2, foliage_y), foliage_r)
        
        # Ground layer
        ground_rect = pygame.Rect(0, GROUND_Y, width, height - GROUND_Y)
        pygame.draw.rect(forest, (34, 139, 34), ground_rect)
        # Grass details
        for i in range(150):
            x = random.randint(0, width)
            grass_h = random.randint(5, 15)
            pygame.draw.line(forest, (40, 150, 40), (x, GROUND_Y), (x, GROUND_Y - grass_h), 2)
        
        return forest

    def draw(self, target):
        target.blit(self.image, (0, 0))


class Basket(pygame.sprite.Sprite):
    """Basket on left side."""
    
    def __init__(self, x, y):
        super().__init__()
        self.apple_count = 0
        self.image = self._create_sprite()
        self.rect = self.image.get_rect(center=(x, y))
        
    def _create_sprite(self):
        surf = pygame.Surface((100, 80), pygame.SRCALPHA)
        # Basket body
        pygame.draw.ellipse(surf, (139, 90, 43), (10, 25, 80, 50))
        pygame.draw.ellipse(surf, (101, 67, 33), (10, 25, 80, 50), 4)
        # Basket handle
        pygame.draw.arc(surf, (101, 67, 33), (30, 5, 40, 30), 0, math.pi, 5)
        # Label
        font = pygame.font.SysFont("arial", 16, bold=True)
        label = font.render("BASKET", True, (255, 255, 255))
        label_rect = label.get_rect(center=(50, 15))
        surf.blit(label, label_rect)
        return surf
    
    def update_apples(self, count):
        """Update the visual representation of apples in basket."""
        self.apple_count = count
        self.image = self._create_sprite()
        # Draw apples in basket
        for i in range(min(count, 6)):  # Show up to 6 apples
            x = 25 + (i % 3) * 25
            y = 40 + (i // 3) * 20
            pygame.draw.circle(self.image, (220, 40, 40), (x, y), 10)
            pygame.draw.circle(self.image, (150, 0, 0), (x, y), 10, 2)


class Dustbin(pygame.sprite.Sprite):
    """Dustbin on right side."""
    
    def __init__(self, x, y):
        super().__init__()
        self.apple_count = 0
        self.image = self._create_sprite()
        self.rect = self.image.get_rect(center=(x, y))
        
    def _create_sprite(self):
        surf = pygame.Surface((100, 100), pygame.SRCALPHA)
        # Dustbin body
        pygame.draw.rect(surf, (100, 100, 100), (20, 30, 60, 70), border_radius=5)
        pygame.draw.rect(surf, (80, 80, 80), (20, 30, 60, 70), 3, border_radius=5)
        # Lid
        pygame.draw.ellipse(surf, (120, 120, 120), (15, 20, 70, 20))
        pygame.draw.ellipse(surf, (100, 100, 100), (15, 20, 70, 20), 3)
        # Label
        font = pygame.font.SysFont("arial", 16, bold=True)
        label = font.render("DUSTBIN", True, (255, 255, 255))
        label_rect = label.get_rect(center=(50, 85))
        surf.blit(label, label_rect)
        return surf
    
    def update_apples(self, count):
        """Update the visual representation of apples in dustbin."""
        self.apple_count = count
        self.image = self._create_sprite()
        # Draw rotten apples (brown) in dustbin
        for i in range(min(count, 6)):  # Show up to 6 apples
            x = 25 + (i % 3) * 25
            y = 45 + (i // 3) * 18
            # Brown/rotten apple color
            pygame.draw.circle(self.image, (139, 90, 43), (x, y), 10)
            pygame.draw.circle(self.image, (100, 60, 30), (x, y), 10, 2)
            # Add some patches to show it's rotten
            pygame.draw.circle(self.image, (100, 60, 30), (x - 3, y - 3), 4)
            pygame.draw.circle(self.image, (80, 50, 25), (x + 3, y + 3), 3)


class AppleFlyEffect(pygame.sprite.Sprite):
    """Animation for apple flying to basket/dustbin."""
    
    def __init__(self, start_pos, end_pos, apple_image):
        super().__init__()
        self.start_pos = Vector2(start_pos)
        self.end_pos = Vector2(end_pos)
        self.pos = Vector2(start_pos)
        self.image = apple_image
        self.rect = self.image.get_rect(center=start_pos)
        self.duration = 0.6
        self.elapsed = 0.0
        
    def update(self, dt):
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.kill()
            return
        
        # Parabolic path
        t = self.elapsed / self.duration
        self.pos = self.start_pos.lerp(self.end_pos, t)
        arc_height = 60 * math.sin(t * math.pi)
        self.rect.center = (int(self.pos.x), int(self.pos.y - arc_height))


class Boy(pygame.sprite.Sprite):
    """Boy character that can move left/right and pick apples."""

    def __init__(self):
        super().__init__()
        self.direction = 1  # 1 for right, -1 for left
        self.animation_state = "idle"  # idle, walking, picking
        self.animation_timer = 0.0
        self.picking_timer = 0.0
        self.image = self._create_sprite("idle")
        self.rect = self.image.get_rect(midbottom=(WIDTH // 2, GROUND_Y))
        self.speed = BOY_SPEED

    def _create_sprite(self, state="idle"):
        """Draw the boy character."""
        width, height = 100, 160
        surf = pygame.Surface((width, height), pygame.SRCALPHA)
        cx = width // 2

        # Head
        pygame.draw.circle(surf, (255, 220, 177), (cx, 35), 30)
        
        # Hair
        hair_points = [
            (cx - 25, 20), (cx - 15, 5), (cx - 5, 0), (cx + 5, 0),
            (cx + 15, 5), (cx + 25, 20), (cx + 28, 35), (cx - 28, 35)
        ]
        pygame.draw.polygon(surf, (60, 40, 25), hair_points)
        pygame.draw.ellipse(surf, (60, 40, 25), (cx - 30, 0, 60, 40))
        
        # Eyes
        pygame.draw.ellipse(surf, (255, 255, 255), (cx - 18, 28, 12, 16))
        pygame.draw.ellipse(surf, (255, 255, 255), (cx + 6, 28, 12, 16))
        pygame.draw.circle(surf, (50, 120, 200), (cx - 12, 36), 5)
        pygame.draw.circle(surf, (50, 120, 200), (cx + 12, 36), 5)
        pygame.draw.circle(surf, (20, 20, 20), (cx - 12, 36), 3)
        pygame.draw.circle(surf, (20, 20, 20), (cx + 12, 36), 3)
        pygame.draw.arc(surf, (200, 100, 100), (cx - 10, 48, 20, 12), 0, math.pi, 2)
        
        # Eyebrows
        pygame.draw.arc(surf, (40, 25, 15), (cx - 20, 24, 14, 8), math.pi / 6, math.pi - math.pi / 6, 2)
        pygame.draw.arc(surf, (40, 25, 15), (cx + 6, 24, 14, 8), math.pi / 6, math.pi - math.pi / 6, 2)
        
        # Nose
        pygame.draw.ellipse(surf, (240, 200, 160), (cx - 3, 42, 6, 8))
        
        # Cheeks
        pygame.draw.circle(surf, (255, 180, 180, 100), (cx - 20, 45), 6)
        pygame.draw.circle(surf, (255, 180, 180, 100), (cx + 20, 45), 6)
        
        # Body
        pygame.draw.rect(surf, (70, 130, 200), (cx - 28, 65, 56, 50), border_radius=12)
        pygame.draw.arc(surf, (50, 110, 180), (cx - 28, 65, 56, 20), 0, math.pi, 2)
        
        # Arms - different based on state
        if state == "picking":
            # Right arm extended forward to pick
            arm_angle = -math.pi / 4 if self.direction == 1 else math.pi / 4
            arm_start_x = cx + (22 if self.direction == 1 else -22)
            arm_end_x = arm_start_x + int(35 * math.cos(arm_angle)) * self.direction
            arm_end_y = 70 + int(35 * abs(math.sin(arm_angle)))
            # Left arm normal
            pygame.draw.ellipse(surf, (255, 220, 177), (cx - 40, 70, 18, 35))
            # Right arm extended
            pygame.draw.line(surf, (255, 220, 177), (arm_start_x, 70), (arm_end_x, arm_end_y), 18)
            pygame.draw.circle(surf, (255, 220, 177), (arm_end_x, arm_end_y), 8)  # Hand
        elif state == "walking":
            # Animate arms swinging
            arm_offset = int(5 * math.sin(self.animation_timer * 10))
            pygame.draw.ellipse(surf, (255, 220, 177), (cx - 40, 70 + arm_offset, 18, 35))
            pygame.draw.ellipse(surf, (255, 220, 177), (cx + 22, 70 - arm_offset, 18, 35))
            pygame.draw.circle(surf, (255, 220, 177), (cx - 32, 100 + arm_offset), 8)
            pygame.draw.circle(surf, (255, 220, 177), (cx + 32, 100 - arm_offset), 8)
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
        
        # Flip if facing left
        if self.direction == -1:
            surf = pygame.transform.flip(surf, True, False)
        
        return surf

    def update(self, dt):
        """Update boy position and animation - ONLY when keys are pressed."""
        keys = pygame.key.get_pressed()
        self.animation_timer += dt
        self.picking_timer += dt
        
        # Reset picking animation after duration
        if self.animation_state == "picking" and self.picking_timer > 0.4:
            self.animation_state = "idle"
            self.picking_timer = 0.0
        
        # Movement - LEFT/RIGHT arrow keys (ONLY when pressed)
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.rect.x -= self.speed * dt
            self.direction = -1
            if self.animation_state != "picking":
                self.animation_state = "walking"
            # Keep boy in screen bounds
            self.rect.x = max(50, min(WIDTH - 50, self.rect.x))
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.rect.x += self.speed * dt
            self.direction = 1
            if self.animation_state != "picking":
                self.animation_state = "walking"
            self.rect.x = max(50, min(WIDTH - 50, self.rect.x))
        else:
            # No movement keys pressed - stay idle (if not picking)
            if self.animation_state == "walking":
                self.animation_state = "idle"
        
        # Update sprite
        self.image = self._create_sprite(self.animation_state)
    
    def play_pick_animation(self):
        """Trigger picking animation."""
        self.animation_state = "picking"
        self.picking_timer = 0.0


class Apple(pygame.sprite.Sprite):
    """Apples falling from the top."""

    def __init__(self, x_position):
        super().__init__()
        self.quality = "good" if random.random() < 0.65 else "damaged"
        self.base_image = self._create_surface(self.quality)
        self.image = self.base_image
        self.rect = self.image.get_rect(center=(x_position, -50))
        self.collected = False
        self.fall_speed = APPLE_FALL_SPEED + random.randint(-30, 30)

    def _create_surface(self, quality):
        radius = random.randint(28, 36)
        surf = pygame.Surface((radius * 2 + 20, radius * 2 + 30), pygame.SRCALPHA)
        center = (surf.get_width() // 2, surf.get_height() // 2)
        base_red = 220 + random.randint(-10, 10)
        
        if quality == "damaged":
            # Bad apple - brown/rotten
            base_color = (139, 90, 43)  # Brown
            pygame.draw.ellipse(surf, base_color, (center[0] - radius, center[1] - radius, radius * 2, radius * 2.2))
            
            # Dark patches
            for _ in range(random.randint(4, 6)):
                patch_radius = random.randint(radius // 3, radius // 2)
                patch_center = (
                    center[0] + random.randint(-radius // 2, radius // 2),
                    center[1] + random.randint(-radius // 2, radius // 2),
                )
                pygame.draw.ellipse(surf, (100, 60, 30), 
                                  (patch_center[0] - patch_radius, patch_center[1] - patch_radius, 
                                   patch_radius * 2, patch_radius * 2.2))
            
            # Stem
            stem_top = (center[0], center[1] - radius - 5)
            stem_bottom = (center[0], center[1] - radius)
            pygame.draw.line(surf, (80, 50, 20), stem_top, stem_bottom, 3)
            
            # Wilted leaf
            leaf_start = (center[0] + 3, center[1] - radius - 3)
            leaf_end = (leaf_start[0] + 8, leaf_start[1] - 10)
            pygame.draw.line(surf, (100, 80, 30), leaf_start, leaf_end, 3)
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
    
    def update(self, dt):
        """Update apple position - make it fall."""
        self.rect.y += self.fall_speed * dt
        # Remove if it falls off screen
        if self.rect.top > HEIGHT:
            self.kill()
    
    def capture_surface(self):
        """Return the apple image for classification."""
        return self.base_image.copy()


class Game:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Forest Apple Collector")
        self.clock = pygame.time.Clock()
        self.background = ForestBackground(WIDTH, HEIGHT)
        self.all_sprites = pygame.sprite.Group()
        self.apples = pygame.sprite.Group()
        self.effects = pygame.sprite.Group()  # For apple flying animations
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
        # Create basket on left
        self.basket = Basket(100, 80)
        self.all_sprites.add(self.basket)
        # No dustbin needed
        
        self.score = 0
        self.good_collected = 0
        self.rotten_collected = 0
        self.lifelines = LIFELINES
        self.elapsed = 0.0
        self.last_apple_spawn = 0.0
        self.state = "playing"

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
                
                # Update boy (movement - ONLY when keys pressed)
                self.boy.update(dt)
                
                # Spawn new apples from top
                if self.elapsed - self.last_apple_spawn >= APPLE_SPAWN_RATE:
                    x = random.randint(100, WIDTH - 100)
                    apple = Apple(x)
                    self.apples.add(apple)
                    self.all_sprites.add(apple)
                    self.last_apple_spawn = self.elapsed
                
                # Update apples (falling)
                self.apples.update(dt)
                
                # Update effects
                self.effects.update(dt)
                
                # Check collisions between boy and apples
                self.handle_collisions()
                
                # Check game end condition
                if self.lifelines <= 0:
                    self.state = "ended"

            self.draw()
        pygame.quit()
        sys.exit()

    def handle_collisions(self):
        """Handle collisions between boy and falling apples."""
        for apple in list(self.apples):
            if apple.collected:
                continue
            
            # Check collision using pygame's collision detection
            if pygame.sprite.collide_rect(self.boy, apple):
                # Play pick animation
                self.boy.play_pick_animation()
                
                # Classify apple using CNN (for visualization/logic if needed)
                # Gameplay rule: whether the apple is good or rotten is decided
                # by how it was spawned, so rotten apples NEVER go to the basket.
                surface = apple.capture_surface()
                label, confidence, _ = self.classifier.classify_surface(surface)
                is_good = (apple.quality == "good")
                
                apple.collected = True
                
                if is_good:
                    # Good apple -> basket
                    self.score += 1
                    self.good_collected += 1
                    self.basket.update_apples(self.good_collected)
                    # Create flying effect to basket
                    effect = AppleFlyEffect(
                        apple.rect.center,
                        self.basket.rect.center,
                        apple.base_image.copy()
                    )
                    self.effects.add(effect)
                    self.all_sprites.add(effect)
                else:
                    # Rotten apple -> lose a lifeline
                    self.lifelines = max(0, self.lifelines - 1)
                    self.rotten_collected += 1
                    # Just remove the apple, no effect needed
                
                apple.kill()
                break

    def draw(self):
        # Draw static background
        self.background.draw(self.screen)
        # Draw ground line
        pygame.draw.line(self.screen, (139, 69, 19), (0, GROUND_Y), (WIDTH, GROUND_Y), 3)
        
        # Draw falling apples
        for apple in self.apples:
            if not apple.collected:
                self.screen.blit(apple.image, apple.rect)
        
        # Draw effects (flying apples)
        for effect in self.effects:
            self.screen.blit(effect.image, effect.rect)
        
        # Draw boy
        self.screen.blit(self.boy.image, self.boy.rect)
        
        # Draw basket only (no dustbin)
        self.screen.blit(self.basket.image, self.basket.rect)

        if self.state == "playing":
            # Score display at top center
            score_text = self.font_medium.render(f"Score: {self.score}", True, (255, 255, 255))
            score_rect = score_text.get_rect(center=(WIDTH // 2, 30))
            # Background for score
            score_bg = pygame.Surface((score_text.get_width() + 20, score_text.get_height() + 10))
            score_bg.fill((0, 0, 0))
            score_bg.set_alpha(180)
            self.screen.blit(score_bg, (score_rect.x - 10, score_rect.y - 5))
            self.screen.blit(score_text, score_rect)
            
            # Lifelines display at top left
            lifeline_text = self.font_medium.render(f"Lives: {self.lifelines}", True, (255, 100, 100))
            lifeline_rect = lifeline_text.get_rect(topleft=(20, 20))
            # Background for lifelines
            lifeline_bg = pygame.Surface((lifeline_text.get_width() + 20, lifeline_text.get_height() + 10))
            lifeline_bg.fill((0, 0, 0))
            lifeline_bg.set_alpha(180)
            self.screen.blit(lifeline_bg, (lifeline_rect.x - 10, lifeline_rect.y - 5))
            self.screen.blit(lifeline_text, lifeline_rect)
            
            # Draw heart icons for lifelines
            heart_size = 20
            for i in range(self.lifelines):
                heart_x = 20 + i * (heart_size + 5)
                heart_y = 60
                # Simple heart shape
                pygame.draw.circle(self.screen, (255, 100, 100), (heart_x, heart_y), heart_size // 2)
                pygame.draw.circle(self.screen, (255, 100, 100), (heart_x + heart_size // 2, heart_y), heart_size // 2)
                points = [
                    (heart_x, heart_y + heart_size // 4),
                    (heart_x - heart_size // 2, heart_y - heart_size // 4),
                    (heart_x + heart_size, heart_y - heart_size // 4),
                    (heart_x + heart_size // 2, heart_y + heart_size // 2)
                ]
                pygame.draw.polygon(self.screen, (255, 100, 100), points)
            
            # Instructions
            inst_text = self.font_small.render("LEFT/RIGHT: Move | Collect Fresh Apples!", True, (200, 200, 200))
            inst_rect = inst_text.get_rect(center=(WIDTH // 2, HEIGHT - 30))
            self.screen.blit(inst_text, inst_rect)

        if self.state == "ended":
            self.draw_game_over()

        pygame.display.flip()

    def draw_game_over(self):
        # Semi-transparent overlay
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))

        # GAME OVER text
        game_over_text = self.font_large.render("GAME OVER", True, (255, 100, 100))
        game_over_rect = game_over_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 120))
        self.screen.blit(game_over_text, game_over_rect)

        # Final score (prominent)
        score_text = self.font_large.render(f"Final Score: {self.score}", True, (255, 255, 255))
        score_rect = score_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40))
        self.screen.blit(score_text, score_rect)
        
        # Stats
        good_text = self.font_medium.render(f"Fresh Apples Collected: {self.good_collected}", True, (100, 255, 100))
        good_rect = good_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20))
        self.screen.blit(good_text, good_rect)
        
        rotten_text = self.font_medium.render(f"Rotten Apples Hit: {self.rotten_collected}", True, (255, 100, 100))
        rotten_rect = rotten_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60))
        self.screen.blit(rotten_text, rotten_rect)

        # Restart instruction
        restart_text = self.font_medium.render("Press SPACE to restart | ESC to quit", True, (200, 200, 200))
        restart_rect = restart_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 120))
        self.screen.blit(restart_text, restart_rect)


if __name__ == "__main__":
    Game().run()
