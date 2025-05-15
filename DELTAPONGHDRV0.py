import pygame
import sys
import time  # For sound duration, though pyaudio handles it mostly
import math  # For math.copysign and other functions
import random # For random choices

# --- Sound Effects (with PyAudio fallback) ---
try:
    import pyaudio
    import numpy as np  # For generating sound waves
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

# Global PyAudio objects
pa = None
stream = None
SAMPLE_RATE = 44100  # Samples per second
DURATION_PADDLE_HIT = 0.03
DURATION_WALL_HIT = 0.02
DURATION_SCORE = 0.1


def init_audio():
    """Initialize PyAudio and open a stream."""
    global pa, stream, PYAUDIO_AVAILABLE
    if PYAUDIO_AVAILABLE:
        try:
            pa = pyaudio.PyAudio()
            stream = pa.open(format=pyaudio.paFloat32,
                             channels=1,
                             rate=SAMPLE_RATE,
                             output=True)
        except Exception as e:
            print(f"Could not initialize PyAudio: {e}")
            PYAUDIO_AVAILABLE = False


def terminate_audio():
    """Stop and close PyAudio stream."""
    global pa, stream, PYAUDIO_AVAILABLE
    if PYAUDIO_AVAILABLE and stream:
        try:
            if stream.is_active(): # Check if stream is active before stopping
                stream.stop_stream()
            stream.close()
        except Exception as e:
            print(f"Error stopping/closing PyAudio stream: {e}")
            pass # Continue termination
    if PYAUDIO_AVAILABLE and pa:
        try:
            pa.terminate()
        except Exception as e:
            print(f"Error terminating PyAudio: {e}")
            pass
    # Ensure globals are reset
    pa = None
    stream = None


def generate_sound_wave(frequency, duration, amplitude=0.3, wave_type='sine'):
    """Generate raw audio wave data."""
    if not PYAUDIO_AVAILABLE:
        return b''
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    if wave_type == 'square':
        wave = amplitude * np.sign(np.sin(2 * np.pi * frequency * t))
    elif wave_type == 'sawtooth': # Added sawtooth for variety
        wave = amplitude * (2 * (t * frequency - np.floor(0.5 + t * frequency)))
    else:  # Default to sine
        wave = amplitude * np.sin(2 * np.pi * frequency * t)
    return wave.astype(np.float32).tobytes()


def play_sound_effect(frequency, duration, wave_type='sine'):
    """Play a generated sound wave."""
    if PYAUDIO_AVAILABLE and stream:
        try:
            wave_data = generate_sound_wave(frequency, duration, wave_type=wave_type)
            stream.write(wave_data)
        except Exception as e:
            # This can happen if the stream is closed or audio device issues
            # print(f"Could not play sound: {e}")
            # Optionally, try to re-initialize audio or mark as unavailable
            # For now, we'll just pass to avoid spamming console
            pass


def play_hit_paddle_sound():
    play_sound_effect(660, DURATION_PADDLE_HIT, 'square')

def play_hit_wall_sound():
    play_sound_effect(330, DURATION_WALL_HIT, 'sawtooth') # Changed sound for wall

def play_score_sound():
    play_sound_effect(880, DURATION_SCORE, 'sine')

# --- Game Constants ---
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 400
PADDLE_WIDTH = 15
PADDLE_HEIGHT = 80
BALL_RADIUS = 8
AI_PADDLE_SPEED = 6  # Renamed from PADDLE_SPEED and slightly adjusted
BALL_SPEED_X_INITIAL = 4 # Slightly reduced initial speed for better control
BALL_SPEED_Y_INITIAL = 4

# Gameplay enhancement constants
WINNING_SCORE = 5
PADDLE_HIT_SPEED_INCREASE_FACTOR = 1.07 # How much speed increases on paddle hit
MAX_ABS_BALL_SPEED_X = 10             # Maximum horizontal ball speed
PADDLE_BOUNCE_ANGLE_FACTOR = 1.7      # Multiplier for Y speed based on paddle hit location
MAX_ABS_BALL_SPEED_Y = 8              # Maximum vertical ball speed

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (50, 50, 50) # Darker gray for center line for better contrast
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# --- Pygame Setup ---
pygame.init()
init_audio() # Initialize audio system
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Ultra!Pong HDR 1.0A - Enhanced")
clock = pygame.time.Clock()
try:
    font = pygame.font.Font(None, 74) # Default font
    small_font = pygame.font.Font(None, 36)
except pygame.error: # Fallback if default font is not found (e.g. minimal systems)
    font = pygame.font.SysFont("arial", 74)
    small_font = pygame.font.SysFont("arial", 36)


# --- Game Objects ---
# Player paddle (left side)
player_paddle = pygame.Rect(30, SCREEN_HEIGHT // 2 - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
# AI paddle (right side)
ai_paddle = pygame.Rect(SCREEN_WIDTH - 30 - PADDLE_WIDTH, SCREEN_HEIGHT // 2 - PADDLE_HEIGHT // 2, PADDLE_WIDTH, PADDLE_HEIGHT)
# Ball
ball = pygame.Rect(SCREEN_WIDTH // 2 - BALL_RADIUS, SCREEN_HEIGHT // 2 - BALL_RADIUS, BALL_RADIUS * 2, BALL_RADIUS * 2)

# --- Game State ---
ball_speed_x = BALL_SPEED_X_INITIAL
ball_speed_y = BALL_SPEED_Y_INITIAL
player_score = 0
ai_score = 0
game_paused = False
game_over = False
winner = ""

def reset_ball(served_by_player_next):
    """
    Resets the ball to the center and sets its initial speed and direction.
    Args:
        served_by_player_next (bool): True if the player serves next, False if AI serves.
    """
    global ball_speed_x, ball_speed_y
    ball.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

    if served_by_player_next:
        ball_speed_x = BALL_SPEED_X_INITIAL
    else:  # Served by AI next
        ball_speed_x = -BALL_SPEED_X_INITIAL
    
    # Alternate y direction for variety on serve
    if random.choice([True, False]): # Using random.choice for more explicit randomness
        ball_speed_y = BALL_SPEED_Y_INITIAL
    else:
        ball_speed_y = -BALL_SPEED_Y_INITIAL

def reset_game():
    """Resets the game to its initial state."""
    global player_score, ai_score, game_over, winner, game_paused
    global ball_speed_x, ball_speed_y # These will be set by reset_ball

    player_score = 0
    ai_score = 0
    game_over = False
    winner = ""
    game_paused = False
    
    # Reset paddle positions
    player_paddle.centery = SCREEN_HEIGHT // 2
    ai_paddle.centery = SCREEN_HEIGHT // 2
    
    # Decide who serves first in a new game (randomly)
    serves_first_by_player = random.choice([True, False])
    reset_ball(serves_first_by_player)

def draw_elements():
    """Draws all game elements to the screen."""
    screen.fill(BLACK) # Black background

    # Draw paddles
    pygame.draw.rect(screen, BLUE, player_paddle) # Player paddle color
    pygame.draw.rect(screen, RED, ai_paddle)     # AI paddle color
    
    # Draw ball
    pygame.draw.ellipse(screen, WHITE, ball)
    
    # Draw center line
    pygame.draw.aaline(screen, GRAY, (SCREEN_WIDTH // 2, 0), (SCREEN_WIDTH // 2, SCREEN_HEIGHT))

    # Draw scores
    player_text = font.render(str(player_score), True, WHITE)
    ai_text = font.render(str(ai_score), True, WHITE)
    screen.blit(player_text, (SCREEN_WIDTH // 4 - player_text.get_width() // 2, 20))
    screen.blit(ai_text, (3 * SCREEN_WIDTH // 4 - ai_text.get_width() // 2, 20))

    # Pause/Game Over display
    if game_paused and not game_over:
        pause_msg_text = "PAUSED"
        resume_msg_text = "Press P to Resume"
        pause_msg_render = small_font.render(pause_msg_text, True, WHITE)
        resume_msg_render = small_font.render(resume_msg_text, True, WHITE)
        screen.blit(pause_msg_render, pause_msg_render.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)))
        screen.blit(resume_msg_render, resume_msg_render.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20)))

    elif game_over:
        winner_msg_text = f"{winner} Wins!"
        play_again_msg_text = "Play Again? (Y/N)"
        winner_msg_render = font.render(winner_msg_text, True, WHITE) # Larger font for winner
        play_again_msg_render = small_font.render(play_again_msg_text, True, WHITE)
        screen.blit(winner_msg_render, winner_msg_render.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30)))
        screen.blit(play_again_msg_render, play_again_msg_render.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20)))

def update_game_state():
    """Updates the game state, including ball movement, collisions, and AI."""
    global ball_speed_x, ball_speed_y, player_score, ai_score, game_over, winner

    if game_paused or game_over:
        return

    # --- Ball Movement ---
    ball.x += ball_speed_x
    ball.y += ball_speed_y

    # --- Paddle Collision and Response ---
    collided_with_paddle_this_frame = False # To prevent double wall sound if paddle hit near wall

    # Player paddle collision (left paddle)
    if ball.colliderect(player_paddle):
        collided_with_paddle_this_frame = True
        play_hit_paddle_sound()
        
        # Correct ball position to be flush with paddle
        ball.left = player_paddle.right
        
        # Calculate new ball_speed_x (increase speed and make it positive)
        current_abs_speed_x = abs(ball_speed_x) # Speed before this collision
        new_abs_speed_x = min(current_abs_speed_x * PADDLE_HIT_SPEED_INCREASE_FACTOR, MAX_ABS_BALL_SPEED_X)
        ball_speed_x = new_abs_speed_x  # Positive direction (moving right)

        # Calculate new ball_speed_y based on impact point
        delta_y = ball.centery - player_paddle.centery
        normalized_delta_y = delta_y / (PADDLE_HEIGHT / 2) # Range approx -1 to 1
        ball_speed_y = normalized_delta_y * BALL_SPEED_Y_INITIAL * PADDLE_BOUNCE_ANGLE_FACTOR

    # AI paddle collision (right paddle)
    elif ball.colliderect(ai_paddle):
        collided_with_paddle_this_frame = True
        play_hit_paddle_sound()

        # Correct ball position
        ball.right = ai_paddle.left
        
        # Calculate new ball_speed_x (increase speed and make it negative)
        current_abs_speed_x = abs(ball_speed_x) # Speed before this collision
        new_abs_speed_x = min(current_abs_speed_x * PADDLE_HIT_SPEED_INCREASE_FACTOR, MAX_ABS_BALL_SPEED_X)
        ball_speed_x = -new_abs_speed_x # Negative direction (moving left)

        # Calculate new ball_speed_y
        delta_y = ball.centery - ai_paddle.centery
        normalized_delta_y = delta_y / (PADDLE_HEIGHT / 2)
        ball_speed_y = normalized_delta_y * BALL_SPEED_Y_INITIAL * PADDLE_BOUNCE_ANGLE_FACTOR

    # Common adjustments for ball_speed_y if a paddle collision occurred
    if collided_with_paddle_this_frame:
        # Cap ball_speed_y
        if abs(ball_speed_y) > MAX_ABS_BALL_SPEED_Y:
            ball_speed_y = math.copysign(MAX_ABS_BALL_SPEED_Y, ball_speed_y)
        # Ensure minimum vertical speed if not zero, to prevent overly flat shots making game stall
        elif 0 < abs(ball_speed_y) < 1.0:
            ball_speed_y = math.copysign(1.0, ball_speed_y)
        # If ball_speed_y is exactly 0.0 (center hit), it remains 0.0 for a straight shot

    # --- Wall Collisions (Y-axis) ---
    # These are checked after paddle collisions to correctly handle edge cases
    if ball.top <= 0:
        ball.top = 0  # Clamp position
        ball_speed_y *= -1
        if not collided_with_paddle_this_frame: # Avoid double sound if hit paddle then wall instantly
             play_hit_wall_sound()
    elif ball.bottom >= SCREEN_HEIGHT:
        ball.bottom = SCREEN_HEIGHT  # Clamp position
        ball_speed_y *= -1
        if not collided_with_paddle_this_frame:
            play_hit_wall_sound()

    # --- Scoring ---
    point_scored = False
    serve_to_player_next = False

    if ball.left <= 0:  # AI scores (ball went off left edge)
        ai_score += 1
        play_score_sound()
        point_scored = True
        serve_to_player_next = True # Player serves next
        if ai_score >= WINNING_SCORE:
            game_over = True
            winner = "AI"
    elif ball.right >= SCREEN_WIDTH:  # Player scores (ball went off right edge)
        player_score += 1
        play_score_sound()
        point_scored = True
        serve_to_player_next = False # AI serves next
        if player_score >= WINNING_SCORE:
            game_over = True
            winner = "Player"
    
    if point_scored and not game_over:
        reset_ball(serve_to_player_next)
    elif point_scored and game_over: # If game ends, just center the ball visually
        ball.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        ball_speed_x = 0 # Stop ball movement
        ball_speed_y = 0


    # --- Player Paddle Control ---
    mouse_y = pygame.mouse.get_pos()[1]
    player_paddle.centery = mouse_y
    # Clamp player paddle to screen bounds
    player_paddle.clamp_ip(screen.get_rect())


    # --- AI Paddle Control (Simple AI) ---
    # AI tries to follow the ball's y-coordinate
    if ai_paddle.centery < ball.centery - AI_PADDLE_SPEED / 2: # Added a small deadzone
        ai_paddle.y += AI_PADDLE_SPEED
    elif ai_paddle.centery > ball.centery + AI_PADDLE_SPEED / 2:
        ai_paddle.y -= AI_PADDLE_SPEED
    # Clamp AI paddle to screen bounds
    ai_paddle.clamp_ip(screen.get_rect())


def main_menu():
    """Displays the main menu and waits for player input."""
    menu_active = True
    while menu_active:
        screen.fill(BLACK)
        title_text = font.render("Ultra!Pong HDR 1.0A", True, WHITE)
        # Using a slightly different approach for subtitle for clarity
        subtitle_line1 = small_font.render("[C] Team Flames 20XX", True, GRAY)
        subtitle_line2 = small_font.render("[C] Enhanced 2024-2025", True, GRAY) # Updated year
        prompt_text = small_font.render("ENTER: Start Game   ESC: Quit", True, WHITE)

        screen.blit(title_text, title_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3)))
        screen.blit(subtitle_line1, subtitle_line1.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3 + 60)))
        screen.blit(subtitle_line2, subtitle_line2.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3 + 90)))
        screen.blit(prompt_text, prompt_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)))
        
        pygame.display.flip()
        clock.tick(30) # Menu doesn't need full 60 FPS

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False  # Signal to quit the entire application
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_KP_ENTER:
                    return True  # Signal to start the game
                if event.key == pygame.K_ESCAPE:
                    return False # Signal to quit

# --- Main Game Loop ---
if __name__ == "__main__":
    if main_menu(): # Show main menu first
        reset_game() # Initialize game state
        running = True
        while running:
            # Event handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_p and not game_over: # Pause only if game not over
                        game_paused = not game_paused
                    elif game_over: # Only handle Y/N if game is over
                        if event.key == pygame.K_y:
                            reset_game() # Reset for a new game
                        elif event.key == pygame.K_n:
                            running = False # Quit to main menu (or exit)
                    elif event.key == pygame.K_ESCAPE: # Allow ESC to pause or go to menu
                        if game_paused:
                            game_paused = False # Unpause
                        elif not game_over: # If game is running, pause it
                            game_paused = True
                        # If game_over, ESC does nothing here (Y/N is primary)
            
            # Update game logic
            update_game_state()
            
            # Draw everything
            draw_elements()
            
            # Update the display
            pygame.display.flip()
            
            # Cap the frame rate
            clock.tick(60) # Target 60 FPS

    # Cleanup
    terminate_audio()
    pygame.quit()
    sys.exit()
