import time
import json
from block import Block
import database

blockchain = []

def init_blockchain():
    """Initialize the blockchain with a genesis block if empty."""
    database.init_db()
    last_block = database.get_last_block()

    if last_block is None:
        genesis_block = Block(0, "0", time.time(), [{"genesis": True}], "genesis")
        database.insert_block(genesis_block)
        blockchain.append(genesis_block)
    else:
        blockchain.append(Block(*last_block[:5]))  # Load last block into memory

def get_latest_block():
    return blockchain[-1]
