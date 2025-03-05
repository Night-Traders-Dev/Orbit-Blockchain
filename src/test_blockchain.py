import asyncio
import aiohttp
import time

API_URL = "http://localhost:5000"

async def submit_transaction(session, tx_id, sender, receiver, amount, fee):
    """Simulates submitting a transaction."""
    transaction = {
        "tx_id": tx_id,
        "sender": sender,
        "receiver": receiver,
        "amount": amount,
        "fee": fee
    }
    async with session.post(f"{API_URL}/propose_block", json={"proposer": sender, "data": [transaction], "poa_proof": [{"tx_id": tx_id, "transaction": transaction}]}) as response:
        return await response.json(), response.status

async def get_blockchain(session):
    """Fetch the blockchain state."""
    async with session.get(f"{API_URL}/blockchain") as response:
        return await response.json(), response.status

async def test_blockchain():
    """Main test function."""
    async with aiohttp.ClientSession() as session:
        print("Submitting transaction...")
        tx_response, tx_status = await submit_transaction(session, "TX123", "Alice", "Bob", 10, 1)
        print(f"Transaction response ({tx_status}):", tx_response)

        print("\nFetching blockchain...")
        chain_response, chain_status = await get_blockchain(session)
        print(f"Blockchain response ({chain_status}):", chain_response)

if __name__ == "__main__":
    asyncio.run(test_blockchain())
