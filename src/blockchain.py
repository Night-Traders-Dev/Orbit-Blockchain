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
    """Retrieve the latest block from the blockchain."""
    return blockchain[-1] if blockchain else None

def get_blockchain():
    """Retrieve the full blockchain from the database."""
    blocks = database.get_all_blocks()
    return [Block(*block[:5]) for block in blocks]

def get_blockchain_stats():
    """Retrieve blockchain statistics for the explorer."""
    total_blocks = database.get_block_count()
    transactions = database.get_all_transactions()

    total_transactions = len(transactions)
    total_amount_sent = sum(float(tx["amount"]) for tx in transactions)
    total_fees_collected = sum(float(tx["fee"]) for tx in transactions)

    last_five_tx = transactions[-5:] if len(transactions) >= 5 else transactions

    return {
        "total_blocks": total_blocks,
        "total_transactions": total_transactions,
        "total_amount_sent": total_amount_sent,
        "total_fees_collected": total_fees_collected,
        "last_transactions": last_five_tx
    }
