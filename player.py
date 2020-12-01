
import random 
import numpy as np

from config import *

class Player:
    '''Player object containing important information about a player.'''
    def __init__(self, location, username):
        '''Setup the player object'''
        # for multiplayer functions
        self.username = username
        self.address = None
        self.score = 0
        self.role = "ghost"
        # player movement variables
        self.location = location
        self.inputs = set()
        self.speed = 10
        # set the color and size of the player
        self.color = (random.randint(100,255), random.randint(100,255), random.randint(100,255))
        self.bgcolor = (random.randint(0,100), random.randint(0,100), random.randint(0,100))
        self.size = 10

    def __str__(self):
        '''Return a stringified copy of this player'''
        return "username:"+self.username+", location:"+str(self.location)+", inputs:"+str(self.inputs)

    def handle_event(self, event):
        '''an event is passed to the client
        
        when an arrow key is pressed or released, the inputs variable is updated with the current inputs'''
        if event.type in [pygame.KEYDOWN, pygame.KEYUP] and event.key in CLIENT_ARROW_KEYS:
            self.inputs = set()
            keys = pygame.key.get_pressed()
            for key in CLIENT_ARROW_KEYS:
                if keys[key]:
                    self.inputs.add(CLIENT_TO_PROTOCOL[key])

    def update_location(self,walls):
        '''Updates the location of this player
        
        Given a set of walls and player inputs, apply a change to the position of this player'''
        # calculate the desired change in position, (dx,dy)
        dx = dy = 0
        for i in self.inputs:
            if i == UP_KEY:
                dy -= self.speed
            elif i == DOWN_KEY:
                dy += self.speed
            elif i == LEFT_KEY:
                dx -= self.speed 
            elif i == RIGHT_KEY:
                dx += self.speed 

        # check if the player is allowed to move into the new spot
        newspot = [self.location[0] + dx, self.location[1] + dy]
        if self.role == 'ghost' or ((dy != 0 or dx != 0) and not self.wallcollide(self.location+newspot,walls)):
            self.location = newspot

    def wallcollide(self, step_vector, walls):
        '''Check if a step intersects a wall

        using math from: https://en.wikipedia.org/wiki/Line%E2%80%93line_intersection'''

        x1,y1,x2,y2 = step_vector 
        for wall in walls:
            x3,y3,x4,y4 = wall 

            denom = np.linalg.det([[x1-x2,x3-x4],[y1-y2,y3-y4]])
            if denom == 0: # parallel or coincedent
                continue 

            t = np.linalg.det([[x1-x3,x3-x4],[y1-y3,y3-y4]]) / denom
            u = -np.linalg.det([[x1-x2,x1-x3],[y1-y2,y1-y3]]) / denom

            # if there is an intersection
            # (check if 0<t represents that there is no collision if the players path starts on a wall)
            if 0 < t <= 1 and 0 <= u <= 1:
                return True 

        return False
    
    def get_rect(self):
        '''get a rect representing the player, used for collision checking'''
        rect = pygame.Rect(0,0,int(self.size*2.5),int(self.size*2.5))
        rect.center = tuple(self.location)
        return rect
