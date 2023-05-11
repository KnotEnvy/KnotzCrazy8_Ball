import pygame
import pymunk
import pymunk.pygame_util
import math
import pygame.mixer

pygame.init()
pygame.mixer.init()

music_file = 'dungeon.aif'  # Replace with the path to your music file
pygame.mixer.music.load(music_file)
pygame.mixer.music.play()

SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 678
BOTTOM_PANEL = 50
STATE_START_SCREEN = 0
STATE_PLAYING = 1
STATE_GAME_MODE_SELECTION = 2
GAME_MODE_8_BALL = 0
GAME_MODE_SPEED_POOL = 1
GAME_MODE_FREE_GAME = 2
game_state = STATE_START_SCREEN
game_mode = None
blink_time = pygame.time.get_ticks()
blink_interval = 500  # Time in milliseconds for how fast the text blinks
blink_show = True

#game window
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT + BOTTOM_PANEL))
pygame.display.set_caption("KnotzCrazy 8-Ball")

#pymunk space
space = pymunk.Space()
space.damping = 0.9  # air friction- any value between 0 and 1
static_body = space.static_body

### space.gravity = (0, 2000) #how to add gravity to pymuch spaces
draw_options = pymunk.pygame_util.DrawOptions(screen)

#clock
clock = pygame.time.Clock()
FPS = 120

#game variables
lives = 3
dia = 36
pocket_dia = 66
taking_shot = True
force = 0
max_force = 30000
force_direction = 1
game_running = True
cue_ball_sunk = False
powering_up = False
sunk_balls = []
show_instructions = True

#colors
BG =(50,50,50)
RED = (255,0,0)
WHITE = (255,255,255)
BLACK = (0,0,0)
GREY = (128,128,128)
LGREY= (211,211,211)
DGREY = (169,169,169)
DIMGREY = (105,105,105)
GOLD = (255, 215, 0)

#fonts
font = pygame.font.SysFont('lato', 30)
large_font = pygame.font.SysFont('lato', 60)

#load images
cue_image = pygame.image.load('assets/images/cue.png')
table_image = pygame.image.load('assets/images/table.png').convert_alpha()
ball_images= []
for i in range(1, 17):
    ball_image = pygame.image.load(f'assets/images/ball_{i}.png').convert_alpha()
    ball_images.append(ball_image)

#output text
def draw_text(text, font, text_col, x, y):
    img = font.render(text, True, text_col)
    screen.blit(img, (x, y))
def draw_centered_text(text, font, color, surface, x, y):
    text_obj = font.render(text, 1, color)
    text_rect = text_obj.get_rect(center=(x, y))
    surface.blit(text_obj, text_rect)

#create balls
def create_ball(radius, pos):
    body = pymunk.Body()
    body.position = pos
    shape = pymunk.Circle(body, radius)
    shape.mass = 8  #unitless value, but affects weight
    shape.elasticity = 0.8 #effects bounciness
    #use pivot joint for friction
    pivot = pymunk.PivotJoint(static_body, body, (0,0), (0,0))
    pivot.max_bias = 0 #disable joint correction
    pivot.max_force = 600 #control linear friction
    
    space.add(body, shape, pivot)
    return shape

#setup game balls
balls = []
rows = 5
#potting balls
for col in range(5):
    for row in range(rows):
        pos = (250 + (col * (dia +1)), 267 + (row * (dia+1)) + (col * dia / 2))
        new_ball = create_ball(dia / 2, pos)
        balls.append(new_ball)
    rows -= 1

#cueball
pos = (888, SCREEN_HEIGHT / 2)
cue_ball = create_ball(dia /2, pos)
balls.append(cue_ball)

#create pockets
pockets = [
    (53,63),
    (592,48),
    (1134,64),
    (55,616),
    (592,629),
    (1134, 616)
]
cushions = [
    [(88,56), (109,77), (555,77), (564, 56)], #each cushion turned into a pymunk body
    [(621,56),(630,77), (1081,77), (1102,56)],
    [(89,621), (110,600), (556,600), (564,621)],
    [(622,621), (630,600), (1081,600), (1102,621)],
    [(56,96), (77,117), (77,560), (56,581)],
    [(1143,96), (1122,117), (1122,560), (1143,581)]
]
#creating cushions
def create_cushion(poly_dims):
    body = pymunk.Body(body_type= pymunk.Body.STATIC)
    body.position = ((0,0))
    shape = pymunk.Poly(body, poly_dims)
    shape.elasticity = 0.6

    space.add(body, shape)
for c in cushions:
    create_cushion(c)

#create cue
class Cue():
    def __init__(self, pos):
        self.original_image = cue_image
        self.angle = 0
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        self.rect = self.image.get_rect()
        self.rect.center = pos

    def update(self, angle):
        self.angle = angle

    def draw(self, surface):
        self.image = pygame.transform.rotate(self.original_image, self.angle)
        surface.blit(self.image, 
                     (self.rect.centerx - self.image.get_width() / 2,
                     self.rect.centery - self.image.get_height() /2)
                     )
cue = Cue(balls[-1].body.position)

class GameMode:
    def __init__(self, name, pos, size=(200, 100)):
        self.name = name
        self.pos = pos
        self.rect = pygame.Rect(pos, size)
        self.color = WHITE

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, 2)
        draw_text(self.name, font, WHITE, self.pos[0] + 10, self.pos[1] + 10)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self.color = WHITE
            return True
        return False

    def handle_hover(self, mouse_pos):
        if self.rect.collidepoint(mouse_pos):
            self.color = GOLD
        else:
            self.color = WHITE



# Create game modes
game_modes = [
    GameMode('8-Ball', (SCREEN_WIDTH / 2 - 300, SCREEN_HEIGHT / 2)),
    GameMode('Speed Pool', (SCREEN_WIDTH / 2 - 100, SCREEN_HEIGHT / 2)),
    GameMode('Free Game', (SCREEN_WIDTH / 2 + 100, SCREEN_HEIGHT / 2))
]

#create powerbar
power_bar = pygame.Surface((10,20))
power_bar.fill(RED)
# Create power bar box and hash marks
# Create power bar box and hash marks
power_bar_box_thickness = 2  # Thickness of the outline
power_bar_box = pygame.Surface(((max_force / 3000) * 15 + power_bar_box_thickness * 2, power_bar.get_height() + power_bar_box_thickness * 2))
power_bar_box.fill(LGREY)  # Choose a color that stands out
hash_mark_0 = pygame.Surface((2, power_bar_box.get_height() - 10))  # Vertical hash mark
hash_mark_0.fill(GREY)  # Choose a color that contrasts the box
hash_mark_half = pygame.Surface((2, power_bar_box.get_height()-3))  # Vertical hash mark
hash_mark_half.fill(BLACK)  # Choose a color that contrasts the box
hash_mark_full = pygame.Surface((2, power_bar_box.get_height() - 10))  # Vertical hash mark
hash_mark_full.fill(GREY)  # Choose a color that contrasts the box



#game loop
run = True
while run:
    
    clock.tick(FPS)
    space.step(1/FPS)

    #background
    screen.fill(BG)
    if game_state == STATE_START_SCREEN:
        draw_text('KnotzCrazy 8-Ball', large_font, WHITE, SCREEN_WIDTH / 2 -160, SCREEN_HEIGHT / 2 -100)
       # Handle blinking text
        current_time = pygame.time.get_ticks()
        if current_time - blink_time > blink_interval:
            blink_time = current_time
            blink_show = not blink_show
        if blink_show:
            draw_text('Click any button to continue', font, WHITE, SCREEN_WIDTH / 2 - 125, SCREEN_HEIGHT / 2)

        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                game_state = STATE_GAME_MODE_SELECTION  # Go to game mode selection after start screen
                
            if event.type == pygame.QUIT:
                run = False

    elif game_state == STATE_GAME_MODE_SELECTION:
        # Draw "Game Modes" text
        draw_centered_text('Game Modes', large_font, WHITE, screen, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4)

        # Get the current mouse position
        mouse_pos = pygame.mouse.get_pos()

        for mode in game_modes:
            mode.handle_hover(mouse_pos)
            mode.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, mode in enumerate(game_modes):
                    if mode.handle_event(event):
                        game_mode = i
                        game_state = STATE_PLAYING  # Go to playing state after game mode is selected
        pygame.display.flip()
        continue


    #draw table
    if game_state == STATE_PLAYING:
        screen.blit(table_image, (0,0))

        #pygame.display.flip()

        #check if balls sunk
        for i, ball in enumerate(balls):
            for pocket in pockets:
                ball_x_dist = abs(ball.body.position[0] - pocket[0])
                ball_y_dist = abs(ball.body.position[1] - pocket[1])
                ball_dist = math.sqrt((ball_x_dist ** 2) + (ball_y_dist ** 2))
                if ball_dist <= pocket_dia / 2:
                    #check if sunk ball was cueball
                    if i == len(balls) - 1:
                        lives -= 1
                        cue_ball_sunk = True
                        ball.body.position = (-100, -100)
                        ball.body.velocity = (0.0,0.0)
                    else:
                        space.remove(ball.body)
                        balls.remove(ball)
                        sunk_balls.append(ball_images[i])
                        ball_images.pop(i)
        #draw balls
        for i, ball in enumerate(balls):
            screen.blit(ball_images[i], (ball.body.position[0]- ball.radius, ball.body.position[1]- ball.radius))

        #check that balls have stopped
        taking_shot = True
        for ball in balls:
            if int(ball.body.velocity[0]) != 0 or int(ball.body.velocity[1]) != 0:
                taking_shot = False

        #draw cue
        if taking_shot == True and game_running == True:
            if cue_ball_sunk == True:
                #reposition Cue
                balls[-1].body.position = (888, SCREEN_HEIGHT /2)
                cue_ball_sunk = False
            #calculate angle
            mouse_pos = pygame.mouse.get_pos()
            cue.rect.center = balls[-1].body.position
            x_dist = balls[-1].body.position[0]- mouse_pos[0]
            y_dist = -(balls[-1].body.position[1]- mouse_pos[1])
            cue_angle = math.degrees(math.atan2(y_dist, x_dist))
            cue.update(cue_angle)
            cue.draw(screen)
        #powerup cue
        if powering_up == True and game_running == True:
            force += 100 * force_direction
            if force >= max_force or force <= 0:
                force_direction *= -1
            # Draw power bar box
            screen.blit(power_bar_box, 
                        (balls[-1].body.position[0] - 30 - power_bar_box_thickness,
                        balls[-1].body.position[1] + 30 - power_bar_box_thickness))

            # Draw hash marks
            screen.blit(hash_mark_0, 
                        (balls[-1].body.position[0] - 30, 
                        balls[-1].body.position[1] + 30))
            screen.blit(hash_mark_half, 
                        (balls[-1].body.position[0] - 30 + power_bar_box.get_width() / 2, 
                        balls[-1].body.position[1] + 30))
            screen.blit(hash_mark_full, 
                        (balls[-1].body.position[0] - 30 + power_bar_box.get_width() - power_bar_box_thickness, 
                        balls[-1].body.position[1] + 30))
            
            #draw powerbar
            for b in range(math.ceil(force / 3000)):
                # Draw power bar box
                screen.blit(power_bar, 
                            (balls[-1].body.position[0] - 30 + (b * 15), 
                            balls[-1].body.position[1] + 30))

        elif powering_up == False and taking_shot == True:
            x_impulse = math.cos(math.radians(cue_angle))
            y_impulse = math.sin(math.radians(cue_angle))
            balls[-1].body.apply_impulse_at_local_point((force * -x_impulse,force *y_impulse), (0,0))
            force = 0
            force_direction = 1

        #draw panel
        pygame.draw.rect(screen, BG, (0, SCREEN_HEIGHT, SCREEN_WIDTH, BOTTOM_PANEL))
        draw_text('LIVES: ' +str(lives), font, WHITE, SCREEN_WIDTH - 200, SCREEN_HEIGHT + 10)
        #draw sunk balls in bottom panel
        for i, ball in enumerate(sunk_balls):
            screen.blit(ball, (10 + (i * 50), SCREEN_HEIGHT + 10))

        #check for game over
        if lives <= 0:
            draw_text('GAME OVER', large_font, WHITE, SCREEN_WIDTH / 2 -160, SCREEN_HEIGHT / 2 -100)
            game_running = False
        
        #check if all balls sunk
        if len(balls) == 1:
            draw_text('YOU WIN!!', large_font, WHITE, SCREEN_WIDTH / 2 -160, SCREEN_HEIGHT / 2 -100)
            game_running = False


        #draw instructions
        if show_instructions:
            draw_text('Click mouse to shoot', font, WHITE, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN:
                    show_instructions = False
                if event.type == pygame.QUIT:
                    run = False
            pygame.display.update()
            continue
        
        #event handler for game
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN and taking_shot ==  True:
                powering_up = True
            if event.type == pygame.MOUSEBUTTONUP and taking_shot ==  True:
                powering_up = False

            if event.type == pygame.QUIT:
                run = False

            

    #space.debug_draw(draw_options)
    pygame.display.update()

pygame.quit

