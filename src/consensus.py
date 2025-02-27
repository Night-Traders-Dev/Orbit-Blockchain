import hashlib
import database
import json

def generate_poa(recent_blocks):
    """Generate Proof of Accuracy (PoA) from recent blocks."""
    if not recent_blocks:
        return [{"tx_id": "GENESIS", "transaction": "GENESIS_PoA"}]

    poa_proof = []

    for block in recent_blocks:
        for tx in block.get("data", []):  # Ensure transactions exist
            if isinstance(tx, dict) and "tx_id" in tx:                                                               poa_proof.append({"tx_id": tx["tx_id"], "transaction": tx})

    return poa_proof

def verify_poa_proof(poa_proof):
    """Verify the Proof of Accuracy from proposer."""
    if not isinstance(poa_proof, list):
        print("[ERROR] PoA proof is not a list.")
        return False

    for poa_entry in poa_proof:
        if not isinstance(poa_entry, dict) or "tx_id" not in poa_entry or "transaction" not in poa_entry:
            print(f"[ERROR] Invalid PoA entry: {poa_entry}")
            return False

    return True

def validate_block_poa(block_data):
    """Validate Proof of Accuracy (PoA) for a received block."""
    poa = block_data.get("proof_of_accuracy")
    if not poa:
        print("[ERROR] Block missing Proof of Accuracy.")
        return False

    history = database.get_recent_blocks(limit=5)  # Get last 5 blocks
    if not history:
        return True  # If no history, assume first few blocks bootstrap the chain

    expected_poa = compute_poa(history)
    is_valid = (poa == expected_poa)

    if not is_valid:
        print(f"[ERROR] Invalid Proof of Accuracy for block {block_data['block_index']}")

    return is_valid

def compute_poa(history):
    """Generate deterministic PoA hash from recent block history."""
    try:
        # Ensure history is sorted based on 'block_index' key
        sorted_history = sorted(history, key=lambda x: x["block_index"] if isinstance(x, dict) else x.block_index)

        # Generate a string from block hashes
        history_str = ",".join(str(b["hash"]) if isinstance(b, dict) else b.hash for b in sorted_history)

        # Compute SHA-256 hash
        return hashlib.sha256(history_str.encode()).hexdigest()
    except Exception as e:
        print(f"[ERROR] Failed to compute PoA: {e}")
        return "INVALID_PoA"
