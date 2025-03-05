import asyncio
import time
import aiohttp
from block import Block
import database

BROADCAST_URL = "http://localhost:5000/broadcast_block"

async def init_blockchain():
    """Initialize blockchain and ensure the first block exists."""
    if await database.is_blockchain_empty():
        print("[INFO] No existing blockchain found. Initializing genesis block...")
        genesis_block = Block(
            block_index=0,
            previous_hash="0",
            timestamp=time.time(),
            data=[],
            proposer="GENESIS",
            proof_of_accuracy="GENESIS_PoA"
        )
        if await database.insert_block(genesis_block):
            print(f"[INFO] Genesis Block Created: {genesis_block.to_dict()}")
        else:
            print("[ERROR] Failed to insert Genesis block.")
    else:
        print("[INFO] Blockchain already exists.")

async def get_latest_block():
    """Retrieve the latest block from the blockchain as a Block object."""
    latest_block_data = await database.get_last_block()
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

async def get_blockchain():
    """Retrieve the full blockchain from the database."""
    return await database.get_all_blocks()

async def get_blockchain_stats():
    """Retrieve blockchain statistics for the explorer."""
    total_blocks = await database.get_block_count()
    transactions = await database.get_all_transactions()
    total_transactions = len(transactions)
    total_amount_sent = sum(float(tx.get("amount", 0)) for tx in transactions)
    total_fees_collected = sum(float(tx.get("fee", 0)) for tx in transactions)
    last_five_tx = transactions[-5:] if total_transactions >= 5 else transactions
    
    return {
        "total_blocks": total_blocks,
        "total_transactions": total_transactions,
        "total_amount_sent": total_amount_sent,
        "total_fees_collected": total_fees_collected,
        "last_transactions": last_five_tx
    }

async def approve_and_add_block(new_block, tx_data):
    """Add a block to the blockchain with atomicity."""
    try:
        success = await database.insert_block(new_block)
        if success:
            for txn in tx_data:
                await database.mark_transaction_as_spent(txn["tx_id"])
            asyncio.create_task(broadcast_block_request(new_block))  # Async broadcast
            print(f"[INFO] Block {new_block.block_index} committed successfully.")
        else:
            print("[ERROR] Block commit failed.")
    except Exception as e:
        print(f"[ERROR] Block commit failed: {e}")

async def broadcast_block_request(block):
    """Send a request to the Flask API to broadcast the block."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(BROADCAST_URL, json={"block": block.to_dict()}) as response:
                if response.status == 200:
                    print(f"[INFO] Block {block.block_index} broadcasted successfully.")
                else:
                    print(f"[WARNING] Broadcast failed: {await response.text()}")
    except Exception as e:
        print(f"[ERROR] Broadcast request failed: {e}")
