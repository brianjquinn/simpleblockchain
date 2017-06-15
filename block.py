#!/usr/bin/python
# Brian Quinn - CS645 Network Security
# Project 3

# block
# class used to represent a single block in the blockchain

import logging
import time
import hashlib

class Block(object):

    def __init__(self, idx, prev_hash, data, miner):
        self.index = idx
        self.previous_hash = prev_hash
        self.timestamp = time.time()
        self.data = data
        self.mined_by = miner
        self.hash = hashlib.sha256(str(self.index) + str(self.previous_hash)
            + str(self.timestamp) + str(self.data) + self.mined_by).hexdigest()
        
    def __repr__(self):
        return "\n{\nindex: %d,\nprevious hash: %s,\ntimestamp: %s,\ndata: %s,\n" \
                "hash: %s,\nmined by: %s\n}" % (self.index, self.previous_hash, \
                self.timestamp, self.data, self.hash, self.mined_by)

    def __eq__(self, other):
        if other == None:
            return False
        idx= self.index == other.index
        p_hash = self.previous_hash == other.previous_hash
        ts = self.timestamp == other.timestamp
        data = self.data == other.data
        mb = self.mined_by == other.mined_by
        h = self.hash = other.hash
        return idx and p_hash and ts and data and mb and h
