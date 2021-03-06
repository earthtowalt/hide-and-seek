import pygame

# Pygame
CAPTION = "Hide and Seek!"
SCREEN_SIZE = 640,400
BACKGROUND_COLOR = (0,0,0,0)

# get the client arrow keys
CLIENT_UP_KEY = pygame.K_UP
CLIENT_DOWN_KEY = pygame.K_DOWN
CLIENT_RIGHT_KEY = pygame.K_RIGHT
CLIENT_LEFT_KEY = pygame.K_LEFT
CLIENT_ARROW_KEYS = [CLIENT_UP_KEY, CLIENT_DOWN_KEY, CLIENT_RIGHT_KEY, CLIENT_LEFT_KEY]

# create codes so control keys are the same across os
UP_KEY = 0
DOWN_KEY = 1
RIGHT_KEY = 2
LEFT_KEY = 3
ARROW_KEYS = [UP_KEY, DOWN_KEY, RIGHT_KEY, LEFT_KEY]

CLIENT_TO_PROTOCOL = {
    CLIENT_UP_KEY:UP_KEY,
    CLIENT_DOWN_KEY:DOWN_KEY,
    CLIENT_RIGHT_KEY:RIGHT_KEY,
    CLIENT_LEFT_KEY:LEFT_KEY
}


# Server Config
SERVER_ADDRESS = ('34.224.98.28', 10001)
# SERVER_ADDRESS = ('172.25.32.1', 10001)
INACTIVE_TIME = 60
MAX_PACKET = 2048

# game rules
COOLDOWN_TIME = 10
HIDE_TIME = 5
SEEK_TIME = 30

# map size
MAP_SIZE = 20
MAP_CENTER = [480,480]

# Role speeds
SEEKER_SPEED = 9
HIDER_SPEED = 7
GHOST_SPEED = 10

# Colors
SEEKER = (255,0,0)
BGSEEKER = (10,10,10)
GHOST = (30,30,30)
BGGHOST = (100,100,100)