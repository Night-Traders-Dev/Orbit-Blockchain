import json
import libsql_client
from block import Block

DB_PATH = "blockchain.db"

async def connect_db():
    """Connect to the local Turso (libSQL) database."""
    try:
#        async with libsql_client.create_client(f"file:{DB_PATH}") as client:
        client = libsql_client.create_client(f"file:{DB_PATH}")
        return client
    except Exception as e:
        print(f"[ERROR] Failed to connect to Turso: {e}")
        client = None  # Prevent crashes if DB fails
        return client

async def init_db():
    global client
    client = await connect_db()
    """Initialize the database schema if it does not exist."""
    if not client:
        print("[ERROR] Database connection not initialized.")
        return
    
    try:
        await client.execute("""
            CREATE TABLE IF NOT EXISTS blockchain (
                block_index INTEGER PRIMARY KEY,
                previous_hash TEXT,
                timestamp INTEGER,
                data TEXT,
                proposer TEXT,
                proof_of_accuracy TEXT
            )
        """)
        await client.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await client.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                tx_id TEXT PRIMARY KEY,
                data TEXT
            )
        """)

        # Ensure last_block is tracked
        await client.execute("INSERT OR IGNORE INTO metadata (key, value) VALUES ('last_block', '0')")
        print("[Database] Initialization complete.")
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}")

async def is_blockchain_empty():
    """Check if the blockchain database contains any blocks."""
    try:
        result = await client.execute("SELECT value FROM metadata WHERE key = 'last_block'")
        last_block = result.rows[0][0] if result.rows else '0'
        return last_block == '0'
    except Exception as e:
        print(f"[ERROR] Failed to check if blockchain is empty: {e}")
        return True

async def insert_block(block):
    """Insert a new block into Turso using transactions."""
    try:
        result = await client.execute("SELECT value FROM metadata WHERE key = 'last_block'")
        last_index = int(result.rows[0][0]) if result.rows else 0
        new_index = last_index + 1

        await client.execute("""
            INSERT INTO blockchain (block_index, previous_hash, timestamp, data, proposer, proof_of_accuracy)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            new_index, block.previous_hash, block.timestamp, json.dumps(block.data), 
            block.proposer, block.proof_of_accuracy
        ))

        # Update last_block metadata
        await client.execute("UPDATE metadata SET value = ? WHERE key = 'last_block'", (str(new_index),))

        # Store transactions separately
        for tx in block.data:
            if isinstance(tx, dict) and "tx_id" in tx:
                await client.execute("INSERT INTO transactions (tx_id, data) VALUES (?, ?)", 
                                     (tx["tx_id"], json.dumps(tx)))

        print(f"[Database] Block {new_index} inserted successfully.")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to insert block: {e}")
        return False

async def get_last_block():
    """Retrieve the last block in the blockchain."""
    try:
        result = await client.execute("SELECT value FROM metadata WHERE key = 'last_block'")
        last_index = int(result.rows[0][0]) if result.rows else 0
        if last_index == 0:
            return None

        result = await client.execute("SELECT * FROM blockchain WHERE block_index = ?", (last_index,))
        block_data = result.rows[0] if result.rows else None
        return {
            "block_index": block_data[0],
            "previous_hash": block_data[1],
            "timestamp": block_data[2],
            "data": json.loads(block_data[3]),
            "proposer": block_data[4],
            "proof_of_accuracy": block_data[5],
        } if block_data else None
    except Exception as e:
        print(f"[ERROR] Failed to retrieve last block: {e}")
        return None

async def get_all_blocks():
    """Retrieve all blocks from Turso."""
    try:
        result = await client.execute("SELECT * FROM blockchain ORDER BY block_index ASC")
        blocks = [
            Block(
                block_index=row[0],
                previous_hash=row[1],
                timestamp=row[2],
                data=json.loads(row[3]),
                proposer=row[4],
                proof_of_accuracy=row[5],
            ) for row in result.rows
        ]
        return blocks
    except Exception as e:
        print(f"[ERROR] Failed to retrieve all blocks: {e}")
        return []

async def get_recent_blocks(limit=5):
    """Retrieve the last N blocks."""
    try:
        result = await client.execute("SELECT * FROM blockchain ORDER BY block_index DESC LIMIT ?", (limit,))
        recent_blocks = [
            Block(
                block_index=row[0],
                previous_hash=row[1],
                timestamp=row[2],
                data=json.loads(row[3]),
                proposer=row[4],
                proof_of_accuracy=row[5],
            ) for row in result.rows
        ]
        return recent_blocks
    except Exception as e:
        print(f"[ERROR] Failed to retrieve recent blocks: {e}")
        return []

async def is_transaction_spent(tx_id):
    """Check if a transaction has already been spent (UTXO tracking)."""
    try:
        result = await client.execute("SELECT COUNT(*) FROM transactions WHERE tx_id = ?", (tx_id,))
        return result.rows[0][0] > 0
    except Exception as e:
        print(f"[ERROR] Failed to check transaction: {e}")
        return False

async def mark_transaction_as_spent(tx_id):
    """Mark a transaction as spent."""
    try:
        await client.execute("INSERT OR IGNORE INTO transactions (tx_id, data) VALUES (?, '{}')", (tx_id,))
    except Exception as e:
        print(f"[ERROR] Failed to mark transaction as spent: {e}")

async def close_db():
    """Close the database connection."""
    if client:
        await client.close()
        print("[Database] Connection closed.")