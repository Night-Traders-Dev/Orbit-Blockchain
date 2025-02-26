import sys
import threading
import requests
from flask import Flask, request, jsonify
from blockchain import init_blockchain, add_block, blockchain

app = Flask(__name__)

nodes = set()  # List of known nodes

NODE_OPERATOR_ADDRESS = "node_operator_123"

init_blockchain()

@app.route('/blockchain', methods=['GET'])
def get_blockchain():
    """Returns the current blockchain."""
    return jsonify([block.to_dict() for block in blockchain]), 200

@app.route('/propose_block', methods=['POST'])
def propose_block():
    """Handles block proposal."""
    data = request.get_json()
    proposer = data.get("proposer")
    tx_data = data.get("data")

    if not proposer or not tx_data:
        return jsonify({"error": "Missing proposer or data"}), 400

    new_block = add_block(tx_data, proposer)

    # Broadcast to network
    threading.Thread(target=broadcast_block, args=(new_block,)).start()
    
    return jsonify({"status": "Block added", "block": new_block.to_dict()}), 200

@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    """Accepts a new transaction."""
    data = request.get_json()
    tx_id = data.get("tx_id")

    if not tx_id:
        return jsonify({"error": "Invalid transaction"}), 400

    return jsonify({"status": "Transaction added"}), 200

@app.route('/receive_block', methods=['POST'])
def receive_block():
    """Receives a new block from the network."""
    data = request.get_json()
    block_data = data.get("block")

    if not block_data:
        return jsonify({"error": "No block data provided"}), 400

    new_block = Block(
        block_data["index"],
        block_data["previous_hash"],
        block_data["timestamp"],
        block_data["data"],
        block_data["proposer"]
    )

    blockchain.append(new_block)
    return jsonify({"status": "Block added"}), 200

def broadcast_block(block):
    """Broadcast a newly added block to all nodes."""
    for node in nodes:
        try:
            requests.post(f"{node}/receive_block", json={"block": block.to_dict()})
        except:
            print(f"Failed to send block to {node}")

if __name__ == '__main__':
    NODE_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"Starting node on port {NODE_PORT}")
    nodes.add(f"http://localhost:{NODE_PORT}")  # Add itself to the network
    app.run(host="0.0.0.0", port=NODE_PORT)
