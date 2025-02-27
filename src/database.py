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

def insert_block(block):
    """Insert a new block and its transactions into RocksDB using atomic transactions."""
    if not db:
        print("[ERROR] Database connection not initialized.")
        return False
    try:
        last_index = int(db.get(b'last_block') or b'0')
        new_index = last_index + 1

        block_key = f'block_{new_index}'.encode()
        block_data = json.dumps({
            "block_index": new_index,
            "previous_hash": block.previous_hash,
            "timestamp": block.timestamp,
            "data": block.data,
            "proposer": block.proposer,
            "hash": block.hash
        }).encode()

        # Use batch write for atomic operations
        with db.write_batch() as batch:
            batch.put(block_key, block_data)
            batch.put(b'last_block', str(new_index).encode())  # Update last block index

            # Store each transaction separately
            for tx in block.data:
                if isinstance(tx, dict) and "tx_id" in tx:
                    tx_key = f'tx_{tx["tx_id"]}'.encode()
                    tx_data = json.dumps(tx).encode()
                    batch.put(tx_key, tx_data)

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
    """Retrieve the latest block from the blockchain."""
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
            hash=last_block["hash"]
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
        last_index_raw = db.get(b'last_block')
        last_index = int(last_index_raw.decode()) if last_index_raw else 0  # Convert bytes to int safely

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
                        proposer=block_json["proposer"]
                    ))
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"[ERROR] Failed to parse block {i}: {e}")
    except Exception as e:
        print(f"[ERROR] Failed to retrieve all blocks: {e}")
    return blocks

def get_block_count():
    """Return the total number of blocks in the blockchain."""
    if not db:
        print("[ERROR] Database connection not initialized.")
        return 0
    try:
        return int(db.get(b'last_block') or b'0')
    except Exception as e:
        print(f"[ERROR] Failed to retrieve block count: {e}")
        return 0

def get_all_transactions():
    """Retrieve all transactions from RocksDB."""
    if not db:
        print("[ERROR] Database connection not initialized.")
        return []
    transactions = []
    try:
        for key, value in db.iterator(prefix=b'tx_'):
            transactions.append(json.loads(value))
    except Exception as e:
        print(f"[ERROR] Failed to retrieve transactions: {e}")
    return transactions

def get_last_transactions(limit=5):
    """Retrieve the last N transactions."""
    transactions = get_all_transactions()
    return transactions[-limit:] if len(transactions) >= limit else transactions

def is_transaction_spent(tx_id):
    """Check if a transaction has already been spent."""
    if not db:
        print("[ERROR] Database connection not initialized.")
        return False
    try:
        spent_key = f"spent_{tx_id}".encode('utf-8')
        spent_status = db.get(spent_key)
        return spent_status is not None  # If exists, it has been spent
    except Exception as e:
        print(f"[ERROR] Checking spent status failed for {tx_id}: {e}")
        return False

def mark_transaction_spent(tx_id):
    """Mark a transaction as spent."""
    if not db:
        print("[ERROR] Database connection not initialized.")
        return
    try:
        spent_key = f"spent_{tx_id}".encode('utf-8')
        db.put(spent_key, b'1')  # Mark as spent with a value of '1'
        print(f"[Database] Transaction {tx_id} marked as spent.")
    except Exception as e:
        print(f"[Database] Error marking transaction {tx_id} as spent: {e}")

def get_transaction(tx_id):
    """Retrieve a transaction by its ID."""
    if not db:
        print("[ERROR] Database connection not initialized.")
        return None
    try:
        tx_data = db.get(f'tx_{tx_id}'.encode())
        return json.loads(tx_data) if tx_data else None
    except Exception as e:
        print(f"[ERROR] Failed to retrieve transaction {tx_id}: {e}")
        return None

def close_db():
    """Close the database connection."""
    if db:
        db.close()
        print("[Database] Connection closed.")

# Initialize the database on startup
init_db()
