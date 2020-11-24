import socket


ADDRESS = ('127.0.0.1', 10001) 

# SOCK_DGRAM is the socket type to use for UDP sockets
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# As you can see, there is no connect() call; UDP has no connections.
# Instead, data is directly sent to the recipient via sendto().
msg = bytes('hello!\n', "utf-8")
sock.sendto(bytes('hello!\n', "utf-8"), ADDRESS)
print("Sent:     {}".format(msg))

received = sock.recv(1024)
print("Received: {}".format(received))