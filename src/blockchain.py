import time
import json
from block import Block
import database

def init_blockchain():
    """Initialize the blockchain with a genesis block if empty."""
    database.init_db()
    last_block = database.get_last_block()

    if last_block is None:
        genesis_block = Block(0, "0", time.time(), [{"genesis": True}], "genesis")
        database.insert_block(genesis_block)

def get_latest_block():
    """Retrieve the latest block from the blockchain."""
    last_block = database.get_last_block()
    if not last_block:
        print("[ERROR] No blocks found in the blockchain.")
        return None  # Return None if no block exists
    try:
        return Block(
            block_index=last_block["block_index"],
            previous_hash=last_block["previous_hash"],
            timestamp=last_block["timestamp"],
            data=last_block["data"],
            proposer=last_block["proposer"]
        )
    except KeyError as e:
        print(f"[ERROR] Missing key {e} in the latest block data.")
        return None

def get_blockchain():
    """Retrieve the full blockchain from the database."""
    return database.get_all_blocks()

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
