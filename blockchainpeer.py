#!/usr/bin/python
# Brian Quinn - CS645 Network Security
# Project 3

# blockchainpeer
# represents a peer (remote or local) blockchainnode

import socket
from blockchainmsg import BlockchainMessage
import logging
import pickle
import struct

class BlockchainPeer(object):

    def __init__(self, host, port, clientsock = None):
        self.host = host
        self.port = port
        self.id = None
        if clientsock == None:
            self.sock = self.init_sock()
        else:
            self.sock = clientsock

    # initializes the socket object and sets the host, port and id
    # for this object
    def init_sock(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        addrinfo = socket.getaddrinfo(self.host, self.port, socket.AF_INET, socket.SOCK_STREAM)
        socktype = addrinfo[0]
        self.host = socktype[4][0]
        self.port = socktype[4][1]
        self.id = self.host + ":" + str(self.port)
        return sock

    # sends a message to the peer defined by this object
    # params:
    #   -senderid: the id of the node sending a message to this peer
    #   -msg_type: the type of message to be sent
    #   -data: the data portion of the message to be sent
    def send_msg(self, senderid, msg_type, data = None):
        msg_obj = BlockchainMessage(senderid, msg_type, data)
        serialized_msg =  pickle.dumps(msg_obj)
        logging.debug("sending length is %d" % len(serialized_msg))
        length_struct = struct.Struct("!I")
        length = length_struct.pack(len(serialized_msg))
        logging.debug("connecting and sending %s to peer: %s" % (repr(msg_obj), self))
        msg = length + serialized_msg
        self.sock.connect((self.host, self.port))
        self.sock.sendall(msg)
        self.sock.close()
        self.sock = self.init_sock()

    def __repr__(self):
        return "[ %s ]" % (self.id)
