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
    """Propose a new block and collect votes."""
    data = request.get_json()
    proposer = data.get("proposer")
    tx_data = data.get("data")

    if not proposer or not isinstance(tx_data, list) or len(tx_data) == 0:
        return jsonify({"error": "Missing or invalid proposer/transaction data"}), 400

    # Validate transactions before block proposal
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

    print(f"[DEBUG] Proposed Block: {new_block.to_dict()}")

    # If this is the only node, approve the block automatically
    if not nodes:
        print("[INFO] No other nodes detected. Auto-approving block.")
        approve_and_add_block(new_block, tx_data)
        return jsonify({"status": "Block added (auto-approved)", "block": new_block.to_dict()}), 200

    # Request votes from other nodes
    votes = collect_votes(new_block)
    print(f"[DEBUG] Vote results: {votes}")

    # Consensus: Majority must approve the block
    if votes.count(True) > votes.count(False):
        approve_and_add_block(new_block, tx_data)
        return jsonify({"status": "Block added", "block": new_block.to_dict()}), 200
    else:
        print(f"[ERROR] Block rejected by network: {new_block.to_dict()}")
        return jsonify({"error": "Block rejected by network"}), 400

def approve_and_add_block(new_block, tx_data):
    """Helper function to add a block to the blockchain."""
    database.insert_block(new_block)  # Store block in RocksDB
    for txn in tx_data:
        database.mark_transaction_spent(txn["tx_id"])  # Mark transactions as spent

    threading.Thread(target=broadcast_block, args=(new_block,)).start()

@app.route('/vote', methods=['POST'])
def vote():
    """Validate and vote on a proposed block."""
    data = request.get_json()
    block_data = data.get("block")

    if not block_data:
        return jsonify({"error": "No block data provided"}), 400

    last_block = get_latest_block()
    vote = (block_data["previous_hash"] == last_block.hash and
            block_data["block_index"] == last_block.block_index + 1)

    return jsonify({"vote": vote}), 200

@app.route('/receive_block', methods=['POST'])
def receive_block():
    """Receive and validate a block from the network."""
    data = request.get_json()
    block_data = data.get("block")

    if not block_data:
        return jsonify({"error": "No block data provided"}), 400

    last_block = get_latest_block()

    if block_data["previous_hash"] == last_block.hash and block_data["block_index"] == last_block.block_index + 1:
        new_block = Block(
            block_data["block_index"],
            block_data["previous_hash"],
            block_data["timestamp"],
            block_data["data"],
            block_data["proposer"]
        )
        database.insert_block(new_block)
        return jsonify({"status": "Block added"}), 200
    else:
        return jsonify({"error": "Invalid block"}), 400

@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    """Accepts a new transaction."""
    data = request.get_json()
    tx_id = data.get("tx_id")

    if not tx_id or database.is_transaction_spent(tx_id):
        return jsonify({"error": "Invalid or duplicate transaction"}), 400

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
