import time
import json
import requests
from block import Block
from blockchain import get_latest_block, get_blockchain, get_blockchain_stats
from database import insert_block, get_last_block, get_all_blocks, is_blockchain_empty
from consensus import generate_poa, verify_poa_proof, compute_poa
from node import app  

BASE_URL = "http://localhost:5000"

def test_block_creation():
    """Test creating and inserting a block."""
    print("\n[TEST] Creating a new block...")
    
    last_block = get_latest_block()
    if not last_block:
        print("[ERROR] No latest block found.")
        return
    
    tx_data = [
        {"tx_id": "tx001", "sender": "Alice", "receiver": "Bob", "amount": 10, "fee": 0.1},
        {"tx_id": "tx002", "sender": "Charlie", "receiver": "David", "amount": 5, "fee": 0.05}
    ]

    poa_proof = generate_poa(get_all_blocks()[-5:])  # Generate PoA from last 5 blocks
    new_block = Block(
        block_index=last_block.block_index + 1,
        previous_hash=last_block.hash,
        timestamp=time.time(),
        data=tx_data,
        proposer="Node_1",
        proof_of_accuracy=compute_poa(get_all_blocks()[-5:])
    )

    if verify_poa_proof(poa_proof):
        print("[SUCCESS] PoA proof verified.")
    else:
        print("[ERROR] Invalid PoA proof.")

    if insert_block(new_block):
        print(f"[SUCCESS] Block {new_block.block_index} added successfully.")
    else:
        print("[ERROR] Block insertion failed.")

def test_get_blockchain():
    """Test retrieving the blockchain."""
    print("\n[TEST] Fetching blockchain...")
    blockchain = get_blockchain()
    
    if blockchain:
        print(f"[SUCCESS] Retrieved {len(blockchain)} blocks.")
    else:
        print("[ERROR] Failed to fetch blockchain.")

def test_get_blockchain_stats():
    """Test retrieving blockchain statistics."""
    print("\n[TEST] Fetching blockchain stats...")
    stats = get_blockchain_stats()
    
    if stats:
        print(f"[SUCCESS] Stats retrieved: {json.dumps(stats, indent=2)}")
    else:
        print("[ERROR] Failed to fetch blockchain stats.")

def test_api_propose_block():
    """Test proposing a new block through the API."""
    print("\n[TEST] Proposing a new block via API...")

    poa_proof = generate_poa(get_all_blocks()[-5:])
    tx_data = [
        {"tx_id": "tx003", "sender": "Eve", "receiver": "Frank", "amount": 15, "fee": 0.2}
    ]

    response = requests.post(
        f"{BASE_URL}/propose_block",
        json={"proposer": "Node_1", "data": tx_data, "poa_proof": poa_proof}
    )

    if response.status_code == 200:
        print("[SUCCESS] Block proposed successfully.")
        print(response.json())
    else:
        print(f"[ERROR] Block proposal failed: {response.text}")

def test_api_get_blockchain():
    """Test fetching blockchain data via API."""
    print("\n[TEST] Fetching blockchain via API...")
    response = requests.get(f"{BASE_URL}/blockchain")

    if response.status_code == 200:
        print("[SUCCESS] Blockchain fetched successfully.")
        print(response.json())
    else:
        print(f"[ERROR] Failed to fetch blockchain: {response.text}")

def test_api_vote():
    """Test voting on a proposed block."""
    print("\n[TEST] Voting on a proposed block...")
    
    last_block = get_latest_block()
    poa_proof = generate_poa(get_all_blocks()[-5:])
    
    if not last_block:
        print("[ERROR] No latest block found.")
        return
    
    response = requests.post(
        f"{BASE_URL}/vote",
        json={"block": last_block.to_dict(), "poa_proof": poa_proof}
    )

    if response.status_code == 200:
        print("[SUCCESS] Vote cast successfully.")
        print(response.json())
    else:
        print(f"[ERROR] Voting failed: {response.text}")

if __name__ == "__main__":
    print("=== Running Blockchain Tests ===")

    # Ensure blockchain is initialized
    if is_blockchain_empty():
        print("[INFO] Blockchain is empty. Initializing genesis block...")
    
    test_block_creation()
    test_get_blockchain()
    test_get_blockchain_stats()
    test_api_propose_block()
    test_api_get_blockchain()
    test_api_vote()

    print("\n=== All Tests Completed ===")
