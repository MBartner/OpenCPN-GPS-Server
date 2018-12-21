#!/usr/bin/python

import argparse
import sys
import signal
import socket
import select
import serial


server = None


# Close socket on keyboard interrupt
def signalHandler(signal, frame):
    if server is not None:
        server.close()
    sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", dest="port", required=True)
    parser.add_argument("-d", dest="dev", required=True)
    parser.add_argument("-b", dest="baud", required=True)
    arguments = parser.parse_args()
    args = vars(arguments)

    IP = ''                        # defaults to localhost (127.0.0.1)
    PORT = int(args['port'])       # Arbitrary port number
    dev = args['dev']              # Ex: '/dev/ttyUSB0'
    baud_rate = int(args['baud'])  # Ex: 4800

    # Allows server to close cleanly
    signal.signal(signal.SIGINT, signalHandler)

    # *** Set up server ***
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.setblocking(0)
        server.bind((IP, PORT))
    except socket.error, msg:
        sys.stderr.write("socket.socket(): %s\n" % msg[1])
        sys.exit(1)
    server.listen(10)
    print "Server running on port %d..." % PORT
    # *** Server set up complete ***

    # Open gps on serial port
    ser = serial.Serial(dev, baud_rate, timeout=5)

    socks = [server]  # List of sockets
    addrs = {}        # Dictionary mapping sockets to their IP and port tuples

    # Server will run forever unless interrupted or error occurs
    while True:
        if len(socks) == 1:
            # This line essentially just checks if there is a new connection.
            #   In this particular case there are no clients connected so the
            #   program will wait here until a new client connects.
            readable, writable, errored = select.select(socks, [], [])
        else:
            # If there are clients connected, we check here real quick, but if
            #   there are no new connections, we still continue with the program.
            readable, writable, errored = select.select(socks, [], [], 0)

        # Add new connections if they are available
        for s in readable:
            if s is server:
                client, client_addr = server.accept()
                socks.append(client)
                addrs[client] = client_addr
                print "Connected to: %s on port %d" % (client_addr[0], client_addr[1])

        # Send data to all connected clients (who aren't ourself)
        for s in socks:
            if s is not server:
                try:
                    s.send(ser.readline().strip("\r\n"))
                except socket.error, msg:
                    socks.remove(s)  # Remove socket
                    print "Disconnected from: %s on port %d" % (addrs[s][0], addrs[s][1])
                    del addrs[s]     # Remove dictionary entry
