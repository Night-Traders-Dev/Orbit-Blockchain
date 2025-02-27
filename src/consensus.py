import database

def verify_poa_proof(poa_proof):
    """Verify if the proposer accurately validated historical transactions."""
    if database.is_blockchain_empty():
        print("[INFO] No previous transactions. Accepting genesis block.")
        return True

    for proof in poa_proof:
        tx_id = proof.get("tx_id")
        original_tx = database.get_transaction(tx_id)

        if not original_tx or original_tx != proof["transaction"]:
            return False  # Invalid proof

    return True  # Valid proof

def validate_block_poa(block_data):
    """Validate Proof of Accuracy (PoA) for a received block."""
    poa = block_data.get("proof_of_accuracy")
    if not poa:
        print("[ERROR] Block missing Proof of Accuracy.")
        return False

    # Retrieve recent blocks for PoA validation
    history = database.get_recent_blocks(limit=5)  # Get last 5 blocks
    if not history:
        return True  # If no history, assume first few blocks bootstrap the chain

    # Compute expected PoA based on historical blocks
    expected_poa = hash(",".join(str(b.hash) for b in history))
    is_valid = (poa == expected_poa)

    if not is_valid:
        print(f"[ERROR] Invalid Proof of Accuracy for block {block_data['block_index']}")

    return is_valid

def compute_poa(history):
    """Generate deterministic PoA hash from recent block history."""
    history_str = ",".join(f"{b.block_index}:{b.hash}" for b in sorted(history, key=lambda x: x.block_index))
    return hashlib.sha256(history_str.encode()).hexdigest()
