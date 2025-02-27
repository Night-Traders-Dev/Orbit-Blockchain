import json
import plyvel
from block import Block

DB_PATH = "blockchain.db"

# Open RocksDB connection
try:
    db = plyvel.DB(DB_PATH, create_if_missing=True)
except Exception as e:
    print(f"[ERROR] Failed to open database: {e}")
    db = None  # Prevent crashes if DB fails

def init_db():
    """Initialize the database by setting up necessary keys."""
    if not db:
        print("[ERROR] Database connection not initialized.")
        return
    try:
        if db.get(b'last_block') is None:
            db.put(b'last_block', b'0')  # Start from block index 0
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")

def is_blockchain_empty():
    """Check if the blockchain database contains any blocks."""
    if not db:
        print("[ERROR] Database connection not initialized.")
        return True
    try:
        return db.get(b'last_block') == b'0'
    except Exception as e:
        print(f"[ERROR] Failed to check if blockchain is empty: {e}")
        return True  # Assume empty on failure

def insert_block(block):
    """Insert a new block into RocksDB using atomic transactions."""
    if not db:
        print("[ERROR] Database connection not initialized.")
        return False
    try:
        last_index = int(db.get(b'last_block') or b'0')
        new_index = last_index + 1

        block_key = f'block_{new_index}'.encode()
        block_data = json.dumps(block.to_dict()).encode()

        # Use batch write for atomic operations
        with db.write_batch() as batch:
            batch.put(block_key, block_data)
            batch.put(b'last_block', str(new_index).encode())  # Update last block index

            # Store each transaction separately
            for tx in block.data:
                if isinstance(tx, dict) and "tx_id" in tx:
                    tx_key = f'tx_{tx["tx_id"]}'.encode()
                    batch.put(tx_key, json.dumps(tx).encode())

        print(f"[Database] Block {new_index} inserted successfully.")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to insert block: {e}")
        return False

def get_last_block():
    """Retrieve the last block in the blockchain."""
    if not db:
        print("[ERROR] Database connection not initialized.")
        return None
    try:
        last_index = int(db.get(b'last_block') or b'0')
        if last_index == 0:
            return None  # No blocks yet
        block_data = db.get(f'block_{last_index}'.encode())
        return json.loads(block_data) if block_data else None
    except Exception as e:
        print(f"[ERROR] Failed to retrieve last block: {e}")
        return None

def get_latest_block():
    """Retrieve the latest block from the blockchain as a Block object."""
    last_block = get_last_block()
    if not last_block:
        print("[ERROR] No blocks found in the blockchain.")
        return None  # Return None if no block exists
    try:
        return Block(
            block_index=last_block["block_index"],
            previous_hash=last_block["previous_hash"],
            timestamp=last_block["timestamp"],
            data=last_block["data"],
            proposer=last_block["proposer"],
            proof_of_accuracy=last_block.get("proof_of_accuracy", "MISSING_PoA"),
        )
    except KeyError as e:
        print(f"[ERROR] Missing key {e} in the latest block data.")
        return None

def get_all_blocks():
    """Retrieve all blocks from RocksDB."""
    if not db:
        print("[ERROR] Database connection not initialized.")
        return []
    blocks = []
    try:
        last_index = int(db.get(b'last_block') or b'0')

        for i in range(1, last_index + 1):
            block_data = db.get(f'block_{i}'.encode())
            if block_data:
                try:
                    block_json = json.loads(block_data.decode())  # Decode bytes to string before parsing
                    blocks.append(Block(
                        block_index=block_json["block_index"],
                        previous_hash=block_json["previous_hash"],
                        timestamp=block_json["timestamp"],
                        data=block_json["data"],
                        proposer=block_json["proposer"],
                        proof_of_accuracy=block_json.get("proof_of_accuracy", "MISSING_PoA"),
                    ))
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[ERROR] Failed to parse block {i}: {e}")
    except Exception as e:
        print(f"[ERROR] Failed to retrieve all blocks: {e}")
    return blocks

def get_recent_blocks(limit=5):
    """Retrieve the last N blocks to support Proof of Accuracy (PoA)."""
    if not db:
        print("[ERROR] Database connection not initialized.")
        return []
    recent_blocks = []
    try:
        last_index = int(db.get(b'last_block') or b'0')
        start_index = max(1, last_index - limit + 1)  # Get the last `limit` blocks

        for i in range(start_index, last_index + 1):
            block_data = db.get(f'block_{i}'.encode())
            if block_data:
                try:
                    block_json = json.loads(block_data.decode())  # Decode bytes to string before parsing
                    recent_blocks.append(Block(
                        block_index=block_json["block_index"],
                        previous_hash=block_json["previous_hash"],
                        timestamp=block_json["timestamp"],
                        data=block_json["data"],
                        proposer=block_json["proposer"],
                        proof_of_accuracy=block_json.get("proof_of_accuracy", "MISSING_PoA"),
                    ))
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[ERROR] Failed to parse block {i}: {e}")
    except Exception as e:
        print(f"[ERROR] Failed to retrieve recent blocks: {e}")
    return recent_blocks


def is_transaction_spent(tx_id):
    """Check if a transaction has already been spent (UTXO tracking)."""
    spent_transactions = db.get(b"spent_transactions")
    if spent_transactions:
        spent_transactions = json.loads(spent_transactions.decode("utf-8"))
    else:
        spent_transactions = set()

    return tx_id in spent_transactions


def mark_transaction_as_spent(tx_id):
    """Mark a transaction as spent."""
    spent_transactions = db.get(b"spent_transactions")
    if spent_transactions:
        spent_transactions = json.loads(spent_transactions.decode("utf-8"))
    else:
        spent_transactions = set()

    spent_transactions.add(tx_id)
    db.put(b"spent_transactions", json.dumps(list(spent_transactions)).encode("utf-8"))

def close_db():
    """Close the database connection."""
    if db:
        db.close()
        print("[Database] Connection closed.")

# Initialize the database on startup
init_db()
