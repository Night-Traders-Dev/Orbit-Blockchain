import time
import json
from block import Block
import database

def init_blockchain():
    """Initialize blockchain and ensure the first block exists."""
    if database.is_blockchain_empty():
        print("[INFO] No existing blockchain found. Initializing genesis block...")
        genesis_block = Block(
            block_index=0,
            previous_hash="0",
            timestamp=time.time(),
            data=[],
            proposer="GENESIS",
            proof_of_accuracy="GENESIS_PoA"
        )
        if database.insert_block(genesis_block):
            print(f"[INFO] Genesis Block Created: {genesis_block.to_dict()}")
        else:
            print("[ERROR] Failed to insert Genesis block.")
    else:
        print("[INFO] Blockchain already exists.")

def get_latest_block():
    """Retrieve the latest block from the blockchain as a Block object."""
    latest_block_data = database.get_latest_block()
    if not latest_block_data:
        print("[ERROR] No blocks found in the blockchain.")
        return None  # Return None if no block exists
    
    return Block(
        block_index=latest_block_data["block_index"],
        previous_hash=latest_block_data["previous_hash"],
        timestamp=latest_block_data["timestamp"],
        data=latest_block_data["data"],
        proposer=latest_block_data["proposer"],
        proof_of_accuracy=latest_block_data["proof_of_accuracy"]
    )

def get_blockchain():
    """Retrieve the full blockchain from the database."""
    return database.get_all_blocks()

def get_blockchain_stats():
    """Retrieve blockchain statistics for the explorer."""
    total_blocks = database.get_block_count()

    # Retrieve transactions only once (optimization)
    transactions = database.get_all_transactions()
    total_transactions = len(transactions)

    # Calculate total sent & fees collected safely
    total_amount_sent = sum(float(tx.get("amount", 0)) for tx in transactions)
    total_fees_collected = sum(float(tx.get("fee", 0)) for tx in transactions)

    # Get the last 5 transactions safely
    last_five_tx = transactions[-5:] if total_transactions >= 5 else transactions

    return {
        "total_blocks": total_blocks,
        "total_transactions": total_transactions,
        "total_amount_sent": total_amount_sent,
        "total_fees_collected": total_fees_collected,
        "last_transactions": last_five_tx
    }
