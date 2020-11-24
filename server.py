from game import HeadlessGameServer

server = HeadlessGameServer()
server.setup_server()
server.main_loop()