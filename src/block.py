import hashlib
import json
from typing import Optional


class Block:
    def __init__(self, block_index: int, previous_hash: str, timestamp: float, data: list, proposer: str, proof_of_accuracy: Optional[str] = None):
        self.block_index = block_index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.proposer = proposer
        self.proof_of_accuracy = proof_of_accuracy
        self.hash = None

    async def initialize(self):
        """Asynchronously initialize PoA and hash."""
        from database import get_recent_blocks
        from consensus import compute_poa
        if self.proof_of_accuracy is None:
            recent_blocks = await get_recent_blocks(limit=5)
            self.proof_of_accuracy = await compute_poa(recent_blocks)
        self.hash = self.calculate_hash()

    def calculate_hash(self) -> str:
        """Calculate the SHA-256 hash of the block contents, including PoA."""
        block_string = f"{self.block_index}{self.previous_hash}{self.timestamp}{json.dumps(self.data)}{self.proposer}{self.proof_of_accuracy}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self) -> dict:
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
