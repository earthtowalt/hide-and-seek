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

# control
UP_KEY = pygame.K_UP
DOWN_KEY = pygame.K_DOWN
RIGHT_KEY = pygame.K_RIGHT
LEFT_KEY = pygame.K_LEFT
ARROW_KEYS = [UP_KEY, DOWN_KEY, RIGHT_KEY, LEFT_KEY]


# Socket
SERVER_ADDRESS = ('54.210.86.172', 10001)

# game rules
COOLDOWN_TIME = 5
HIDE_TIME = 5
SEEK_TIME = 15

class Map:
    def __init__(self, ms=100):
        self.mapsize = ms
        self.walls = [[0,  0,  ms, 0],  \
                      [ms, 0,  ms, ms], \
                      [ms, ms, 0,  ms], \
                      [0,  ms, 0,  0]]
        self.addWall([200,200],[800,800])
        self.addWall([200,800],[800,200])
    
    # add a wall from point a to point b
    def addWall(self, a, b):
        self.walls.append(a+b)


class Player:
    def __init__(self, location, username, speed=8):
        self.username = username
        self.address = None
        self.location = location
        self.inputs = set()
        self.speed = speed
        self.color = (0,0,255)
        self.bgcolor = (100,100,200)
        self.score = 0
        self.role = "ghost"
        self.size = 10

        self.color = (random.randint(100,255), random.randint(100,255), random.randint(100,255))
        self.bgcolor = (random.randint(0,100), random.randint(0,100), random.randint(0,100))
        
    def handle_event(self, event):
        # if event.type == pygame.KEYDOWN:
        #     self.inputs.add(event.key)
        # elif event.type == pygame.KEYUP and event.key in self.inputs:
        #     self.inputs.remove(event.key)
        
        if event.type in [pygame.KEYDOWN, pygame.KEYUP] and event.key in ARROW_KEYS:
            self.inputs = set()
            keys = pygame.key.get_pressed()
            for key in ARROW_KEYS:
                if keys[key]:
                    self.inputs.add(key)
        
    def update_location(self,walls):
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

        newspot = [self.location[0] + dx, self.location[1] + dy]
        if self.role == 'ghost' or ((dy != 0 or dx != 0) and not self.wallcollide(self.location+newspot,walls)):
            self.location = newspot

    def wallcollide(self, step_vector, walls):
        x1,y1,x2,y2 = step_vector 
        for wall in walls:
            x3,y3,x4,y4 = wall 

            denom = np.linalg.det([[x1-x2,x3-x4],[y1-y2,y3-y4]])
            if denom == 0: # parallel or coincedent
                continue 

            t = np.linalg.det([[x1-x3,x3-x4],[y1-y3,y3-y4]]) / denom
            u = -np.linalg.det([[x1-x2,x1-x3],[y1-y2,y1-y3]]) / denom

            if 0 < t <= 1 and 0 <= u <= 1:
                return True 

        return False
    
    def get_rect(self):
        rect = pygame.Rect(0,0,self.size,self.size)
        rect.center = tuple(self.location)
        return rect


class Game:
    def __init__(self):
        '''create a gunner and create a group for bullets '''
        
        # game fps and loop condiiton
        self.done = False
        self.clock = pygame.time.Clock()
        self.fps = 30
        self.state = "waiting"

        # setup players
        # self.player = Player([300,400])
        
        # sprite groups ?players?
        # self.players = pygame.sprite.Group()
        self.map = Map(1200)
        # maze = Maze(15,15,7,7)
        # maze.make_maze()

        self.map.walls = Maze.load_from_file('map1.txt')

    

    def update(self):
        '''update all bullets, and the player motion'''
        for player in self.players:
            if not (player.role == 'seeker' and self.state == 'hiding'):
                player.update_location(self.map.walls)
        # print(self.player.location)
    
    def get_caught(self, seeker):
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
    def __init__(self, username):
        # pygame window setup 
        os.environ['SDL_VIDEO_CENTERED'] = '1'
        # os.environ["SDL_VIDEODRIVER"] = "dummy"
        pygame.init()
        pygame.display.set_caption(CAPTION)
        pygame.display.set_mode(SCREEN_SIZE)
        
        Game.__init__(self)
        #init screen 
        self.screen = pygame.display.get_surface()
        self.screen.set_colorkey((0,0,0))

        self.textfont = pygame.font.Font(None, 25)

        # create the player objects
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

        self.recent_timestamp = 0
    
    def serve_forever(self):
        while True:
            data, address = self.socket.recvfrom(1024)
            
            # print('\treceived: %s bytes from %s' % (len(data), address))
            # print('\treceived: %s' % data)
            # print('\tunpickled:%s' % pickle.loads(data))
            # print()
            
            if data:
                data = pickle.loads(data)
                
                # print('\tparsing data...')
                # self.parse_data(data)

                if data['type'] == 'login_ack':
                    print("successful login at address: %s:%d" % address)
                    if data['status'] != 'ok':
                        print("login failed")
                        sys.exit(0)
                # if inputs ack is not the current inputs, then send the current inputs again. 
                if data['type'] == 'inputs_ack' and data['inputs'] != self.player.inputs:
                    msg = pickle.dumps({'type':'inputs','inputs':self.player.inputs})
                    self.send(msg)
                if data['type'] == 'kick':
                    print('kicked from game...')
                    pygame.quit()
                    thread.interrupt_main()
                    sys.exit()
                if data['type'] == 'update' and data['timestamp'] > self.recent_timestamp:
                    # old way (no averaging)   
                    self.players = data['players']
                    self.player = next(x for x in data['players'] if x.username == self.player.username)

                    self.state = data['game_state']

                    self.recent_timestamp = data['timestamp']
                    
                
                    # future: Add averaging or some other method to predict other player positions better
                    # now = dict()
                    # for p in self.players:
                    #     now[p.username] = p
                    # for p in data['players']:
                    #     if p.username in now:
                    #         now[p.username] = p 
                    #     else:
                    #         self.players.append(p)
                
    def send(self, data):
        # create thread to send data
        # attach timestamp
        # try to send data to server, wait n ms for ack, maybe exp backoff
        # keep sending until ack or timeout
        self.socket.sendto(data, SERVER_ADDRESS)
        # print('sent data, waiting for ack')
        # keep going until ack? 
        # try:
        #     received = self.socket.recv(1024)
        # except socket.timeout:
        #     print("TIMEOUT")
        #     time.sleep(.5)
        # print('received ack')
        
    def login(self, username):
        self.send(pickle.dumps({'type':'login', 'username':username, 'return_port':self.socket.getsockname()[1]}))
        print('waiting for server ack and map info...')
    
    def event_loop(self):
        ''' events are passed to appropriate object'''
        for event in pygame.event.get():
            # print(event)
            if event.type == pygame.QUIT:
                self.done = True 
            # if an arrow key was pressed, pass it along to the player
            if event.type in [pygame.KEYDOWN,pygame.KEYUP] and event.key in ARROW_KEYS:
                self.player.handle_event(event)
                msg = pickle.dumps({'type':'inputs','inputs':self.player.inputs})
                self.send(msg)
    
    def draw(self):
        '''draw all elements to the display surface'''
        # black the screen
        self.screen.fill(BACKGROUND_COLOR)

        surface = pygame.Surface(SCREEN_SIZE, pygame.SRCALPHA)
        
        # draw the map 
        # create a camera Frame that will be relative to the map 
        Frame = np.zeros(SCREEN_SIZE)
        for wall in np.array(self.map.walls):
            wall[0] -= self.player.location[0] - SCREEN_SIZE[0]/2
            wall[1] -= self.player.location[1] - SCREEN_SIZE[1]/2
            wall[2] -= self.player.location[0] - SCREEN_SIZE[0]/2
            wall[3] -= self.player.location[1] - SCREEN_SIZE[1]/2
            
            pygame.draw.line(surface, (255,255,255,255), wall[:2], wall[2:], 3)

        for player in self.players:
            if player != self.player:
                x = int(player.location[0] - self.player.location[0] + SCREEN_SIZE[0]/2)
                y = int(player.location[1] - self.player.location[1] + SCREEN_SIZE[1]/2)

                # seeker will be red
                if player.role == "seeker":
                    color = (255,0,0,255)
                    bgcolor = (200,200,200,255)
                elif player.role == "ghost":
                    color = player.color + (50,)
                    bgcolor = player.color + (50,)
                else:
                    color = player.color + (255,)
                    bgcolor = player.bgcolor + (255,)
                # print(color)
                pygame.draw.circle(surface,bgcolor,(x,y), 12)
                pygame.draw.circle(surface,color,(x,y), 10)


                # draw usernames and scores above other players
                text = self.textfont.render(player.username[:6], True, (255,255,255))
                text_rect = text.get_rect(center=(x, y-40))
                surface.blit(text,text_rect)

                text = self.textfont.render(str(player.score), True, (255,255,255))
                text_rect = text.get_rect(center=(x, y-20))
                surface.blit(text,text_rect)

        
        # draw the player (always in the middle)
        # seeker will be red
        if self.player.role == "seeker":
            color = (255,0,0,255)
            bgcolor = (200,200,200,255)
        elif self.player.role == "ghost":
            color = self.player.color + (50,)
            bgcolor = self.player.color + (50,)
        else:
            color = self.player.color + (255,)
            bgcolor = self.player.bgcolor + (255,)

        pygame.draw.circle(surface,bgcolor,tuple(map(int,(SCREEN_SIZE[0]/2, SCREEN_SIZE[1]/2))), 12)
        pygame.draw.circle(surface,color,tuple(map(int,(SCREEN_SIZE[0]/2, SCREEN_SIZE[1]/2))), 10)
        # self.player.draw(self.screen)
        # self.bullets.draw(self.screen)

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

        self.screen.blit(surface,(0,0))

        pygame.display.update()
    
    
    def main_loop(self):
        '''main loop'''
        while not self.done:
            self.event_loop()
            self.update()
            self.draw()
            self.clock.tick(self.fps)

class HeadlessGameServer(Game):
    
    def __init__(self):
        # initialize game attrs
        Game.__init__(self)

        # create player list
        self.players = []
        self.seeker = None

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_addresses = set()
        
    
    # create UDP Server
    def setup_server(self):
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
    
    # what to do when packet received: 
    #   update player info, 
    #   send back ack
    #   broadcast death/player join? 
    def serve_forever(self):
        while True:
            try:
                data, address = self.socket.recvfrom(1024)
            
                # print('\treceived: %s bytes from %s' % (len(data), address))
                # print('\treceived: %s' % data)
                # print('\tunpickled:%s' % pickle.loads(data))
                # print()
                
                if data:
                    # print('\tparsing data...')
                    self.parse_data(data, address)
            except ConnectionResetError:
                # do something here to recover when a client is lost
                # self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                # print(socket.getfqdn())
                # print(socket.gethostbyname(socket.getfqdn()))
                # self.socket.bind((socket.gethostbyname(socket.getfqdn()),SERVER_ADDRESS[1]))
                print("connection lost")
    
    def parse_data(self, data, address):
        data = pickle.loads(data)
        
        if data["type"] == "login":
            # username already taken
            if [x for x in self.players if x.username == data['username']]:
                self.socket.sendto(pickle.dumps({'type':'login_ack','status':'bad'}), address)
            else:
                # ack
                self.socket.sendto(pickle.dumps({'type':'login_ack', 'status':'ok'}), address) # TODO: Send the map with a larger packet size?
                print('replied to %s login_ack' % data['username'])
                # register user
                newPlayer = Player([300,200],data['username'])
                newPlayer.address = address
                self.players.append(newPlayer)

                self.client_addresses.add((address[0],data['return_port']))

        if data["type"] == "inputs":

            # get the Player Object for the player
            client_player = [x for x in self.players if x.address == address]
            if client_player:
                # reply with ack
                self.socket.sendto(pickle.dumps({'type':'inputs_ack','inputs':data['inputs']}), address)
                print('replied to %s inputs_ack' % client_player[0].username)
                # apply inputs to player
                client_player[0].inputs = data['inputs']
            else:
                # reply with kick message if player is not registered
                self.socket.sendto(pickle.dumps({'type':'kick'}), address)
        
    
    def notify_clients(self):
        start = time.time()
        while True:
            # send along a timestamp! the client will only apply the most recent timestamp update
            timestamp = int((time.time()-start)*10) 
            # create update object to send 
            data = pickle.dumps({'type':'update','players':self.players,'game_state':self.state,'timestamp':timestamp})
            # send update to all clients
            for addr in self.client_addresses:
                # print(addr,data)
                self.socket.sendto(data, addr)
            
            time.sleep(0.200) # update clients at 200 ms interval
            
            
    def main_loop(self):
        '''main loop'''

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
        self.state="hiding"
        print("ROUND START...")

        for player in self.players:
            player.role = "hider"

        # randomly select a seeker
        self.seeker = random.choice(self.players)
        self.seeker.role = "seeker"

    def seeker_start(self):
        self.state = "seeking"
        print("SEEKER START...")


    def round_end(self):
        self.state = "waiting"
        print("ROUND END...")
        for player in self.players:
            if player.role == "hider":
                player.score += 1
            player.role = "ghost"

        self.seeker = None


