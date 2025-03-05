import asyncio
import sys
import time
import aiohttp
from flask import Flask, request, jsonify
from blockchain import init_blockchain, get_latest_block, approve_and_add_block
from block import Block
from consensus import verify_poa_proof, validate_block_poa, compute_poa, generate_poa
import database

app = Flask(__name__)
nodes = set()

NODE_OPERATOR_ADDRESS = "heoEnsiaowm391"

@app.route('/nodes', methods=['GET'])
def get_nodes():
    """Returns the list of known nodes."""
    return jsonify(list(nodes)), 200

@app.route('/blockchain', methods=['GET'])
async def get_blockchain():
    """Returns the current blockchain from the database."""
    try:
        blocks = await database.get_all_blocks()
        if not blocks:
            return jsonify({"message": "No blocks found in the blockchain."}), 404

        blockchain_data = [block.to_dict() for block in blocks]
        return jsonify(blockchain_data), 200
    except Exception as e:
        print(f"[ERROR] Failed to fetch blockchain: {e}")
        return jsonify({"error": "Internal server error, could not fetch blockchain."}), 500

@app.route('/propose_block', methods=['POST'])
async def propose_block():
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
        if await database.is_transaction_spent(txn["tx_id"]):
            return jsonify({"error": f"Double spend detected: {txn['tx_id']}"}), 400
        if txn["amount"] <= 0 or txn["fee"] < 0:
            return jsonify({"error": f"Invalid transaction amounts: {txn}"}), 400

    last_block = await get_latest_block()
    new_block = Block(
        block_index=last_block.block_index + 1,
        previous_hash=last_block.hash,
        timestamp=time.time(),
        data=tx_data,
        proposer=proposer
    )

    if not await verify_poa_proof(poa_proof):
        return jsonify({"error": "Invalid Proof of Accuracy"}), 400

    votes = await collect_votes(new_block)
    if votes.count(True) > votes.count(False):
        await approve_and_add_block(new_block, tx_data)
        await database.mark_transaction_as_spent(txn["tx_id"])
        return jsonify({"status": "Block added", "block": new_block.to_dict()}), 200
    else:
        await approve_and_add_block(new_block, tx_data)
        await database.mark_transaction_as_spent(txn["tx_id"])
        return jsonify({"status": "Block added", "block": new_block.to_dict()}), 200
#        return jsonify({"error": "Block rejected by network"}), 400

@app.route('/recent_blocks', methods=['GET'])
async def get_recent_blocks():
    """Return the last 5 blocks for Proof of Accuracy verification."""
    recent_blocks = await database.get_recent_blocks(1)
    if not recent_blocks:
        return jsonify({"error": "No recent blocks found"}), 400
    return jsonify([block.to_dict() for block in recent_blocks]), 200

@app.route('/vote', methods=['POST'])
async def vote():
    """Vote on a proposed block based on its validity and Proof of Accuracy."""
    data = request.get_json()
    block_data = data.get("block")
    poa_proof = data.get("poa_proof")

    if not block_data or not poa_proof:
        return jsonify({"error": "No block data or PoA proof provided"}), 400

    last_block = await get_latest_block()
    if last_block is None:
        return jsonify({"error": "Failed to retrieve latest block"}), 500

    is_valid = (block_data["previous_hash"] == last_block.hash and
                block_data["block_index"] == last_block.block_index + 1)

    if is_valid and verify_poa_proof(poa_proof):
        return jsonify({"vote": True}), 200
    else:
        return jsonify({"vote": False}), 400

async def collect_votes(block):
    """Ask nodes to vote asynchronously."""
    if not nodes:
        print("[INFO] No nodes available. Auto-approving block.")
        return [True]

    votes = []
    async with aiohttp.ClientSession() as session:
        for node in nodes:
            try:
                async with session.post(f"{node}/vote", json={"block": block.to_dict()}) as response:
                    if response.status == 200:
                        vote_data = await response.json()
                        votes.append(vote_data.get("vote", False))
            except aiohttp.ClientError:
                votes.append(False)
    return votes

@app.route('/broadcast_block', methods=['POST'])
async def broadcast_block():
    """API endpoint to broadcast a newly added block to all nodes."""
    data = request.get_json()
    if not data or 'block' not in data:
        return jsonify({"error": "Invalid request, 'block' missing"}), 400

    block = data['block']
    failed_nodes = []

    async with aiohttp.ClientSession() as session:
        for node in nodes:
            try:
                async with session.post(f"{node}/receive_block", json={"block": block}) as response:
                    if response.status != 200:
                        failed_nodes.append(node)
            except aiohttp.ClientError:
                failed_nodes.append(node)

    if failed_nodes:
        return jsonify({"message": "Block broadcasted with some failures", "failed_nodes": list(failed_nodes)}), 207
    return jsonify({"message": "Block successfully broadcasted to all nodes"}), 200

async def main():
    await database.init_db()  # Initialize database first
    await init_blockchain()  # Ensure blockchain gets initialized correctly
    nodes.add(f"http://localhost:{NODE_PORT}")
    app.run(host="0.0.0.0", port=NODE_PORT)

if __name__ == '__main__':
    NODE_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"Starting node on port {NODE_PORT}")

    asyncio.run(main())  # Use a single asyncio.run() call

