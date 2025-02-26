import json
import sqlite3
from block import Block

DB_FILE = "blockchain.db"

def init_db():
    """Initialize the database and create necessary tables."""
    with sqlite3.connect(DB_FILE, timeout=5) as conn:
        cursor = conn.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS blocks (
            block_index INTEGER PRIMARY KEY AUTOINCREMENT,  -- Auto-increment
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
            fee REAL NOT NULL,
            block_index INTEGER,
            FOREIGN KEY(block_index) REFERENCES blocks(block_index)
        )
        """)

        conn.commit()

def get_last_block():
    """Retrieve the last block in the blockchain."""
    with sqlite3.connect(DB_FILE, timeout=5) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1")
        return cursor.fetchone()

def insert_block(block):
    """Insert a new block and its transactions into the database."""
    with sqlite3.connect(DB_FILE, timeout=5) as conn:
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO blocks (previous_hash, timestamp, data, proposer, hash)
        VALUES (?, ?, ?, ?, ?)
        """, (block.previous_hash, block.timestamp, json.dumps(block.data), block.proposer, block.hash))

        block_id = cursor.lastrowid  # Fetch the new block's ID

        for tx in block.data:
            if isinstance(tx, dict) and "tx_id" in tx:
                cursor.execute("""
                INSERT INTO transactions (tx_id, sender, receiver, amount, fee, block_index)
                VALUES (?, ?, ?, ?, ?, ?)
                """, (tx["tx_id"], tx["sender"], tx["receiver"], float(tx["amount"]), float(tx["fee"]), block_id))

        conn.commit()


def get_all_blocks():
    """Retrieve all blocks from the blockchain database."""
    with sqlite3.connect(DB_FILE, timeout=5) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM blocks ORDER BY block_index ASC")
        blocks = cursor.fetchall()

    return [Block(*block[:5]) for block in blocks]

def get_block_count():
    """Return the total number of blocks in the blockchain."""
    with sqlite3.connect(DB_FILE, timeout=5) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM blocks")
        return cursor.fetchone()[0]

def get_all_transactions():
    """Retrieve all transactions from the database."""
    with sqlite3.connect(DB_FILE, timeout=5) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM transactions ORDER BY rowid ASC")
        return [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]

def get_last_transactions(limit=5):
    """Retrieve the last N transactions."""
    with sqlite3.connect(DB_FILE, timeout=5) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM transactions ORDER BY rowid DESC LIMIT {limit}")
        return [dict(zip([col[0] for col in cursor.description], row)) for row in cursor.fetchall()]
