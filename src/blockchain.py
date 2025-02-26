import time
import json
import database
from block import Block

blockchain = []

def init_blockchain():
    """Initialize blockchain with the genesis block if empty."""
    last_block = database.get_last_block()
    if not last_block:  # No blocks found, create genesis block
        genesis_block = Block(0, "0", time.time(), [{"genesis": True}], "genesis")
        database.save_block(genesis_block)


def add_block(data, proposer):
    """Create and add a new block to the blockchain."""
    last_block = blockchain[-1]
    new_block = Block(last_block.index + 1, last_block.hash, time.time(), data, proposer)
    blockchain.append(new_block)
    database.insert_block(new_block)
    return new_block
