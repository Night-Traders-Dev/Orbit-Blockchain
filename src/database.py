import sqlite3
import json

DB_NAME = "heo_node.db"

def get_last_block():
    """Retrieve the last block from the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM blocks ORDER BY \"index\" DESC LIMIT 1")
    last_block = cursor.fetchone()
    
    conn.close()
    
    if last_block:
        return {
            "index": last_block[0],
            "previous_hash": last_block[1],
            "timestamp": last_block[2],
            "data": json.loads(last_block[3]),  # Assuming JSON data
            "proposer": last_block[4],
            "hash": last_block[5]
        }
    else:
        return None  # No blocks in the database yet

def save_block(block):
    """Save a block to the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO blocks ("index", previous_hash, timestamp, data, proposer, hash) 
    VALUES (?, ?, ?, ?, ?, ?)
    """, (block.index, block.previous_hash, block.timestamp, json.dumps(block.data), block.proposer, block.hash))
    
    conn.commit()
    conn.close()

def init_db():
    """Initialize the SQLite database with required tables."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blocks (
        "index" INTEGER PRIMARY KEY,
        previous_hash TEXT,
        timestamp REAL,
        data TEXT,
        proposer TEXT,
        hash TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        tx_id TEXT PRIMARY KEY,
        sender TEXT,
        receiver TEXT,
        amount REAL,
        fee REAL
    )
    """)
    
    conn.commit()
    conn.close()
