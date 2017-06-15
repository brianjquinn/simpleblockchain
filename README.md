Brian Quinn - CS645 Network Security @ Drexel University

### Project Description

Your last project is to develop a small blockchain system.  You can feel free to model your basic system structure after the Bitcoin system, but you certainly don't need to implement all the details of Bitcoin.  Remember that the main thing that happens with the blockchain system is that a large number of entities exchange in a distributed record keeping activity.  Each entity can initiate an action.  By way of the blockchain, everyone involved agrees on exactly what actions have taken place.  Although those actions are financial transactions in Bitcoin, the basic idea could be used for any number of other things.  Almost certainly, it will be helpful for you to set up a scenario of what the actions are that will guide the development of your system.  For testing, you'll need to set up a group of these entities that communicate through some channels.  This can be done with network connections, or language-based message passing, or some other mechanism.  Of course, your overall submission needs to include both your source code and a writeup that goes over the design, an analysis of the cryptographic aspects, and your test results.

### Project Implementation and Details

The idea around this blockchain based implementation was to understand the semantics of a maintaining a distributed ledger using some of the blockchain concepts without the intricacies that comes with implementing a blockchain for something like Bitcoin. 

This implementation revolved around setting up peer to peer nodes that could be connected together at any point and sync up the state of this blockchain like data structure, while also simulataneiously trying to "mine" blocks. Mining is vasty simplified and is described later.

The center of this implementation is with the blockchainnode.py (BlockchainNode class). The Blockchainnode is implemented in a way so that an initial node can be setup, then subsequent nodes can be spun up to point at already running peers. For example, to setup a peer to peer network in which each node has 2 peers (a triangular formation) you could do the following:

A<--->B<--->C<--->A

    python blockchainnode.py -d -p 10000
    python blockchainnode.py -d -p 10001 --peers localhost:10000
    python blockchainnode.py -d -p 10002 --peers localhost:10000 localhost:10001

or a configuration like so: A<-->B<-->C would be accomplished like this:

    python blockchainnode.py -d -p 10000
    python blockchainnode.py -d -p 10001 --peers localhost:10000
    python blockchainnode.py -d -p 10002 --peers localhost:10001

-d enableds DEBUG level logging, default level is INFO

The -p option specifies the port on the current machine that the node will be listening for connections/messages on.

    python blockchainnode.py -h will show the command line options

An initial node should be setup without specifying peers via the --peers argument. Further nodes need to specify their peers via the --peers argument where each peer is defined by ip:port and separated by a space. If a given node cannot connect to peers specified by the command line the user will be notified and the node will not start.

### Node Operation

A node when started essentially alternates between doing the following 2 things:

    1. Trying to accept connections for 5 second intervals and processing the messages that come from those connections in a seperate thread. 
    2. Maintaining the digital ledger data structure by mining and asking peers for information it needs (such as the latest block or the whole block chain itself)

The data structure representing the distributed ledger or blockchain is essentially a list of Block objects (block.py) where each block has the following fields:

    index - 0 based indexed for blocks in the blockchain
    previous hash - the sha-256 hash of the previous block in the blockchain
    timestamp - time the block was "mined"
    data - data wishing to be associated with the block
    mined by - the node in this system who "mined" the block
    hash - a SHA-256 hash of index, previous hash, timestamp, data and mined by

That way integrity is maintained because the latest block's hash is dependent on the previous block's hashes (all hashes are SHA-256).

A new block is "mined" and broadcasted to the other connected nodes in the network who validate the block and add it to their copy of the blockchain by checking the following:

    if newblock is the block to be added and latestblock is the latest block in the chain:

    newblock.index = lastestblock.index + 1
    newblock.previoushash = latestblock.hash
    newblock.data = the agreed upon "magic number" (explained in Mining later)

Furthermore, every X (default 10) amount of timeouts listening for peers, a node will request the latest block in the blockchain from its peers. If differences are found between its own latest block and received latest blocks, the node will request the entire blockchain from its peers. This is where the longer-chain-wins rules comes into effect.

If the blockchain it receives is longer than it's own, the received blockchain will replace the node's original copy and the node will continue on. This presents a situation where histories could differ however, the node's history who has done the most cumulative work (ie. you have random genereated the magic number the most times) will eventually be propagated throughout the network.

### Mining

The process of adding blocks to the blockchain (mining) is vastly oversimplied just to demonstrate the concept that a digital ledger can be maintained across network connected nodes.

When a node starts up, before it starts mining, it will request from it's peers the "magic number". The magic number is decided by the first node that is started in the network (ie. a node that is not given any peers via --peers argument), a genesis node if you will.

This magic number is just a random integer between 1 and 10, but it's what drives the "mining" process in this implementation. When a node wants to add a block to the blockchain it must generate a random number. If that random number matches the "magic number", it will create a new block based on the sementatics of the Blockchain data structure and broadcast it to its peers so they can validate it, and add it to their block chain.

### Test Results

The system was tested with 2, 3 and 4 node configurations running on the same machine. I did, also try a 2 node configuration on seperate machines just to test non-localhost host communication on a LAN. Since, a 5 second time was used, studying the logs was the best way to test the implementation. On each 5 second timeout, the node would print out its blockchain length and its full blockchain in human readable form. The way I tested it was I would let 3 nodes run for about 20 minutes and take their last print out of the blockchain. Then I diffed each node's printout of the blockchain and saw they were all the same. This told me that my distributed record keeping activity implementation was successful.

### Summary

All-in-all the code in this project implements a distributed record keeping activity with Blockchain semantics. A node essentially listens for connections from known peers and exchanges different message types (defined in blockchainmsg.py) that aid in maintaining N copies of a blockchain like data structure across machines. At the same time a node is attempting to perform a very simple "proof of work" in order to add a record (block) to the chain by generating a random number and hoping it is equal to the agreed upon target value. The data contained in these "mined" blocks is arbritrary (but in this case its the agreed upon target number) since the goal of the implementation was to display a distributed record keeping activity amongst network connected nodes. In this case the record to keep is in the order which network connected nodes generate an agreed upon random number on a continuous basis. The hashing comes into play to ensure validity of ordering in the longest current chain in the network.

The data stored in these blocks could be anything, and the mining function could easily be replaced. What this project provides is a p2p messaging functionality to continuously keep track of a blockchain data structure in a distributed and decentralized manner and to perform some given mining function. The transactions or data that pile up between blocks being mined (and subsequently stored in those blocks) could be made application specific.
