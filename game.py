import pygame
import os, sys
import numpy as np
import socket 
import pickle
import threading
import time
import random

from mapmaker import Maze
from player import Player

from config import *

# TODO figure out self.start_time, start_time
# TODO Seeker countdown

# TODO stress test the max number of players
# TODO handle when there are more players than the byte-size can handle

# TODO combine map segments to reduce number of walls
# TODO Allow player to move diagonally along wall
# Create a config.txt file so that changing parameters like 
#      serveraddress, etc. does not need to be commits to the game file.
# put each class in a file

# send professor setup email
# TODO Write-up
# TODO Presentation

class Game:
    '''Base Game class'''
    def __init__(self):
        '''Create the game basics and map'''
        
        # game fps and loop condiiton
        self.done = False
        self.clock = pygame.time.Clock()
        self.fps = 30
        self.state = "waiting"

        # create an empty list for the players
        self.players = []

        # setup map -- a list of coordinate pairs
        self.map_seed = -1
        self.map = []
        
        # set a start timer for timestamps
        self.start_time = time.time()
    

    def update(self):
        '''update all bullets, and the player motion'''
        for player in self.players:
            if not (player.role == 'seeker' and self.state == 'hiding'):
                player.update_location(self.map)
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

    def generate_map(self,seed):
        maze = Maze(20,20,10,10)
        maze.make_maze(seed)
        return maze.get_wall_list()
