import asyncio
import aiohttp
import time
import random
import string

API_URL = "http://localhost:5000"

def generate_address():
    """Generate a random wallet address."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))

async def get_latest_tx_id(session):
    """Fetch the latest block and determine the next transaction ID."""
    async with session.get(f"{API_URL}/blockchain") as response:
        if response.status == 200:
            blockchain = await response.json()
            if blockchain:
                last_block = blockchain[-1]
                return f"TX{last_block['block_index'] + 1}"
        return "TX1"  # If no blocks exist, start from TX1

async def submit_transaction(session, tx_id):
    """Submit a transaction with random sender, receiver, amount, and fee."""
    sender = generate_address()
    receiver = generate_address()
    amount = round(random.uniform(1, 100), 2)  # Random amount between 1 and 100
    fee = round(random.uniform(0.01, 1), 2)    # Random fee between 0.01 and 1

    transaction = {
        "tx_id": tx_id,
        "sender": sender,
        "receiver": receiver,
        "amount": amount,
        "fee": fee
    }

    # Fetch recent blocks to generate valid PoA proof
    async with session.get(f"{API_URL}/recent_blocks") as response:
        if response.status == 200:
            recent_blocks = await response.json()
        else:
            recent_blocks = []

    poa_proof = [{"tx_id": tx_id, "transaction": transaction}] if recent_blocks else [{"tx_id": "GENESIS", "transaction": "GENESIS_PoA"}]

    async with session.post(f"{API_URL}/propose_block", json={"proposer": sender, "data": [transaction], "poa_proof": poa_proof}) as response:
        return await response.json(), response.status

async def get_blockchain(session):
    """Fetch and print the blockchain."""
    async with session.get(f"{API_URL}/blockchain") as response:
        return await response.json(), response.status

async def test_blockchain():
    """Main test function."""
    async with aiohttp.ClientSession() as session:
        # Get the latest transaction ID
        latest_tx_id = await get_latest_tx_id(session)

        print("Submitting transaction...")
        tx_response, tx_status = await submit_transaction(session, latest_tx_id)
        print(f"Transaction response ({tx_status}):", tx_response)

        print("\nFetching blockchain...")
        chain_response, chain_status = await get_blockchain(session)
        print(f"Blockchain response ({chain_status}):", chain_response)

if __name__ == "__main__":
    asyncio.run(test_blockchain())
