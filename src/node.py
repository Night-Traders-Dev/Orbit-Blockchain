import sys
import time
import threading
import json
import requests
from flask import Flask, request, jsonify
from blockchain import init_blockchain, get_latest_block
from block import Block
import database

app = Flask(__name__)

nodes = set()
transactions = []  # List of pending transactions
spent_txns = set()  # Set to track spent transactions

NODE_OPERATOR_ADDRESS = "heoEnsiaowm391"

@app.route('/blockchain', methods=['GET'])
def get_blockchain():
    """Returns the current blockchain."""
    return jsonify([block.to_dict() for block in blockchain]), 200

@app.route('/propose_block', methods=['POST'])
def propose_block():
    """Propose a new block and collect votes."""
    data = request.get_json()
    proposer = data.get("proposer")
    tx_data = data.get("data")

    if not proposer or not tx_data:
        return jsonify({"error": "Missing proposer or data"}), 400

    for txn in tx_data:
        if txn["tx_id"] in spent_txns:
            return jsonify({"error": f"Double spend detected: {txn['tx_id']}"}), 400

    last_block = get_latest_block()
    new_block = Block(last_block. block_index + 1, last_block.hash, time.time(), tx_data, proposer)

    votes = collect_votes(new_block)

    if votes.count(True) > votes.count(False):
        database.insert_block(new_block)
        spent_txns.update(tx["tx_id"] for tx in tx_data)
        threading.Thread(target=broadcast_block, args=(new_block,)).start()
        return jsonify({"status": "Block added", "block": new_block.to_dict()}), 200
    else:
        return jsonify({"error": "Block rejected by network"}), 400

@app.route('/vote', methods=['POST'])
def vote():
    """Validate and vote on a proposed block."""
    data = request.get_json()
    block_data = data.get("block")

    if not block_data:
        return jsonify({"error": "No block data provided"}), 400

    last_block = get_latest_block().to_dict()

    vote = (block_data["previous_hash"] == last_block["hash"] and
            block_data["block_index"] == last_block["block_index"] + 1)

    return jsonify({"vote": vote}), 200

@app.route('/receive_block', methods=['POST'])
def receive_block():
    """Receive and validate a block from the network."""
    data = request.get_json()
    block_data = data.get("block")

    if not block_data:
        return jsonify({"error": "No block data provided"}), 400

    last_block = get_latest_block().to_dict()

    if block_data["previous_hash"] == last_block["hash"] and block_data["block_index"] == last_block["block_index"] + 1:
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

    if not tx_id or tx_id in spent_txns:
        return jsonify({"error": "Invalid or duplicate transaction"}), 400

    transactions.append(data)
    return jsonify({"status": "Transaction added"}), 200

def collect_votes(block):
    """Ask all nodes to vote on a proposed block."""
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
    app.run(host="0.0.0.0", port=NODE_PORT)
