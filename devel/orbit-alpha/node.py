import asyncio
import json
import websockets
import hashlib
import time
from typing import List, Dict, Set
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization, hashes

# ========== Quorum Slice ==========
class QuorumSlice:
    def __init__(self, validators: List[str]):
        self.validators = set(validators)

    def intersects(self, other: 'QuorumSlice') -> bool:
        return bool(self.validators & other.validators)

# ========== Blockchain Node ==========
class OrbitNode:
    def __init__(self, node_id, validators):
        self.node_id = node_id
        self.quorum = QuorumSlice(validators)
        self.ledger = []
        self.peers = set()
        self.pending_transactions = []
        self.private_key, self.public_key = self.generate_keys()
    
    def generate_keys(self):
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        return private_key, public_key

    def sign_transaction(self, transaction):
        signature = self.private_key.sign(
            json.dumps(transaction, sort_keys=True).encode(),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        return signature.hex()

    async def handle_connection(self, websocket, path):
        async for message in websocket:
            data = json.loads(message)
            if data["type"] == "transaction":
                await self.process_transaction(data["transaction"])
            elif data["type"] == "consensus":
                await self.run_consensus(data["transactions"])

    async def process_transaction(self, transaction):
        self.pending_transactions.append(transaction)

    async def run_consensus(self, transactions):
        print(f"[{self.node_id}] Running Consensus on {len(transactions)} transactions...")
        transactions_hash = hashlib.sha256(json.dumps(transactions, sort_keys=True).encode()).hexdigest()
        
        # Step 1: Nomination (Propose Transactions)
        await self.broadcast({"type": "nominate", "transactions": transactions})

        # Step 2: Voting (Simulating agreement)
        votes = {peer: transactions_hash for peer in self.peers}
        
        # Step 3: Finalization
        if len(votes) > len(self.peers) // 2:
            self.ledger.append({"transactions": transactions, "hash": transactions_hash})
            print(f"[{self.node_id}] Block finalized with hash: {transactions_hash}")

    async def broadcast(self, message):
        for peer in self.peers:
            async with websockets.connect(peer) as websocket:
                await websocket.send(json.dumps(message))

# ========== Start Node ==========
async def main():
    node = OrbitNode("node_1", ["node_2", "node_3"])
    server = await websockets.serve(node.handle_connection, "localhost", 8765)
    print("[Node] Orbit Blockchain Node is running...")
    await server.wait_closed()

asyncio.run(main())
