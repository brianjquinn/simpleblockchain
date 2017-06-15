#!/usr/bin/python
# Brian Quinn - CS645 Network Security
# Project 3

# blockchainnode
# a peer to peer blockchain node

# usage: blockchainnode [-h] [-d] [-p PORT] [--peers [PEERS [PEERS ...]]]

# optional arguments:
#   -h, --help            parameter help
#   -d, --debug           flag that sets log level to DEBUG (INFO by default)
#   -p PORT, --port PORT  sets the server port to listen for connections on arbitrarily selected otherwise
#   --peers [PEERS [PEERS ...]] space seperated list of peers in the form host:port

import argparse
from blockchainpeer import BlockchainPeer
from blockchainmsg import BlockchainMessage
from blockchain import Blockchain
import logging
import pickle
import socket
import string
import struct
import sys
import threading

class BlockchainNode(object):

    #socket timeout in seconds
    CONNECTION_LISTEN_TIMEOUT = 5
    # the number of timesouts that need to occur before we ask our peers about
    # the blockchain
    SYNC_BLOCKCHAIN_TIMEOUTS = 10

    def __init__(self, port, peers):
        self.serverhostname = None
        self.serverport = None
        self.id = None
        self.serversock = self.__init_server_socket(port)
        self.blockchain = Blockchain(self.id)
        self.peers = {}
        # map of message types to handlder functions
        self.handlers = {
            BlockchainMessage.PEER_INIT : self.__handle_peer_init_msg,
            BlockchainMessage.PEER_REMV : self.__handle_peer_remv_msg,
            BlockchainMessage.GET_BLOCKCHAIN : self.__handle_get_blockchain_msg,
            BlockchainMessage.FULL_BLOCKCHAIN : self.__handle_full_blockchain_msg,
            BlockchainMessage.NEW_BLOCK : self.__handle_new_block_msg,
            BlockchainMessage.GET_LATEST_BLOCK : self.__handle_get_latest_block_msg,
            BlockchainMessage.LATEST_BLOCK : self.__handle_latest_block_msg,
            BlockchainMessage.GET_MAGIC_NUM : self.__handle_get_magic_num_msg,
            BlockchainMessage.NEW_MAGIC_NUM : self.__handle_new_magic_num_msg
        }
        self.shutdown = False
        self.sync_count = 0

        self.lock = threading.RLock()

        # fire up the node
        self.start(peers)

    # starts the blockchainnode's main server listening loop, and spawing the
    # mining thread as well
    # params:
    #   -possiblepeers: a list of peers to establish on startup (these are passed
    #   in from the command line)
    def start(self, possiblepeers):

        if len(possiblepeers) > 0:
            logging.info("establishing peers from passed in list")
            self.peers = self.__establish_peers(possiblepeers)
        else:
            self.blockchain.set_magic_number()

        logging.info("BLOCKCHAIN NODE STARTED - %s:%d" %\
            (self.serverhostname, self.serverport))
        while not self.shutdown:
            try:
                logging.debug("listening for peer connections")
                clientsock, clientaddr = self.serversock.accept()
                clientsock.settimeout(None)
                peerconn_thread = threading.Thread(target = \
                    self.__handlepeerconnectandrecv, args = [ clientsock ])
                peerconn_thread.start()
            except socket.timeout:
                self.__maintain_bc_and_mine()
                self.lock.acquire()
                self.sync_count = (self.sync_count + 1) % 10
                self.lock.release()
                continue
            except KeyboardInterrupt:
                logging.debug("ctrl+c pressed")
                self.shutdown = True
                continue

        logging.debug("peer connection listening loop ending")
        logging.debug("closing server socket")
        self.serversock.close()
        logging.info("notifying peers to remove me from their peer list")
        self.__broadcast_to_peers(BlockchainMessage.PEER_REMV)

    # initializes the server socket for the blockchainnode
    # params:
    #   -port: the port on which the server socket should listen
    #   -queue_size: the number of connections that will be queued 
    #   (not socket.accept()'ed) before refusing connections
    def __init_server_socket(self, port, queue_size = 5):
        logging.debug("initializing server socket")
        # IPv4 (AF_INET) TCP (SOCK_STREAM) socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # allow for the socket to be reclaimed before it's TIMEWAIT
        # period is finished
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", port))
        sock.settimeout(self.CONNECTION_LISTEN_TIMEOUT)
        addrinfo = socket.getaddrinfo("", port, socket.AF_INET, socket.SOCK_STREAM)
        sockinfo = addrinfo[0]
        self.serverhostname = sockinfo[4][0]
        self.serverport = sockinfo[4][1]
        self.id = self.serverhostname + ":" + str(self.serverport)
        sock.listen(queue_size)
        return sock

    # called when the socket times out in the main loop - this checks the blockchain
    # sends out any messages when information is needed and attempts to mine a block
    def __maintain_bc_and_mine(self):
        self.lock.acquire()
        logging.debug("number of peers: %d" % len(self.peers))
        logging.debug("sync count = %d" % self.sync_count)
        if self.blockchain.magic_num == None:
            self.__broadcast_to_peers(BlockchainMessage.GET_MAGIC_NUM)
        else:
            if len(self.blockchain.blocks) == 0 and len(self.peers) > 0:
                logging.debug("blockchain is empty but I have peers - request the blockchain")
                self.__broadcast_to_peers(BlockchainMessage.GET_BLOCKCHAIN)
            elif self.sync_count == 9:
                logging.debug("10 timeeouts - request the latest block")
                self.__broadcast_to_peers(BlockchainMessage.GET_LATEST_BLOCK)

            logging.debug("current blockchain length %d" % len(self.blockchain.blocks))
            logging.debug("current blockchain: %s" % self.blockchain.blocks)
            newblock = self.blockchain.mine_block()
            if newblock != None:
                logging.info("new block mined:%s" % newblock)
                self.__broadcast_to_peers(BlockchainMessage.NEW_BLOCK, newblock)
        self.lock.release()
            
    # handles an incoming connection from another blockchainnode
    # params:
    #   -clientsock: the client socket extracted from the accepted connection
    def __handlepeerconnectandrecv(self, clientsock):
        host, port = clientsock.getpeername()
        logging.info("handling peer connection from: %s:%d" % (host, port))
        try:
            raw_msg = clientsock.recv(1024)
            length = struct.unpack_from("!I", raw_msg[:4])[0]
            bytes_recvd = len(raw_msg[4:])
            logging.debug("length: %s, bytes_recvd: %d" % (length, bytes_recvd))
            while bytes_recvd < length:
                chunk = clientsock.recv(1024)
                raw_msg += chunk
                bytes_recvd += len(chunk)
                logging.debug("length: %s, bytes_recvd: %d" % (length, bytes_recvd))

            msg = pickle.loads(raw_msg[4:])

            logging.info("received message: %s", repr(msg))

            if msg.msg_type == BlockchainMessage.PEER_INIT or \
            msg.msg_type == BlockchainMessage.PEER_REMV:
                self.handlers[msg.msg_type](msg)
            else:
                peerid = msg.senderid
                self.lock.acquire()
                peer = None
                if self.peers.has_key(peerid):
                    peer = self.peers[peerid]
                    self.lock.release()
                    if self.handlers.has_key(msg.msg_type):
                        self.handlers[msg.msg_type](peer, msg)
                    else:
                        logging.info("received unknown message type: " \
                            "%s - doing nothing" % (str(msg.msg_type)))
                else:
                    logging.info("peerid not an established peer - doing nothing")
                    self.lock.release()
        except Exception:
            logging.error("An exception occured handling connection/receving message")
            raise
        finally:
            logging.debug("cleaning up client socket")
            clientsock.close()

    # handles the PEER_INIT message type
    # params: 
    #   -message: the messsage to process
    def __handle_peer_init_msg(self, message):
        logging.debug("processing PEER_INIT message")
        peer = self.__peer_from_peerid(message.senderid)

        if not self.peers.has_key(peer.id):
            logging.info("storing: %s as established peer" % repr(peer))
            self.lock.acquire()
            self.peers[peer.id] = peer
            self.lock.release()
        else:
            logging.debug("already established this peer: %s, ignoring" % repr(peer))
        
    # handles PEER_REMV message type
    # params:
    #   -message: the message to process
    def __handle_peer_remv_msg(self, message):
        peeridtoremove = message.senderid
        self.lock.acquire()
        if self.peers.has_key(peeridtoremove):
            logging.info("removing peer: %s" % (self.peers[peeridtoremove]))
            del self.peers[peeridtoremove]
        else:
            logging.debug("received PEER_REMV from peer not in my list - ignoring")
        self.lock.release()

    # handles GET_BLOCKCHAIN message type
    # params:
    #   -peer: the peer who sent the message
    #   -message: the message to process
    def __handle_get_blockchain_msg(self, peer, message):
        logging.info("handling GET_BLOCKCHAIN message")
        self.lock.acquire()
        if len(self.blockchain.blocks) > 0:
            peer.send_msg(self.id, BlockchainMessage.FULL_BLOCKCHAIN, self.blockchain.blocks)
        else:
            logging.debug("my blockchain is empty - ignoring message")
        self.lock.release()

    # handles FULL_BLOCKCHAIN message type
    # params:
    #   -peer: the peer who sent the message
    #   -message: the message to process
    def __handle_full_blockchain_msg(self, peer, message):
        logging.info("handling FULL_BLOCKCHAIN message")
        listofblocks = message.data
        self.lock.acquire()
        self.blockchain.examine_peer_blockchain(listofblocks)
        self.lock.release()

    # handles NEW_BLOCK message type
    # params:
    #   -peer: the peer who sent the message
    #   -message: the message to process
    def __handle_new_block_msg(self, peer, message):
        logging.info("handling NEW_BLOCK message")
        newblock = message.data
        self.lock.acquire()
        if self.blockchain.validate_newblock(newblock):
            logging.info("new block is valid - adding")
            self.blockchain.add_block(newblock)
        else:
            logging.info("new block received is not valid - request block chain from peers")
            self.__broadcast_to_peers(BlockchainMessage.GET_BLOCKCHAIN)
        self.lock.release()

    #handles GET_LATEST_BLOCK message type
    #params:
    #   -peer: the peer who sent the message
    #   -message: the message to process
    def __handle_get_latest_block_msg(self, peer, message):
        logging.info("handling GET_LATEST_BLOCK message")
        self.lock.acquire()
        latest_block = self.blockchain.get_latest_block()
        if latest_block == None:
            logging.debug("no latest block to send - ignoring")
        else:
            peer.send_msg(self.id, BlockchainMessage.LATEST_BLOCK, latest_block)
        self.lock.release()

    #handles LATEST_BLOCK message type
    #params:
    #   -peer: the peer who sent the message
    #   -message: the message to process
    def __handle_latest_block_msg(self, peer, message):
        logging.info("handling LATEST_BLOCK message")
        peer_latest_block = message.data
        self.lock.acquire()
        if self.blockchain.latest_block_matches(peer_latest_block):
            logging.info("latest block matches - I'm up to date")
        else:
            logging.info("my latest block didn't match peers latest - requesting the blockchain")
            self.__broadcast_to_peers(BlockchainMessage.GET_BLOCKCHAIN)
        self.lock.release()
    # handles GET_MAGIC_NUM message type
    # params:
    #   -peer: the peer who sent the message
    #   -message: the message to process
    def __handle_get_magic_num_msg(self, peer, message):
        logging.info("handling GET_MAGIC_NUM message")
        self.lock.acquire()
        if self.blockchain.magic_num != None:
            peer.send_msg(self.id, BlockchainMessage.NEW_MAGIC_NUM, self.blockchain.magic_num)
        else:
            logging.debug("my magic num isn't set - ignoring message")
        self.lock.release()

    # handles NEW_MAGIC_NUM message type
    # params:
    #   -peer: the peer who sent the message
    #   -message: the message to process
    def __handle_new_magic_num_msg(self, peer, message):
        logging.info("handling NEW_MAGIC_NUM message")
        magic_num = message.data
        self.lock.acquire()
        self.blockchain.set_magic_number(magic_num)
        self.lock.release()

    # attemps to establish a connection and store references to peers
    # params:
    #   -peerlist: command line supplied list of peers, each peer is in the 
    #   form <host>:<port>
    # returns:
    #   -a dictionary of id's to BlockchainPeer objects
    def __establish_peers(self, peerlist):
        established_peers = {}
        for peer in peerlist:
            peer = self.__peer_from_peerid(peer)
            if peer != None:
                try:
                    peer.send_msg(self.id, BlockchainMessage.PEER_INIT)
                    established_peers[peer.id] = peer
                except socket.error as e:
                    logging.error("socket error sending message to potential peer: %s" % e)
                    logging.info("check the validity of peers passed in from the command line")
                    sys.exit(1)
            else:
                raise AttributeError("invalid peer format, expecting host:port")

        return established_peers

    # creates a BlockchainPeer object from an id (ip:port)
    # params:
    #   -peerid: the string peerid to be converted to a BlockchainPeer object
    # returns:
    #   -a BlockchainPeer object if peerid is valid, otherwise None
    def __peer_from_peerid(self, peerid):
        if string.count(peerid, ":") == 1:
            peer_split = string.split(peerid, ":", 1)
            peer_host = peer_split[0]
            peer_port = int(peer_split[1])
            return BlockchainPeer(peer_host, peer_port)
        return None

    # sends a message to all known peers
    # params:
    #   -msg_type: the type of message to send
    #   -data: the data to include in the message
    def __broadcast_to_peers(self, msg_type, data = None):
        self.lock.acquire()
        for peer in self.peers.values():
            peer.send_msg(self.id, msg_type, data)
        self.lock.release()

if __name__ == "__main__":
    argparser = argparse.ArgumentParser(prog="blockchainnode")

    # pass in the -d or --debug to set logging to level=DEBUG, otherwise 
    # it defaults to level=INFO 
    argparser.add_argument("-d", "--debug", action="store_const", const=logging.DEBUG, 
        dest="log_level", default=logging.INFO)

    # pass in -p PORT or --port=PORT/--port PORT to set the port for the node to use
    argparser.add_argument("-p","--port", dest="port", type=int, default=0)

    # pass in --peers hostname:port hostname2:port2... to define a list of peers
    # for this node
    argparser.add_argument("--peers", nargs="*", default=[])

    # get the args passed in from command line
    args = argparser.parse_args()

    # configure the logger
    logging.basicConfig(level=args.log_level, format="%(asctime)s - " \
        "%(levelname)s:(%(threadName)s) - %(message)s")

    # create the node (which also starts it)
    node = BlockchainNode(args.port, args.peers)