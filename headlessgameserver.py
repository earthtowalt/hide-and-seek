import socket
import threading 
import random 
import time
import pickle

from game import Game 
from player import Player

from config import *


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

        # create an initial map for the game
        self.map_seed = random.randint(1,100)
        print('generating initial map with seed: %d' % self.map_seed)
        self.map = self.generate_map(self.map_seed)

        # use this to notify all players when their 
        self.countdown_timer = None
    
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
                data, address = self.socket.recvfrom(MAX_PACKET)
                if data:
                    self.parse_data(data, address)
            except ConnectionResetError:
                # TODO do something here to recover when a client has disconnected?
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
                # print('replied to %s login_ack' % data['username'])
                # register user
                newPlayer = Player(MAP_CENTER,data['username'])
                newPlayer.address = address
                newPlayer.last_active = time.time()
                newPlayer.last_timestamp = data['timestamp']
                self.players.append(newPlayer)
                print("login: %s" % newPlayer.username)
                
        # handle client inputs
        if data["type"] == "inputs":
            # get the Player Object for the player
            client_player = [x for x in self.players if x.address == address]

            # reply with kick message if player is not registered
            if not client_player:
                self.socket.sendto(pickle.dumps({'type':'kick'}), address)

            # if this is the most recent client-timestamp
            elif client_player and data['timestamp'] >= client_player[0].last_timestamp:
                # reply with ack
                self.socket.sendto(pickle.dumps({'type':'inputs_ack','inputs':data['inputs']}), address)
                print('replied to %s inputs_ack' % client_player[0].username)
                # apply inputs to player
                # print('setting inputs for:',client_player[0].username,'inputs are:',data['inputs'])
                client_player[0].inputs = data['inputs']
                client_player[0].last_timestamp = data['timestamp']

                # prevent timeout
                client_player[0].last_active = time.time()
                
    def kick_inactive(self):
        # kick any inactive players
        inactive = []
        for player in self.players:
            if time.time() - player.last_active > INACTIVE_TIME:
                inactive.append(player)
        for player in inactive:
            print('kicking: %s' % player.username)
            self.socket.sendto(pickle.dumps({'type':'kick'}), player.address)
            self.players.remove(player)
    
    def notify_clients(self):
        '''Send gamestate information to all clients at intervals'''
        start = time.time()
        while True:
            # send along a timestamp! the client will only apply the most recent timestamp update
            timestamp = int((time.time()-start)*10) 
            # create update object to send 
            data = pickle.dumps({'type':        'update',
                                 'players':     self.players,
                                 'game_state':  self.state,
                                 'map_seed':    self.map_seed,
                                 'timestamp':   timestamp})
            # send update to all clients
            for p in self.players:
                addr = p.address
                # print(addr,data)
                self.socket.sendto(data, addr)
                # print("notifying: %s:%d" % addr)
            
            time.sleep(0.100) # update clients at 100 ms interval
            
            
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
                    p.speed = GHOST_SPEED
                    self.seeker.score += 2

            # handle game state changes
            if len(self.players) < 2:
                self.state = "waiting"
                reset_time = time.time()
                self.kick_inactive()
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

        # reset all players
        for player in self.players:
            player.role = "hider"
            player.speed = HIDER_SPEED
            player.location = MAP_CENTER.copy()
            player.location[0] += random.uniform(-25,25)
            player.location[1] += random.uniform(-25,25)

        # randomly select a seeker
        self.seeker = random.choice(self.players)
        self.seeker.role = "seeker"
        self.seeker.speed = SEEKER_SPEED

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
            player.speed = GHOST_SPEED

        self.seeker = None

        self.kick_inactive()

        # start generating the next map
        self.map_seed = random.randint(1,100)
        print('generating new map with seed: %d' % self.map_seed)
        self.map = self.generate_map(self.map_seed)