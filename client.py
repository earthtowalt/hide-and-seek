# client runner

from game import VisualGame

username = input("Enter your username: ")

game = VisualGame(username)
game.login(username)
game.main_loop()