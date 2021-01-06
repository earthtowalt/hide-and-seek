# Hide and Seek Game
Created for the EECE 4371 final project

## Steps to run: 
- run the server.py script and take note of the address (can be run on local network or hosted on hosting service)
- change the SERVER_ADDRESS variable the server ip in the config.py file
- run client.py

## Gameplay
The objective of the game is to catch the other players when you are the seeker and to hide from the seeker when you are a hider. The seeker is always red and the hiders are random colors. The server will be in the waiting state until at least two clients join. Then the game will cycle between the waiting, hiding, and seeking states. In the hiding state, a seeker is chosen and all other players will get a few seconds to run into the maze and hide. Then, the seeker is allowed to move and tries to chase down and catch as many players as possible. Points will be awarded based on whether the seeker catches a player or whether a player survives a round.  
  
I chose this project because I already have some experience in game development, and I wanted to apply what I learned about network protocol to make a multiplayer game. 

## Implementation
A central server runs the actual game (server.py). Players can connect to the game by running client.py. When a player connects, they will see a GUI popup where they can move around and see other players. The gui is implemented in pygame. It handles player inputs and displays the graphics for the game. The networking is done with UDP. It was chosen over TCP because I wanted packets to be sent as soon as possible and I wanted to easily be able to handle multiple connections to different clients.  

### Protocol
Every packet sent is a pickled dictionary. There will be a key 'type' that determines the type of message. These are the message types, along with other fields of the message:
- client
  - login :- username, timestamp
  - inputs :- inputs, timestamp
- server
  - login_ack :- status
  - inputs_ack :- inputs
  - update :- players, game_state, map_seed, timestamp
  - kick  
  
### Threading
The client's main thread handles player inputs, updates the display, and simulates the game. It has a separate thread for listening for messages from the server.  
The server's main thread simulates the game and keeps track of the time to update the gamestate. It has a separate thread for listening to inputs from the client and another thread to update each client on ~100 ms intervals. 

## Issues
A few of the main issues that I faced were *packet loss*, *latency*, and *random map generation*.  

I implemented a timestamp system in the client's input updates that lets the server know which set of inputs is the correct one to use (the last sent packet). This helps with packets arriving out of order to the server. The client also checks on every server update to make sure that the server has the most recent inputs. If the server is telling the client that it has inputs that differ from what the client wants, then the client will resend the correct inputs until a server update comes back with the correct inputs. This can help with packet loss.  

Latency was an issue that I was not able to completely solve. It takes time for the packets to move from client to server and vice versa. The effects of latency can be seen when you press the right arrow. On your screen, your player will start moving instantly, but the server doesn't know you have moved yet, so you will snap back to your original position until the server receives your input packet, and then you will start moving smoothly to the right. One fix that helped with the jumpiness was to decrease the server update delay from 200 ms to 100 ms. There is still room for improvement here.  

One other struggle I had was synchronizing the map across all of the different players. I implemented the map as a list of walls, each wall represented by 4 numbers: (x1,y1,x2,y2). Originally I was sending the list of walls in the game updates, but this was not feasible once I implemented the large maze map. Instead, I started to generate the map from a random seed, so that the client can receive the new seed from the server, then generate an identical map on the client-side. 

## Future Work
A better system for motion prediction could be implemented on the client side for the movements of other players. Also, the server could take into account the time it takes for a packet to travel from the client to the server and retroactively apply the input change in some way. 
