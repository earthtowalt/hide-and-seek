import os, sys
import pygame 
import pickle
import socket 
import threading
import time


import numpy as np

from player import Player 
from game import Game

from config import *

class VisualGame(Game):
    '''A class for the client-side of the hide and seek game
    
    Creates a GUI with pygame and maintains a UDP communication with the server
    To use this object: initialize it, call login(), then call main_loop()'''
    def __init__(self, username):
        '''Setup VisualGame object
        
        Sets up the pygame visualization and the UDP socket'''
        # pygame window setup 
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        # os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        pygame.display.set_caption(CAPTION)
        pygame.display.set_mode(SCREEN_SIZE)
        # call the super constructor
        Game.__init__(self)

        #init screen 
        self.screen = pygame.display.get_surface()
        self.screen.set_colorkey((0,0,0))
        # initialize the Font
        self.textfont = pygame.font.Font(None, 25)

        # create the player objects - self.player is THIS client player, self.players is a list of all players
        self.player = Player(MAP_CENTER, username)
        self.players = [self.player]
        
        # initialize UDP connection
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        self.socket.bind(('',0)) # have the computer give me a random port
        print("binding client to %s:%d" % self.socket.getsockname())
        print("starting client-serve thread")
        t = threading.Thread(target=self.serve_forever)
        t.setDaemon(True) # don't hang on exit
        t.start()

        # current time_stamp will handle the 
        self.current_update_timestamp = 0

    def serve_forever(self):
        '''loop forever to handle incoming UDP packets'''
        while True:
            # read the data and address
            data, address = self.socket.recvfrom(MAX_PACKET)
            
            if data:
                data = pickle.loads(data)

                # print('received data: %s' % data['type'])

                # if login fails, then quit. 
                if data['type'] == 'login_ack':
                    print("successful login at address: %s:%d" % address)
                    if data['status'] != 'ok':
                        print("login failed")
                        self.done = True 
                        sys.exit(1)
                # server may kick any players for inactivity or for failing to login properly
                if data['type'] == 'kick':
                    print('kicked from game...')
                    self.done = True
                    sys.exit(0)
                # apply game-state updates
                if data['type'] == 'update' and data['timestamp'] > self.current_update_timestamp:
                    
                    # save the current inputs, we don't want to change these based on server update. 
                    current_inputs = self.player.inputs

                    # get the players data from the server and get the client player in self.player
                    self.players = data['players']
                    self.player = next(x for x in data['players'] if x.username == self.player.username)

                    # if a server update contains incorrect player inputs, resend the inputs
                    if current_inputs != self.player.inputs:
                        print('correcting inputs to: %s' % str(current_inputs))
                        self.send({'type':'inputs','inputs':current_inputs})
                    
                    # set the player inputs back to what the player is actually pressing
                    self.player.inputs = current_inputs

                    # update the game state
                    self.state = data['game_state']
                    # keep track of when the latest server update was received
                    self.current_update_timestamp = data['timestamp']

                    # if the mapseed is different from the current seed, then calculate the new map.
                    if data['map_seed'] != self.map_seed:
                        # generate new map...
                        print('generating new client map with seed: %d' % data['map_seed'])
                        self.map = self.generate_map(data['map_seed'])
                        # update seed variable
                        self.map_seed = data['map_seed']

                    # TODO: Add averaging or some other method to reduce other players jumpiness
                    # now = dict()
                    # for p in self.players:
                    #     now[p.username] = p
                    # for p in data['players']:
                    #     if p.username in now:
                    #         now[p.username] = p 
                    #     else:
                    #         self.players.append(p)

    def send(self, data):
        '''send data to the server

        expects a dictionary. Will attach the timestamp and pickle the message'''

        data['timestamp'] = int((time.time()-self.start_time)*10)
        msg = pickle.dumps(data)
        self.socket.sendto(msg, SERVER_ADDRESS)
        
    def login(self, username):
        '''send a login message to the server with the username FIXME DONT SEND PORT NUM'''

        self.send({'type':'login', 'username':username, 'return_port':self.socket.getsockname()[1]})
        print('waiting for server ack and map info...')
    
    def event_loop(self):
        '''handle events by passing them to the appropriate objects'''
        for event in pygame.event.get():
            # print(event)
            if event.type == pygame.QUIT:
                self.done = True 
            # if an arrow key was pressed, pass it along to the player
            if event.type in [pygame.KEYDOWN,pygame.KEYUP] and event.key in CLIENT_ARROW_KEYS:
                # update the player object with the event
                self.player.handle_event(event)

                # send a message to the server with updated player inputs
                self.send({'type':'inputs','inputs':self.player.inputs})
    
    def draw(self):
        '''draw all elements to the display surface'''
        # black the screen
        self.screen.fill(BACKGROUND_COLOR)
        
        # create a surface to draw to, it will later be blit to the screen
        surface = pygame.Surface(SCREEN_SIZE)

        # draw a small circle at the center of the map (for debugging) 
        tmp = MAP_CENTER.copy()
        tmp[0] -= int(self.player.location[0] - SCREEN_SIZE[0]/2)
        tmp[1] -= int(self.player.location[1] - SCREEN_SIZE[1]/2)
        pygame.draw.circle(surface, (255,255,255), tmp, 3)
        
        # draw the map 
        # create a camera Frame that will be relative to the map 
        Frame = np.zeros(SCREEN_SIZE)
        # adjust the wall positions based on the player location and screen size, then draw the walls to the surface
        for wall in np.array(self.map):
            wall[0] -= self.player.location[0] - SCREEN_SIZE[0]/2
            wall[1] -= self.player.location[1] - SCREEN_SIZE[1]/2
            wall[2] -= self.player.location[0] - SCREEN_SIZE[0]/2
            wall[3] -= self.player.location[1] - SCREEN_SIZE[1]/2
            
            pygame.draw.line(surface, (255,255,255,255), wall[:2], wall[2:], 3)

        # draw each player along with their names and scores
        for player in self.players:
            if player != self.player:
                x = int(player.location[0] - self.player.location[0] + SCREEN_SIZE[0]/2)
                y = int(player.location[1] - self.player.location[1] + SCREEN_SIZE[1]/2)

                # set the color
                if player.role == "seeker":
                    color = SEEKER
                    bgcolor = BGSEEKER
                elif player.role == "ghost":
                    color = GHOST
                    bgcolor = BGGHOST
                else:
                    color = player.color
                    bgcolor = player.bgcolor
                # draw the player circle
                pygame.draw.circle(surface,bgcolor,(x,y), 12)
                pygame.draw.circle(surface,color,(x,y), 10)

                # draw usernames and scores above other players
                text = self.textfont.render(player.username[:10], True, (255,255,255))
                text_rect = text.get_rect(center=(x, y-40))
                surface.blit(text,text_rect)

                text = self.textfont.render(str(player.score), True, (255,255,255))
                text_rect = text.get_rect(center=(x, y-20))
                surface.blit(text,text_rect)
        
        # set the player color
        if self.player.role == "seeker":
            color = SEEKER
            bgcolor = BGSEEKER
        elif self.player.role == "ghost":
            color = GHOST
            bgcolor = BGGHOST
        else:
            color = self.player.color
            bgcolor = self.player.bgcolor
        # draw the player circles
        pygame.draw.circle(surface,bgcolor,tuple(map(int,(SCREEN_SIZE[0]/2, SCREEN_SIZE[1]/2))), 12)
        pygame.draw.circle(surface,color,tuple(map(int,(SCREEN_SIZE[0]/2, SCREEN_SIZE[1]/2))), 10)

        # draw usernames and score above this player
        text = self.textfont.render(self.player.username[:6], True, (255,255,255))
        text_rect = text.get_rect(center=(SCREEN_SIZE[0]/2, SCREEN_SIZE[1]/2 - 40))
        surface.blit(text,text_rect)

        text = self.textfont.render(str(self.player.score), True, (255,255,255))
        text_rect = text.get_rect(center=(SCREEN_SIZE[0]/2, SCREEN_SIZE[1]/2 - 20))
        surface.blit(text,text_rect)

        # draw game state
        text = self.textfont.render(self.state.upper(), True, (0,0,255))
        text_rect = text.get_rect(center=(SCREEN_SIZE[0]/2, 60))
        surface.blit(text,text_rect)

        # paint the surface to the screen
        self.screen.blit(surface,(0,0))

        # update the display
        pygame.display.update()
    
    # repeat for the duration of the game. 
    def main_loop(self):
        '''main control loop'''
        while not self.done:
            self.event_loop()
            self.update()
            self.draw()
            self.clock.tick(self.fps)
