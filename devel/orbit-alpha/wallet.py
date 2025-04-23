import asyncio
import json
import websockets

class OrbitWallet:
    def __init__(self, node_address):
        self.node_address = node_address

    async def send_transaction(self, sender, receiver, amount):
        transaction = {
            "sender": sender,
            "receiver": receiver,
            "amount": amount,
            "timestamp": time.time()
        }
        
        async with websockets.connect(self.node_address) as websocket:
            await websocket.send(json.dumps({"type": "transaction", "transaction": transaction}))
            print(f"[Wallet] Transaction sent: {transaction}")

async def main():
    wallet = OrbitWallet("ws://localhost:8765")
    await wallet.send_transaction("Alice", "Bob", 10)

asyncio.run(main())
