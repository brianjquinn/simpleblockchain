#!/usr/bin/python
# Brian Quinn - CS645 Network Security
# Project 3

# blockchain
# class used to manage and represent a node's blockchain

from block import Block
import logging
from random import SystemRandom

class Blockchain(object):

    MAGIC_NUMBER_MAX = 10

    def __init__(self, minerid):
        self.rand = SystemRandom()
        self.blocks = []
        self.magic_num = None
        self.miner = minerid

    # sets the magin number which is the target for mining operations
    # params:
    #   -magic_num - the value to set the magic number to or generate it randomly
    #   if None
    def set_magic_number(self, magic_num = None):
        if magic_num == None:
            self.magic_num = self.rand.randint(1,self.MAGIC_NUMBER_MAX)
        else:
            self.magic_num = magic_num

        logging.info("set magic number to: %d" % self.magic_num)

    # validates a new block based on block chain semantics to determine if it 
    # can be added to the blockchain
    # params:
    #   -new_block: the new block to verified
    # returns:
    #   -true if the block can be validly added to our blockchain, false otherwise
    def validate_newblock(self, new_block):
        valid_idx = False
        prev_hash_match = False

        #special case - first block
        if new_block.index == 0 and len(self.blocks) == 0:
            valid_idx = True
            prev_hash_match = new_block.previous_hash == 0
        elif len(self.blocks) > 0: 
            latest_block = self.blocks[-1]
            valid_idx = new_block.index == latest_block.index + 1
            prev_hash_match = latest_block.hash == new_block.previous_hash

        magic_num_match = new_block.data == self.magic_num

        return valid_idx and prev_hash_match and magic_num_match

    # adds a block to the blockchain
    # params:
    #   -block: the block to be added
    def add_block(self, block):
        self.blocks.append(block)

    # gets the latest block from the blockchain
    # returns:
    #   -the leatst block from the blockchain or None if the blockchain is empty
    def get_latest_block(self):
        if len(self.blocks) == 0:
            return None
        return self.blocks[-1]

    # performs the "mining" operations by generating a random number within 
    # the specified range
    # returns:
    #   -a new block if mining is successful, None otherwise
    def mine_block(self):
        random_num = self.rand.randint(1,self.MAGIC_NUMBER_MAX)
        # random_num = self.magic_num
        newblock = None
        # determine if we should create a new block
        if random_num == self.magic_num:
            if len(self.blocks) == 0:
                newblock = Block(0, 0, random_num, self.miner)
            else:
                latest_block = self.blocks[-1]
                newblock = Block(latest_block.index + 1, \
                    latest_block.hash, random_num, self.miner)

            self.add_block(newblock)
        else:
            logging.info("mining fail - generated number: %d " \
                "doesn't match magic number: %d" % (random_num, self.magic_num))

        return newblock

    # determines if the current latest block matches the passed in block
    # params:
    #   -block: the block to compare the current latest block against - generally
    #   from the GET_LATEST_BLOCK message from another peer
    def latest_block_matches(self, block):
        latest_block = self.blocks[-1]
        return latest_block == block

    # examines the list of blocks which represent a peer's blockchain, first it
    # checks to see if the blockchain is longer than its own copy, if so, it validates
    # it and then replaces its own block chain with listofblocks
    # params:
    #   -list of Block objects that repersent the blockchain to check
    def examine_peer_blockchain(self, listofblocks):
        if len(listofblocks) > len(self.blocks):
            logging.debug("blockchain received is longer than current blockchain")
            valid = True
            prevblock = listofblocks[0]
            for i in range(1, len(listofblocks)):
                currblock = listofblocks[i]
                if currblock.index != prevblock.index + 1:
                    valid = False
                    break
                if currblock.previous_hash != prevblock.hash:
                    valid = False
                    break
                if currblock.data != self.magic_num:
                    valid = False
                    break
                prevblock = currblock

            if valid:
                logging.info("blockchain received is valid - replacing")
                self.blocks = listofblocks
            else:
                logging.info("blockchain received is not valid - ignoring")
        else:
            logging.debug("peer blockchain len: %d, my blockchain len %d" \
                " - ignoring" % (len(listofblocks), len(self.blocks)))





