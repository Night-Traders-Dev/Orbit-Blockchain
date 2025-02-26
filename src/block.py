import time
import hashlib
import json

class Block:
    def __init__(self, block_index, previous_hash, timestamp, data, proposer):
        self.block_index = block_index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.data = data
        self.proposer = proposer
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block_string = f"{self.block_index}{self.previous_hash}{self.timestamp}{json.dumps(self.data)}{self.proposer}"
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self):
        return {
            "block_index": self.block_index,
            "previous_hash": self.previous_hash,
            "timestamp": self.timestamp,
            "data": self.data,
            "proposer": self.proposer,
            "hash": self.hash
        }
