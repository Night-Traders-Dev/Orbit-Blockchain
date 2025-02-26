import json
import plyvel
from block import Block

DB_PATH = "blockchain.db"

# Open RocksDB connection
db = plyvel.DB(DB_PATH, create_if_missing=True)

def init_db():
    """Initialize the database by setting up necessary keys."""
    if db.get(b'last_block') is None:
        db.put(b'last_block', b'0')  # Start from block index 0

def insert_block(block):
    """Insert a new block and its transactions into RocksDB."""
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

    db.put(block_key, block_data)
    db.put(b'last_block', str(new_index).encode())  # Update last block index

    # Store each transaction separately
    for tx in block.data:
        if isinstance(tx, dict) and "tx_id" in tx:
            tx_key = f'tx_{tx["tx_id"]}'.encode()
            tx_data = json.dumps(tx).encode()
            db.put(tx_key, tx_data)


def get_last_block():
    """Retrieve the last block in the blockchain."""
    last_index = int(db.get(b'last_block') or b'0')
    if last_index == 0:
        return None  # No blocks yet
    block_data = db.get(f'block_{last_index}'.encode())
    return json.loads(block_data) if block_data else None




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

def get_all_blocks():
    """Retrieve all blocks from RocksDB."""
    blocks = []
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
    return blocks

def get_block_count():
    """Return the total number of blocks in the blockchain."""
    return int(db.get(b'last_block') or b'0')

def get_all_transactions():
    """Retrieve all transactions from RocksDB."""
    transactions = []
    for key, value in db.iterator(prefix=b'tx_'):
        transactions.append(json.loads(value))
    return transactions

def get_last_transactions(limit=5):
    """Retrieve the last N transactions."""
    transactions = get_all_transactions()
    return transactions[-limit:] if len(transactions) >= limit else transactions

def is_transaction_spent(tx_id):
    """Check if a transaction has already been spent."""
    try:
        # Check if the transaction ID exists in the spent transactions database
        spent_key = f"spent_{tx_id}".encode('utf-8')
        # Attempt to get the value from the DB
        spent_status = db.get(spent_key)
        if spent_status:
            return True  # Transaction has been spent
        else:
            return False  # Transaction has not been spent
    except Exception as e:
        print(f"Error checking if transaction is spent: {e}")
        return False

def mark_transaction_spent(tx_id):
    """Mark a transaction as spent."""
    try:
        spent_key = f"spent_{tx_id}".encode('utf-8')
        db.put(spent_key, b'1')  # Mark as spent with a value of '1'
        print(f"[Database] Transaction {tx_id} marked as spent.")
    except Exception as e:
        print(f"[Database] Error marking transaction {tx_id} as spent: {e}")
