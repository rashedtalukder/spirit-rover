# PlumGeekPixelServer.py
# Author: Kevin King for Plum Geek LLC
#
# This script should be run in the background. It will set up a sockets
# server that will listen for pixel control messages.
# The TCP/IP port used can be changed by editing the SERVER_PORT number below.
# Look at the PixAnimation.py file for specific opearations that are available.


import time
import socket
import select
import sys
import PixAnimation as p

# Pixel Server Configuration:
SERVER_PORT = 20568
PACKET_LENGTH = (p.LED_COUNT * 3) + 1  # packet long enough to accept litteral
# individual rgb values for each pixel
# plus 1 for the first byte (which denotes
# the command/mode being used)


def checkSocks():
    global pixserver_running
    global socket_data
    global previous_data
    global PACKET_LENGTH

    # read the listen buffer for all 'input' devices, process if data present
    # otherwise, skip (this skip action is forced by the timeout "0" in
    # the select.select() function)
    inputready, outputready, exceptready = select.select(inputs, [], [], 0)
    for s in inputready:
        if s == server:
            # handle the server socket
            client, addr = server.accept()
            inputs.append(client)
            return 1

        else:
            # handle all other sockets
            s.setblocking(0)
            try:
                data = s.recv(PACKET_LENGTH)

                if data:
                    s.send(data)
                    if data != previous_data:  # if new data doesn't match old data
                        p.new_data = 1  # set the new data flag
                        previous_data = data  # update prev data to present data
                    # incoming packets are ASCII "field:field:..." strings
                    socket_data = data.decode("ascii", "ignore").split(':')
                else:
                    s.close()
                    inputs.remove(s)
                return 1
            except socket.error:
                pass
    return 1



# Main program logic follows:
if __name__ == '__main__':

    # Create NeoPixel object with appropriate configuration
    # strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)
    # strip.begin() # Intialize the library (must be called once before other functions)

    # create a socket server object
    # simple example: http://www.tutorialspoint.com/python/python_networking.htm
    # socket select example: http://ilab.cs.byu.edu/python/select/echoserver.html
    server = socket.socket()  # create a socket object
    host = socket.gethostname()  # get local machine name
    # reserve a port for the service (define at top of this script)
    port = SERVER_PORT
    server.bind((host, port))  # bind to the port
    server.listen(5)  # listen for client connections
    inputs = [server]  # input sources (socket server)
    pixserver_running = 1  # flag that keeps this process running
    previous_data = 0  # holder for previous
    # holder list for received data via socket
    socket_data = [0] * PACKET_LENGTH

    try:
        # print(" ")
        print("PlumGeek Pixel Server now servin' on port {}.".format(port))
        # print("Press Ctrl-C or Enter to exit.")
        # turn Status pixel green, indicates Pi is up and Pixel Server is running
        p.hue_pixel(0, 135, 80)
        while pixserver_running:
            checkSocks()
            # users can edit animations in PixAnimation.py file
            p.selectAnimation(socket_data)
            time.sleep(0.005)
        server.close()

    except KeyboardInterrupt:  # do this if interrupted with Ctrl-C on keybaord
        server.close()  # close the socket connection
        # print('')						#blank line
        print('Connections Closed.')  # message to user
