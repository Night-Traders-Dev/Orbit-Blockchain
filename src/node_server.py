import sys
import time
import threading
import hashlib
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# ----------------------------
# Global Storage
# ----------------------------
blockchain = []
transactions = []  # List of pending transactions
spent_txns = set()  # Set to track spent transactions
nodes = set()  # Active nodes in the network

# Replace with the actual address of the node operator
NODE_OPERATOR_ADDRESS = "heoEnsiaowm391"

# ----------------------------
# Block Class
# ----------------------------
class Block:
    def __init__(self, index, previous_hash, timestamp, data, proposer):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.proposer = proposer
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = f"{self.index}{self.previous_hash}{self.timestamp}{json.dumps(self.data)}{self.proposer}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self):
        return {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "data": self.data,
            "proposer": self.proposer,
            "hash": self.hash
        }

# ----------------------------
# Blockchain Initialization
# ----------------------------
def init_blockchain():
    if not blockchain:
        genesis = Block(0, "0", time.time(), [{"genesis": True}], "genesis")
        blockchain.append(genesis)

init_blockchain()

# ----------------------------
# Node Discovery & Management
# ----------------------------
@app.route('/nodes', methods=['GET'])
def get_nodes():
    return jsonify(list(nodes)), 200

def discover_nodes():
    """ Connects to an existing node to discover peers """
    global nodes
    try:
        response = requests.get("http://existing-node:5000/nodes")
        if response.status_code == 200:
            nodes.update(response.json())
    except:
        print("No existing nodes found. Initializing node list.")
        nodes.add(f"http://localhost:{NODE_PORT}")

# ----------------------------
# Transaction Processing
# ----------------------------
def process_transaction(tx_data, proposer):
    """ Processes transactions and adds node operator rewards """
    total_fee = sum(tx["fee"] for tx in tx_data)

    # Reward the node operator
    reward_tx = {
        "tx_id": f"reward_{time.time()}",
        "sender": "network",
        "receiver": proposer,
        "amount": total_fee,
        "fee": 0
    }

    tx_data.append(reward_tx)
    return tx_data

# ----------------------------
# Blockchain Endpoints
# ----------------------------
@app.route('/blockchain', methods=['GET'])
def get_blockchain():
    """ Returns the current blockchain """
    return jsonify([block.to_dict() for block in blockchain]), 200

@app.route('/propose_block', methods=['POST'])
def propose_block():
    """ Propose a new block and collect votes """
    data = request.get_json()
    proposer = data.get("proposer")
    tx_data = data.get("data")

    if not proposer or not tx_data:
        return jsonify({"error": "Missing proposer or data"}), 400

    # Validate transactions
    for txn in tx_data:
        tx_id = txn.get("tx_id")
        if tx_id in spent_txns:
            return jsonify({"error": f"Double spend detected: {tx_id}"}), 400

    # Process transactions (include miner reward)
    tx_data = process_transaction(tx_data, proposer)

    last_block = blockchain[-1]
    new_block = Block(last_block.index + 1, last_block.hash, time.time(), tx_data, proposer)

    # Broadcast the block for voting
    votes = collect_votes(new_block)

    # If majority votes yes, add the block
    if votes.count(True) > votes.count(False):
        blockchain.append(new_block)
        for txn in tx_data:
            spent_txns.add(txn["tx_id"])

        threading.Thread(target=broadcast_block, args=(new_block,)).start()
        return jsonify({"status": "Block added", "block": new_block.to_dict()}), 200
    else:
        return jsonify({"error": "Block rejected by network"}), 400

@app.route('/vote', methods=['POST'])
def vote():
    """ Validate and vote on a proposed block """
    data = request.get_json()
    block_data = data.get("block")

    if not block_data:
        return jsonify({"error": "No block data provided"}), 400

    last_block = blockchain[-1].to_dict()

    # Check if the block is valid
    vote = (
        block_data["previous_hash"] == last_block["hash"] and
        block_data["index"] == last_block["index"] + 1
    )

    return jsonify({"vote": vote}), 200

@app.route('/receive_block', methods=['POST'])
def receive_block():
    """ Receive and validate a block from the network """
    data = request.get_json()
    block_data = data.get("block")

    if not block_data:
        return jsonify({"error": "No block data provided"}), 400

    last_block = blockchain[-1].to_dict()
    if block_data["previous_hash"] == last_block["hash"] and block_data["index"] == last_block["index"] + 1:
        new_block = Block(
            block_data["index"],
            block_data["previous_hash"],
            block_data["timestamp"],
            block_data["data"],
            block_data["proposer"]
        )
        blockchain.append(new_block)
        print(f"Node on port {NODE_PORT} added broadcasted block.")
        return jsonify({"status": "Block added"}), 200
    else:
        return jsonify({"error": "Invalid block"}), 400

# ----------------------------
# Transaction Handling
# ----------------------------
@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    """ Accepts a new transaction """
    data = request.get_json()
    tx_id = data.get("tx_id")

    if not tx_id or tx_id in spent_txns:
        return jsonify({"error": "Invalid or duplicate transaction"}), 400

    transactions.append(data)
    return jsonify({"status": "Transaction added"}), 200

# ----------------------------
# Health Check
# ----------------------------
@app.route('/', methods=['GET'])
def index():
    """ Check if the node is running """
    return jsonify({"status": f"Node running on port {NODE_PORT}"}), 200

# ----------------------------
# Network Broadcasting
# ----------------------------
def collect_votes(block):
    """ Ask all nodes to vote on a proposed block """
    votes = []
    for node in nodes:
        try:
            response = requests.post(f"{node}/vote", json={"block": block.to_dict()})
            if response.status_code == 200:
                vote_data = response.json()
                votes.append(vote_data.get("vote", False))
        except:
            print(f"Failed to get vote from {node}")
            votes.append(False)
    return votes

def broadcast_block(block):
    """ Broadcast a newly added block to all nodes """
    print(f"Broadcasting block: {block.to_dict()}")
    for node in nodes:
        try:
            requests.post(f"{node}/receive_block", json={"block": block.to_dict()})
        except:
            print(f"Failed to send block to {node}")

# ----------------------------
# Start Node
# ----------------------------
if __name__ == '__main__':
    NODE_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"Starting node on port {NODE_PORT}")
    discover_nodes()
    nodes.add(f"http://localhost:{NODE_PORT}")  # Add itself to the network
    app.run(host="0.0.0.0", port=NODE_PORT)
