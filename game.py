import pygame
import os, sys
import numpy as np
import socket 
import pickle
import threading
import time
import random

from mapmaker import Maze

# Pygame
CAPTION = "Hidey"
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


# Server address
SERVER_ADDRESS = ('34.224.98.28', 10001)
# SERVER_ADDRESS = ('172.25.32.1', 10001)

# game rules
COOLDOWN_TIME = 5
HIDE_TIME = 5
SEEK_TIME = 15

# Colors
SEEKER = (255,0,0)
BGSEEKER = (10,10,10)
GHOST = (30,30,30)
BGGHOST = (100,100,100)


class Map:
    '''Class used to store a map of walls'''
    def __init__(self, ms=100):
        '''Initialize this map with a set of border walls'''
        self.mapsize = ms
        self.walls = [[0,  0,  ms, 0],  \
                      [ms, 0,  ms, ms], \
                      [ms, ms, 0,  ms], \
                      [0,  ms, 0,  0]]

    def addWall(self, a, b):
        '''add a wall from point a to point b'''
        self.walls.append(a+b)
    
    
class Player:
    '''Player object containing important information about a player.'''
    def __init__(self, location, username, speed=8):
        '''Setup the player object'''
        # for multiplayer functions
        self.username = username
        self.address = None
        self.score = 0
        self.role = "ghost"
        # player movement variables
        self.location = location
        self.inputs = set()
        self.speed = speed
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
        '''get a rect representing the player, used for drawing'''
        rect = pygame.Rect(0,0,self.size,self.size)
        rect.center = tuple(self.location)
        return rect

 
class Game:
    '''Base Game class'''
    def __init__(self):
        '''create a gunner and create a group for bullets '''
        
        # game fps and loop condiiton
        self.done = False
        self.clock = pygame.time.Clock()
        self.fps = 30
        self.state = "waiting"

        # setup map
        self.map = Map(1200)
        self.map.walls = Maze.load_from_file('map1.txt')
        
        # set a start timer for timestamps
        self.start_time = time.time()
    

    def update(self):
        '''update all bullets, and the player motion'''
        for player in self.players:
            if not (player.role == 'seeker' and self.state == 'hiding'):
                player.update_location(self.map.walls)
        # print(self.player.location)
    
    def get_caught(self, seeker):
        '''get a list of all hiding players that collide with the seeker'''
        seeker_rect = seeker.get_rect()
        caught = []
        for player in self.players:
            if player != seeker and player.role == 'hider' and player.get_rect().colliderect(seeker_rect):
                caught.append(player)
        return caught

        
    def main_loop(self):
        '''main loop'''
        pass


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
        self.player = Player([301,401], username)
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
            data, address = self.socket.recvfrom(1024)
            
            if data:
                data = pickle.loads(data)

                print('received data: %s' % data['type'])

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
        
        # draw the map 
        # create a camera Frame that will be relative to the map 
        Frame = np.zeros(SCREEN_SIZE)
        # adjust the wall positions based on the player location and screen size, then draw the walls to the surface
        for wall in np.array(self.map.walls):
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
        text = self.textfont.render(self.state.upper(), True, (255,255,255))
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


class HeadlessGameServer(Game):
    '''Class for creating the hide-and-seek game server'''
    def __init__(self):
        '''Setup the server and Game'''
        # initialize game attrs
        Game.__init__(self)

        # create player list
        self.players = []
        self.seeker = None

        # create the socket used for the server
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
    
    # create UDP Server
    def setup_server(self):
        '''Bind the server to the serverport and start the input and notification threads'''
        self.socket.bind((socket.gethostbyname(socket.getfqdn()),SERVER_ADDRESS[1]))
        print("starting server at %s:%d" % self.socket.getsockname())
        
        print("starting serve thread")
        t = threading.Thread(target=self.serve_forever)
        t.setDaemon(True) # don't hang on exit
        t.start()
        print("starting reply server")
        t2 = threading.Thread(target=self.notify_clients)
        t2.setDaemon(True) # don't hang on exit
        t2.start()
    
    def serve_forever(self):
        '''Receive and handle packets from the UDP Port'''
        while True:
            try:
                data, address = self.socket.recvfrom(1024)
                if data:
                    self.parse_data(data, address)
            except ConnectionResetError:
                # TODO do something here to recover when a client is lost
                print("connection lost")
                pass
    
    def parse_data(self, data, address):
        '''Parse and handle a packet
        
        Set the player inputs, handle a login, and reply if necessary'''
        # unpickle the data
        data = pickle.loads(data)
        
        # handle client login
        if data["type"] == "login":
            # username already taken
            if [x for x in self.players if x.username == data['username']]:
                self.socket.sendto(pickle.dumps({'type':'login_ack','status':'bad'}), address)
            else:
                # ack
                self.socket.sendto(pickle.dumps({'type':'login_ack', 'status':'ok'}), address) # TODO: Send the map with a larger packet size?
                print('replied to %s login_ack' % data['username'])
                # register user
                newPlayer = Player([301,401],data['username'])
                newPlayer.address = address
                newPlayer.last_input = -1
                self.players.append(newPlayer)
                
        # handle client inputs
        if data["type"] == "inputs":
            # get the Player Object for the player
            client_player = [x for x in self.players if x.address == address]

            # reply with kick message if player is not registered
            if not client_player:
                self.socket.sendto(pickle.dumps({'type':'kick'}), address)
            
            # if this is the most recent timestamp
            elif client_player and data['timestamp'] >= client_player[0].last_input:
                # reply with ack
                self.socket.sendto(pickle.dumps({'type':'inputs_ack','inputs':data['inputs']}), address)
                print('replied to %s inputs_ack' % client_player[0].username)
                # apply inputs to player
                print('setting inputs for:',client_player[0].username,'inputs are:',data['inputs'])
                client_player[0].inputs = data['inputs']
                
        
    
    def notify_clients(self):
        '''Send gamestate information to all clients at intervals'''
        start = time.time()
        while True:
            # send along a timestamp! the client will only apply the most recent timestamp update
            timestamp = int((time.time()-start)*10) 
            # create update object to send 
            data = pickle.dumps({'type':'update','players':self.players,'game_state':self.state,'timestamp':timestamp})
            # send update to all clients
            for p in self.players:
                addr = p.address
                # print(addr,data)
                self.socket.sendto(data, addr)
                print("notifying: %s:%d" % addr)
            
            time.sleep(0.200) # update clients at 200 ms interval
            
            
    def main_loop(self):
        '''Main control loop
        
        Run the game simulation and handle game state changes'''

        # reset_time is the time when a round ends or the server starts
        reset_time = time.time()

        # waiting for players to join to start the game
        self.state="waiting"

        while not self.done:
            # the client inputs are handled in a separate thread, here we just simulate the game
            self.update()

            # get all players caught by seeker, set them to ghosts, increment seeker score
            if self.state == "seeking":
                caught = self.get_caught(self.seeker)
                for p in caught:
                    print("%s was caught" % p.username)
                    p.role = "ghost"
                    self.seeker.score += 2

            # handle game state changes
            if len(self.players) < 2:
                reset_time = time.time()
            if self.state == "waiting" and time.time() - reset_time > COOLDOWN_TIME:
                self.round_start()
            elif self.state == "hiding" and time.time() - reset_time > COOLDOWN_TIME + HIDE_TIME:
                self.seeker_start()
            elif self.state == "seeking" and time.time() - reset_time > COOLDOWN_TIME + HIDE_TIME + SEEK_TIME:
                self.round_end()
                reset_time = time.time()


            self.clock.tick(self.fps)

    def round_start(self):
        '''Start the round'''
        self.state="hiding"
        print("ROUND START...")

        for player in self.players:
            player.role = "hider"
            player.location = [301,401]

        # randomly select a seeker
        self.seeker = random.choice(self.players)
        self.seeker.role = "seeker"

    def seeker_start(self):
        '''Start the seeker phase'''
        self.state = "seeking"
        print("SEEKER START...")


    def round_end(self):
        '''End the round'''
        self.state = "waiting"
        print("ROUND END...")
        for player in self.players:
            if player.role == "hider":
                player.score += 1
            player.role = "ghost"

        self.seeker = None


