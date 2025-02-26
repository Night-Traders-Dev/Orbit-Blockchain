import json
import sqlite3

DB_FILE = "blockchain.db"

def init_db():
    """Initialize the database and create necessary tables."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blocks (
        block_index INTEGER PRIMARY KEY,
        previous_hash TEXT NOT NULL,
        timestamp REAL NOT NULL,
        data TEXT NOT NULL,
        proposer TEXT NOT NULL,
         hash TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        tx_id TEXT PRIMARY KEY,
        sender TEXT NOT NULL,
        receiver TEXT NOT NULL,
        amount REAL NOT NULL,
        fee REAL NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

def get_last_block():
    """Retrieve the last block in the blockchain."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1")
    block = cursor.fetchone()
    conn.close()
    return block

def insert_block(block):
    """Insert a new block into the database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO blocks (block_index, previous_hash, timestamp, data, proposer, hash)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (block.block_index, block.previous_hash, block.timestamp, json.dumps(block.data), block.proposer, block.hash))
    
    conn.commit()
    conn.close()
