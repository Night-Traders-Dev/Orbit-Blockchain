import sys
import time
import threading
import requests
from flask import Flask, request, jsonify
from blockchain import init_blockchain, get_latest_block
from block import Block
import database

app = Flask(__name__)
nodes = set()  # Store connected nodes

NODE_OPERATOR_ADDRESS = "heoEnsiaowm391"

@app.route('/nodes', methods=['GET'])
def get_nodes():
    """Returns the list of known nodes."""
    return jsonify(list(nodes)), 200


@app.route('/blockchain', methods=['GET'])
def get_blockchain():
    """Returns the current blockchain from the database."""
    try:
        # Fetch all blocks from DB
        blocks = database.get_all_blocks()
        if not blocks:
            # Return a message if no blocks are found in the database
            return jsonify({"message": "No blocks found in the blockchain."}), 404

        # Convert blocks to dictionary format for JSON response
        blockchain_data = [block.to_dict() for block in blocks]
        return jsonify(blockchain_data), 200
    except Exception as e:
        # Handle unexpected errors and log them
        print(f"[ERROR] Failed to fetch blockchain: {e}")
        return jsonify({"error": "Internal server error, could not fetch blockchain."}), 500


@app.route('/propose_block', methods=['POST'])
def propose_block():
    """Propose a new block and submit PoA proof for validation."""
    data = request.get_json()
    proposer = data.get("proposer")
    tx_data = data.get("data")
    poa_proof = data.get("poa_proof")  # Proof of Accuracy from proposer

    if not proposer or not isinstance(tx_data, list) or len(tx_data) == 0:
        return jsonify({"error": "Missing or invalid proposer/transaction data"}), 400

    if not poa_proof:
        return jsonify({"error": "Missing Proof of Accuracy"}), 400

    # Validate transactions
    for txn in tx_data:
        if not all(k in txn for k in ["tx_id", "sender", "receiver", "amount", "fee"]):
            return jsonify({"error": f"Invalid transaction format: {txn}"}), 400
        if database.is_transaction_spent(txn["tx_id"]):
            return jsonify({"error": f"Double spend detected: {txn['tx_id']}"}), 400
        if txn["amount"] <= 0 or txn["fee"] < 0:
            return jsonify({"error": f"Invalid transaction amounts: {txn}"}), 400

    # Fetch latest block
    last_block = get_latest_block()
    new_block = Block(
        block_index=last_block.block_index + 1,
        previous_hash=last_block.hash,
        timestamp=time.time(),
        data=tx_data,
        proposer=proposer
    )

    # Verify PoA Proof before requesting votes
    if not verify_poa_proof(poa_proof):
        return jsonify({"error": "Invalid Proof of Accuracy"}), 400

    # Request votes from other nodes
    votes = collect_votes(new_block, poa_proof)
    if votes.count(True) > votes.count(False):
        approve_and_add_block(new_block, tx_data)
        return jsonify({"status": "Block added", "block": new_block.to_dict()}), 200
    else:
        return jsonify({"error": "Block rejected by network"}), 400

def verify_poa_proof(poa_proof):
    """Verify if the proposer accurately validated historical transactions."""
    if database.is_blockchain_empty():
        print("[INFO] No previous transactions. Accepting genesis block.")
        return True

    for proof in poa_proof:
        tx_id = proof.get("tx_id")
        original_tx = database.get_transaction(tx_id)

        if not original_tx or original_tx != proof["transaction"]:
            return False  # Invalid proof

    return True  # Valid proof


def validate_block_poa(block_data):
    """Validate Proof of Accuracy (PoA) for a received block."""
    poa = block_data.get("proof_of_accuracy")
    if not poa:
        print("[ERROR] Block missing Proof of Accuracy.")
        return False

    # Retrieve recent blocks for PoA validation
    history = database.get_recent_blocks(limit=5)  # Get last 5 blocks
    if not history:
        return True  # If no history, assume first few blocks bootstrap the chain

    # Compute expected PoA based on historical blocks
    expected_poa = hash(",".join(str(b.hash) for b in history))
    is_valid = (poa == expected_poa)

    if not is_valid:
        print(f"[ERROR] Invalid Proof of Accuracy for block {block_data['block_index']}")

    return is_valid



def approve_and_add_block(new_block, tx_data):
    """Helper function to add a block to the blockchain."""
    database.insert_block(new_block)  # Store block in RocksDB
    for txn in tx_data:
        database.mark_transaction_spent(txn["tx_id"])  # Mark transactions as spent

    threading.Thread(target=broadcast_block, args=(new_block,)).start()

@app.route('/vote', methods=['POST'])
def vote():
    """Vote on a proposed block based on its validity and Proof of Accuracy."""
    data = request.get_json()
    block_data = data.get("block")
    poa_proof = data.get("poa_proof")

    if not block_data or not poa_proof:
        return jsonify({"error": "No block data or PoA proof provided"}), 400

    # Check block validity
    last_block = get_latest_block()
    is_valid = (block_data["previous_hash"] == last_block.hash and
                block_data["block_index"] == last_block.block_index + 1)

    # Verify PoA proof
    if is_valid and verify_poa_proof(poa_proof):
        return jsonify({"vote": True}), 200
    else:
        return jsonify({"vote": False}), 400


@app.route('/receive_block', methods=['POST'])
def receive_block():
    """Receive and validate a block from the network, enforcing Proof of Accuracy."""
    data = request.get_json()
    block_data = data.get("block")

    if not block_data:
        return jsonify({"error": "No block data provided"}), 400

    last_block = get_latest_block()

    # Validate block structure and PoA
    if (block_data["previous_hash"] == last_block.hash and
        block_data["block_index"] == last_block.block_index + 1 and
        validate_block_poa(block_data)):

        new_block = Block(
            block_index=block_data["block_index"],
            previous_hash=block_data["previous_hash"],
            timestamp=block_data["timestamp"],
            data=block_data["data"],
            proposer=block_data["proposer"]
        )

        database.insert_block(new_block)
        return jsonify({"status": "Block added"}), 200
    else:
        return jsonify({"error": "Invalid block or missing Proof of Accuracy"}), 400


@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    """Accepts a new transaction with Proof of Accuracy validation."""
    data = request.get_json()
    tx_id = data.get("tx_id")
    poa = data.get("proof_of_accuracy")  # Expect PoA in transaction

    if not tx_id or database.is_transaction_spent(tx_id):
        return jsonify({"error": "Invalid or duplicate transaction"}), 400

    # If blockchain is empty, allow transaction (Bootstrap Phase)
    if database.is_blockchain_empty():
        print("[INFO] Blockchain is empty. Accepting initial transactions.")
    else:
        if not poa or not validate_poa(poa):
            return jsonify({"error": "Missing or invalid Proof of Accuracy"}), 400

    database.insert_transaction(data)
    return jsonify({"status": "Transaction added"}), 200


def collect_votes(block):
    """Ask all nodes to vote on a proposed block."""
    if not nodes:
        print("[INFO] No nodes available for voting. Skipping vote collection.")
        return [True]  # Auto-approve

    votes = []
    for node in nodes:
        try:
            response = requests.post(f"{node}/vote", json={"block": block.to_dict()})
            if response.status_code == 200:
                vote_data = response.json()
                votes.append(vote_data.get("vote", False))
        except:
            votes.append(False)
    return votes

def broadcast_block(block):
    """Broadcast a newly added block to all nodes."""
    for node in nodes:
        try:
            requests.post(f"{node}/receive_block", json={"block": block.to_dict()})
        except:
            pass

if __name__ == '__main__':
    NODE_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"Starting node on port {NODE_PORT}")
    init_blockchain()
    nodes.add(f"http://localhost:{NODE_PORT}")
    app.run(host="0.0.0.0", port=NODE_PORT)
