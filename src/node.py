import sys
import time
import threading
import requests
import json
import hashlib
from flask import Flask, request, jsonify
from blockchain import init_blockchain, get_latest_block, approve_and_add_block
from block import Block
from consensus import verify_poa_proof, validate_block_poa, compute_poa, generate_poa
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
        blocks = database.get_all_blocks()
        if not blocks:
            return jsonify({"message": "No blocks found in the blockchain."}), 404

        blockchain_data = [block.to_dict() for block in blocks]
        return jsonify(blockchain_data), 200
    except Exception as e:
        print(f"[ERROR] Failed to fetch blockchain: {e}")
        return jsonify({"error": "Internal server error, could not fetch blockchain."}), 500


@app.route('/propose_block', methods=['POST'])
def propose_block():
    """Propose a new block and submit PoA proof for validation."""
    data = request.get_json()
    proposer = data.get("proposer")
    tx_data = data.get("data")
    poa_proof = data.get("poa_proof")

    if not proposer or not isinstance(tx_data, list) or len(tx_data) == 0:
        return jsonify({"error": "Missing or invalid proposer/transaction data"}), 400

    if not poa_proof:
        return jsonify({"error": "Missing Proof of Accuracy"}), 400

    for txn in tx_data:
        if not all(k in txn for k in ["tx_id", "sender", "receiver", "amount", "fee"]):
            return jsonify({"error": f"Invalid transaction format: {txn}"}), 400
        if database.is_transaction_spent(txn["tx_id"]):
            return jsonify({"error": f"Double spend detected: {txn['tx_id']}"}), 400
        if txn["amount"] <= 0 or txn["fee"] < 0:
            return jsonify({"error": f"Invalid transaction amounts: {txn}"}), 400

    last_block = get_latest_block()
    new_block = Block(
        block_index=last_block.block_index + 1,
        previous_hash=last_block.hash,
        timestamp=time.time(),
        data=tx_data,
        proposer=proposer
    )

    if not verify_poa_proof(poa_proof):
        return jsonify({"error": "Invalid Proof of Accuracy"}), 400

    votes = collect_votes(new_block)
    if votes.count(True) > votes.count(False):
        approve_and_add_block(new_block, tx_data)
        database.mark_transaction_as_spent(txn["tx_id"]) 
        return jsonify({"status": "Block added", "block": new_block.to_dict()}), 200
    else:
        return jsonify({"error": "Block rejected by network"}), 400


@app.route('/recent_blocks', methods=['GET'])
def get_recent_blocks():
    """Return the last 5 blocks for Proof of Accuracy verification."""
    recent_blocks = database.get_recent_blocks(1)

    if not recent_blocks:
        return jsonify({"error": "No recent blocks found"}), 400

    return jsonify([block.to_dict() for block in recent_blocks]), 200


@app.route('/vote', methods=['POST'])
def vote():
    """Vote on a proposed block based on its validity and Proof of Accuracy."""
    data = request.get_json()
    block_data = data.get("block")
    poa_proof = data.get("poa_proof")

    if not block_data or not poa_proof:
        return jsonify({"error": "No block data or PoA proof provided"}), 400

    last_block = get_latest_block()
    if last_block is None:
        return jsonify({"error": "Failed to retrieve latest block"}), 500

    if not all(k in block_data for k in ["previous_hash", "block_index"]):
        return jsonify({"error": "Invalid block format"}), 400

    is_valid = (block_data["previous_hash"] == last_block.hash and
                block_data["block_index"] == last_block.block_index + 1)

    if is_valid and verify_poa_proof(poa_proof):
        return jsonify({"vote": True}), 200
    else:
        return jsonify({"vote": False}), 400


def collect_votes(block):
    """Ask nodes to vote, retrying failed ones with exponential backoff."""
    if not nodes:
        print("[INFO] No nodes available. Auto-approving block.")
        return [True]

    votes = []
    for node in nodes:
        retries = 3
        delay = 1  

        while retries > 0:
            try:
                response = requests.post(f"{node}/vote", json={"block": block.to_dict()}, timeout=5)
                if response.status_code == 200:
                    vote_data = response.json()
                    votes.append(vote_data.get("vote", False))
                    break  
            except requests.RequestException:
                retries -= 1
                time.sleep(delay)
                delay *= 2  
        else:
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
    database.init_db()
    init_blockchain()
    nodes.add(f"http://localhost:{NODE_PORT}")
    app.run(host="0.0.0.0", port=NODE_PORT)
