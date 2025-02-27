import time
import hashlib
import json

class Block:
    def __init__(self, block_index, previous_hash, timestamp, data, proposer, proof_of_accuracy=None):
        self.block_index = block_index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.proposer = proposer
        self.proof_of_accuracy = proof_of_accuracy or self.generate_proof_of_accuracy()
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        """Calculate the SHA-256 hash of the block contents, including PoA."""
        block_string = f"{self.block_index}{self.previous_hash}{self.timestamp}{json.dumps(self.data)}{self.proposer}{self.proof_of_accuracy}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def generate_proof_of_accuracy(self):
        """Generates PoA by hashing the last 5 blocks' hashes (or fewer if unavailable)."""
        from database import get_recent_blocks  # Avoids circular import
        recent_blocks = get_recent_blocks(limit=5)

        if not recent_blocks:
            return "GENESIS_PoA"  # Special case for the first block

        poa_string = ",".join(block.hash for block in recent_blocks)
        return hashlib.sha256(poa_string.encode()).hexdigest()

    def to_dict(self):
        """Convert block attributes to dictionary format."""
        return {
            "block_index": self.block_index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "data": self.data,
            "proposer": self.proposer,
            "proof_of_accuracy": self.proof_of_accuracy,
            "hash": self.hash
        }
