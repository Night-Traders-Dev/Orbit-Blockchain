import requests
import random
import time
import threading

NODE_URLS = [
    "http://localhost:5000" #,
#    "http://localhost:5001",
#    "http://localhost:5002"
]

NUM_CLIENTS = 100
client_ids = [f"Client{i}" for i in range(1, NUM_CLIENTS + 1)]
client_ids.append("Genesis")

local_balances = {
    client_id: random.uniform(100, 1000) if client_id != "Genesis" else 0.0
    for client_id in client_ids
}

block_count = 0
lock = threading.Lock()

def propose_transaction(sender, receiver, amount, fee):
    """ Propose a transaction to a node. """
    if amount <= 0:
        print(f"[{sender}] Invalid transaction: cannot send 0 tokens.")
        return False

    tx_id = f"{sender}_{receiver}_{int(time.time())}"
    payload = {
        "proposer": sender,
        "data": [{"tx_id": tx_id, "sender": sender, "receiver": receiver, "amount": amount, "fee": fee}]
    }

    random.shuffle(NODE_URLS)  # Shuffle to balance load
    for node_url in NODE_URLS:
        try:
            response = requests.post(f"{node_url}/propose_block", json=payload, timeout=5)
            if response.status_code == 200:
                print(f"[{sender}] Transaction successful via {node_url}: {payload['data']}")
                return True
            else:
                print(f"[{sender}] Node {node_url} rejected transaction: {response.json()}")
        except requests.RequestException as e:
            print(f"[{sender}] Connection error to {node_url}: {e}")

    print(f"[{sender}] Transaction failed.")
    return False

def distribute_genesis_funds():
    """ Distribute Genesis funds equally among clients. """
    global local_balances
    with lock:
        genesis_balance = local_balances["Genesis"]
        if genesis_balance <= 0:
            return

        receivers = [client for client in client_ids if client != "Genesis"]
        amount_per_client = round(genesis_balance / len(receivers), 2)

        if amount_per_client <= 0:
            return

        print(f"\n[Genesis Distribution] {genesis_balance:.2f} distributed ({amount_per_client:.2f} per client)")

        for client in receivers:
            local_balances[client] += amount_per_client
            propose_transaction("Genesis", client, amount_per_client, 0)

        local_balances["Genesis"] = 0

def simulate_transaction():
    """ Simulate a transaction between random clients. """
    global block_count
    with lock:
        senders = [s for s in local_balances if s != "Genesis" and local_balances[s] > 0]
        if not senders:
            print("No sender has a positive balance.")
            return False

        sender = random.choice(senders)
        receiver = random.choice([r for r in client_ids if r != sender])

        sender_balance = local_balances[sender]
        amount = round(random.uniform(0.01 * sender_balance, 0.10 * sender_balance), 2)
        fee = round(amount * 0.0005, 4)  # 0.05% fee
        total_deduction = amount + fee

        if total_deduction > sender_balance:
            return True  # Retry later

        local_balances[sender] -= total_deduction
        local_balances[receiver] += amount
        local_balances["Genesis"] += fee
        block_count += 1

        print(f"Block {block_count} processed.")

    success = propose_transaction(sender, receiver, amount, fee)
    
    if block_count % 50 == 0:
        distribute_genesis_funds()

    return success

def transaction_worker():
    """ Run transactions in a controlled loop. """
    while True:
        if not simulate_transaction():
            print("Terminating transaction simulation.")
            break
        time.sleep(random.uniform(0.1, 0.5))  # Random delay

if __name__ == '__main__':
    print("Starting transaction simulation with 100 clients plus Genesis.")
    
    for client, bal in local_balances.items():
        print(f"{client}: {bal:.2f}")

    num_threads = 5  # Limit concurrency
    threads = [threading.Thread(target=transaction_worker) for _ in range(num_threads)]
    
    for t in threads:
        t.start()

    for t in threads:
        t.join()
