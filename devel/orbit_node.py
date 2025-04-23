import hashlib
import blake3
import json
import time
import threading
import socket
from nacl.signing import SigningKey
from queue import Queue
import pickle
from typing import List, Dict, Any
#from transport_runner import TransportRunner
#from leo_node import LEO_Node
#from heo_node import HEO_Node
#from wallet_node import Wallet_Node

BASE_FEE = 0.1

def calculate_transaction_fee(mempool_size: int) -> float:
    if mempool_size <= 10:
        multiplier = 0
    elif mempool_size <= 50:
        multiplier = 0.5
    else:
        multiplier = min((mempool_size - 50) * 0.02 + 1.0, 10.0)  # cap at 10x base
    return round(BASE_FEE * (1 + multiplier), 4)

def compute_merkle_root(transactions):
    hashes = [blake3.blake3(json.dumps(tx, sort_keys=True).encode()).digest() for tx in transactions]
    if not hashes:
        return blake3.blake3(b'').hexdigest()
    while len(hashes) > 1:
        if len(hashes) % 2 != 0:
            hashes.append(hashes[-1])
        new_hashes = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i + 1]
            new_hashes.append(blake3.blake3(combined).digest())
        hashes = new_hashes
    return blake3.blake3(hashes[0]).hexdigest()

# ==== Core Node Class ====

class Node:
    def __init__(self, role: str, port: int, discovery_port: int = 8000):
        self.role = role
        self.node_id, self.signing_key = self.generate_node_id(role)
        self.ledger = []
        self.reputation = 1.0
        self.accuracy_score = 1.0
        self.port = port
        self.peers = []
        self.discovery_port = discovery_port
        self.mempool: List[Dict[str, Any]] = []

    def broadcast_announcement(self):
        announcement = {
            "node_id": self.node_id,
            "role": self.role,
            "port": self.port
        }
        for peer in self.peers:
            try:
                self.send_data(peer, {"announcement": announcement})
            except Exception as e:
                print(f"[{self.role}] Error broadcasting announcement to {peer}: {e}")

    def listen_for_announcements(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.bind(('0.0.0.0', self.discovery_port))
            print(f"[{self.role}] Listening for peer announcements on discovery port {self.discovery_port}...")
            while True:
                data, addr = s.recvfrom(1024)
                announcement = pickle.loads(data)
                self.handle_peer_announcement(announcement, addr)

    def handle_peer_announcement(self, announcement, addr):
        peer_id = announcement['node_id']
        peer_role = announcement['role']
        peer_port = announcement['port']
        peer_address = (addr[0], peer_port)
        if peer_address not in self.peers:
            self.peers.append(peer_address)
            print(f"[{self.role}] Discovered new peer {peer_id} ({peer_role}) at {peer_address}")
            self.add_peer(peer_address)

    def update_accuracy(self, correct_validations, total):
        if total > 0:
            self.accuracy_score = (correct_validations / total) * 0.8 + self.accuracy_score * 0.2

    def generate_node_id(self, role):
        key = SigningKey.generate()
        address_prefix = {'HEO': 'H-', 'LEO': 'L-', 'WALLET': 'W-'}[role]
        return address_prefix + key.verify_key.encode().hex(), key

    def hash_transaction(self, tx):
        return blake3.blake3(json.dumps(tx, sort_keys=True).encode()).hexdigest()

    def validate_transaction(self, tx):
        tx['fee'] = calculate_transaction_fee(len(self.mempool))
        tx['hash'] = self.hash_transaction(tx)
        return tx

    def add_block(self, txs):
        timestamp = time.time()
        validated = [self.validate_transaction(tx) for tx in txs]
        merkle_root = compute_merkle_root(validated)
        block = {
            "index": len(self.ledger),
            "timestamp": timestamp,
            "transactions": validated,
            "merkle_root": merkle_root,
            "prev_hash": self.ledger[-1]["block_hash"] if self.ledger else "0" * 64,
            "miner": self.node_id,
            "total_fees": sum(tx["fee"] for tx in validated),
        }
        block["block_hash"] = self.hash_block(block, timestamp)
        self.ledger.append(block)
        self.mempool = [tx for tx in self.mempool if tx not in validated]
        return block

    def validate_block(self, block):
        expected_merkle = compute_merkle_root(block["transactions"])
        return block.get("merkle_root") == expected_merkle and block.get("block_hash") == self.hash_block(block)

    def hash_block(self, block: Dict[str, Any], timestamp: float) -> str:
        block_copy = dict(block)
        block_copy["timestamp"] = timestamp
        block_str = json.dumps(block_copy, sort_keys=True).encode()
        return blake3.blake3(block_str).hexdigest()


    def add_peer(self, peer_address):
        self.peers.append(peer_address)

    def send_data(self, peer, data):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(peer)
                s.sendall(pickle.dumps(data))
        except Exception as e:
            print(f"[{self.role}] Error sending to {peer}: {e}")

    def receive_data(self, connection):
        data = connection.recv(4096)
        if data:
            return pickle.loads(data)
        return None

    def listen_for_peers(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('0.0.0.0', self.port))
            s.listen(5)
            print(f"[{self.role}] Listening for peers on port {self.port}...")
            while True:
                conn, addr = s.accept()
                threading.Thread(target=self.handle_connection, args=(conn, addr), daemon=True).start()

    def handle_connection(self, conn, addr):
        with conn:
            data = self.receive_data(conn)
            if data:
                self.process_received_data(data)

    def process_received_data(self, data):
        if isinstance(data, dict) and 'block' in data:
            print(f"[{self.role}] Received block: {data['block']['block_hash'][:10]}")
            self.add_block(data['block']['transactions'])
        elif isinstance(data, dict) and 'tx' in data:
            print(f"[{self.role}] Received transaction: {data['tx']['hash'][:10]}")
            if data['tx']['hash'] not in [tx['hash'] for tx in self.mempool]:
                self.mempool.append(data['tx'])



# ==== LEO Node ====

class LEO_Node(Node):
    def __init__(self, port):
        super().__init__('LEO', port)
        self.confirmations = {}
        self.confirmed_blocks = set()
        self.heo_peer = None
        self.seen_tx_hashes = set()
        self.mempool: List[Dict[str, Any]] = []
        self.ledger: List[Dict[str, Any]] = []

    def set_heo_peer(self, peer):
        self.heo_peer = peer

    def vote_on_block(self, block_hash):
        if block_hash not in self.confirmations:
            self.confirmations[block_hash] = set()
        self.confirmations[block_hash].add(self.node_id)

        for peer in self.peers:
            self.send_data(peer, {"vote": {"block_hash": block_hash, "voter": self.node_id}})

        if self.heo_peer:
            self.send_data(self.heo_peer, {"vote": {"block_hash": block_hash, "voter": self.node_id}})

        if len(self.confirmations[block_hash]) >= 3:
            self.confirmed_blocks.add(block_hash)
            for peer in self.peers:
                self.send_data(peer, {"confirmed_block": block_hash, "by": self.node_id})
            return True
        return False

    def broadcast_block(self, block):
        # Compute and inject the Merkle root
        block['merkle_root'] = compute_merkle_root(block['transactions'])

        # Remove already seen transactions
        filtered_txs = []
        for tx in block['transactions']:
            if tx['hash'] in self.seen_tx_hashes:
                print(f"[{self.role}] Transaction {tx['hash'][:10]} already processed. Skipping broadcast.")
                continue
            self.seen_tx_hashes.add(tx['hash'])
            filtered_txs.append(tx)

        block['transactions'] = filtered_txs

        if not block['transactions']:
            print(f"[{self.role}] No new transactions to broadcast in block.")
            return

        # Broadcast the updated block
        for peer in self.peers:
            self.send_data(peer, {"block": block})
        print(f"[{self.role}] Block {block['block_hash'][:10]} with Merkle root {block['merkle_root'][:10]} broadcasted to peers.")

    def start_peer_discovery(self):
        """Start broadcasting announcements periodically."""
        while True:
            time.sleep(10)  # Every 10 seconds
            self.broadcast_announcement()



# ==== HEO Node ====

class HEO_Node(Node):
    def __init__(self, port):
        super().__init__('HEO', port)
        self.confirmations = {}
        self.confirmed_blocks = set()
        self.seen_tx_hashes = set()  # Track processed transactions

    def process_received_data(self, data):
        if 'vote' in data:
            vote = data['vote']
            bh, voter = vote['block_hash'], vote['voter']
            if bh not in self.confirmations:
                self.confirmations[bh] = set()
            self.confirmations[bh].add(voter)
            if len(self.confirmations[bh]) >= 3 and bh not in self.confirmed_blocks:
                self.confirmed_blocks.add(bh)
                print(f"[HEO] Finalized block {bh[:10]}")

        elif 'block' in data:
            block = data['block']

            # Verify Merkle root
            expected_merkle_root = compute_merkle_root(block['transactions'])
            if block.get('merkle_root') != expected_merkle_root:
                print(f"[HEO] Block {block['block_hash'][:10]} has invalid Merkle root. Skipping...")
                return

            if self.contains_double_spends(block):
                print(f"[HEO] Block {block['block_hash'][:10]} contains double spends. Skipping...")
            else:
                super().process_received_data(data)

    def contains_double_spends(self, block):
        tx_hashes = set()
        for tx in block['transactions']:
            tx_hash = tx['hash']
            if tx_hash in tx_hashes or tx_hash in self.seen_tx_hashes:
                return True  # Found a double spend
            tx_hashes.add(tx_hash)

        # Mark transactions in this block as seen
        self.seen_tx_hashes.update(tx_hashes)
        return False

    def is_block_finalized(self, block_hash):
        return block_hash in self.confirmed_blocks

    def start_peer_discovery(self):
        """Start broadcasting announcements periodically."""
        while True:
            time.sleep(10)  # Every 10 seconds
            self.broadcast_announcement()


# ==== Wallet Node ====

class WalletNode(Node):
    def __init__(self, port):
        super().__init__('WALLET', port)
        self.balance = 100
        self.tx_history = []
        self.address = ('localhost', port)
        self.processed_blocks = set()  # Track processed blocks to prevent re-processing

    def create_transaction(self, to, amount, fee):
        total = amount + fee
        if total > self.balance:
            print(f"[Wallet] Not enough balance to send {amount} + fee {fee}")
            return None
        tx = {
            'sender': self.node_id,
            'receiver': to,
            'amount': amount,
            'fee': fee,
            'timestamp': time.time(),
            'hash': self.generate_tx_hash()
        }
        self.balance -= total
        self.tx_history.append(tx)
        return tx

    def process_received_data(self, data):
        if isinstance(data, dict):
            if 'block' in data:
                block = data['block']
                if block['block_hash'] not in self.processed_blocks:
                    self.apply_block(block)
                    self.processed_blocks.add(block['block_hash'])
            elif 'transactions' in data and 'block_hash' in data:
                self.apply_block(data)

    def apply_block(self, block):
        for tx in block['transactions']:
            involved = False
            if tx['receiver'] == self.node_id:
                self.balance += tx['amount']
                involved = True
            if tx['sender'] == self.node_id:
                involved = True
            if involved:
                self.tx_history.append(tx)
                direction = "Received" if tx['receiver'] == self.node_id else "Sent"
                print(f"[{self.role}] {direction} {tx['amount']} {'from' if direction == 'Received' else 'to'} {tx['sender' if direction == 'Received' else 'receiver'][:8]} (Block: {block['block_hash'][:10]})")

    def generate_tx_hash(self):
        # Generate a unique transaction hash (for simplicity, using timestamp and sender/receiver)
        return f"{time.time()}-{self.node_id}"

    def start_peer_discovery(self):
        """Start broadcasting announcements periodically."""
        while True:
           time.sleep(10)  # Every 10 seconds
           self.broadcast_announcement()



# ==== Transport Runner ====

class TransportRunner:
    def __init__(self, leo_nodes, heo_node, wallet_nodes):
        self.mempool = Queue()
        self.leo_nodes = leo_nodes
        self.heo_node = heo_node
        self.wallet_nodes = wallet_nodes

    def broadcast_transaction(self, tx):
        if "fee" not in tx:
            tx["fee"] = self.calculate_transaction_fee()
        tx["hash"] = blake3.blake3(json.dumps(tx, sort_keys=True).encode()).hexdigest()
        print(f"[TR] Broadcasting TX {tx['hash'][:10]} with fee {tx['fee']}")
        self.mempool.put(tx)

    def broadcast_block_to_wallets(self, block):
        for wallet in self.wallet_nodes:
            try:
                wallet.send_data(wallet.address, {'block': block})
            except Exception as e:
                print(f"[TR] Failed to send block to wallet {wallet}: {e}")

    def start_block_production(self):
        while True:
            time.sleep(5)
            tx_batch = []
            while not self.mempool.empty() and len(tx_batch) < 5:
                tx_batch.append(self.mempool.get())

            if tx_batch:
                print("[TR] Creating block...")
                # Generate Merkle root for this batch
                merkle_root = compute_merkle_root(tx_batch)
                # Create block via LEO and insert Merkle root
                block = self.leo_nodes[0].add_block(tx_batch)
                block['merkle_root'] = merkle_root  # Insert Merkle root

                for leo in self.leo_nodes:
                    leo.broadcast_block(block)
                for leo in self.leo_nodes:
                    leo.vote_on_block(block["block_hash"])

                time.sleep(1)
                if self.heo_node.is_block_finalized(block["block_hash"]):
                    self.broadcast_block_to_wallets(block)

    def calculate_transaction_fee(self) -> float:
        mempool_size = self.mempool.qsize()
        if mempool_size <= 10:
            multiplier = 0
        elif mempool_size <= 50:
            multiplier = 0.5
        else:
            multiplier = min((mempool_size - 50) * 0.02 + 1.0, 10.0)
        return round(BASE_FEE * (1 + multiplier), 4)

# ==== CLI ====

def run_repl(wallets, tr, nodes):
    print("\nOrbit CLI Ready.")
    print("Commands:")
    print("  send <from> <to> <amount>")
    print("  balance")
    print("  history <wallet>")
    print("  ledger <node>")
    print("  peers <node>")
    print("  connect <node> <host:port>")
    print("  discover <node>")
    print("  broadcast_block <node>")
    print("  create_wallet <name>")
    print("  exit\n")

    while True:
        cmd = input(">> ").strip().split()
        if not cmd:
            continue

        match cmd[0]:
            case "send" if len(cmd) == 4:
                sender, receiver, amount = cmd[1], cmd[2], float(cmd[3])
                if sender not in wallets or receiver not in wallets:
                    print("Invalid wallet names.")
                    continue
                fee = tr.calculate_transaction_fee()
                tx = wallets[sender].create_transaction(wallets[receiver].node_id, amount, fee)
                if tx:
                    tr.broadcast_transaction(tx)
            case "balance":
                for name, w in wallets.items():
                    print(f"{name}: {w.balance:.2f}")

            case "history" if len(cmd) == 2:
                wallet = cmd[1]
                if wallet in wallets:
                    for tx in wallets[wallet].tx_history:
                        print(json.dumps(tx, indent=2))
                else:
                    print("Unknown wallet.")

            case "ledger" if len(cmd) == 2:
                node = cmd[1]
                if node in nodes:
                    for i, block in enumerate(nodes[node].ledger):
                        print(f"\nBlock {i} - Hash: {block['block_hash'][:10]}")
                        for tx in block['transactions']:
                            print(f"  TX {tx['hash'][:10]}: {tx['sender']} -> {tx['receiver']} : {tx['amount']}")
                else:
                    print("Unknown node.")

            case "peers" if len(cmd) == 2:
                node = cmd[1]
                if node in nodes:
                    for p in nodes[node].peers:
                        print(f"{node} peer: {p}")
                else:
                    print("Unknown node.")

            case "connect" if len(cmd) == 3:
                node_name, target = cmd[1], cmd[2]
                host, port = target.split(":")
                port = int(port)
                if node_name in nodes:
                    nodes[node_name].add_peer((host, port))
                    print(f"{node_name} connected to {target}")
                else:
                    print("Unknown node.")

            case "broadcast_block" if len(cmd) == 2:
                node = cmd[1]
                if node in nodes:
                    if nodes[node].ledger:
                        block = nodes[node].ledger[-1]
                        for peer in nodes[node].peers:
                            nodes[node].send_data(peer, {"block": block})
                        print(f"Broadcasted block {block['block_hash'][:10]}")
                    else:
                        print("No blocks to broadcast.")
                else:
                    print("Unknown node.")

            case "create_wallet" if len(cmd) == 2:
                name = cmd[1]
                if name in wallets:
                    print(f"Wallet {name} already exists.")
                    continue
                port = 9100 + len(wallets) + 1
                new_wallet = WalletNode(port)
                wallets[name] = new_wallet
                nodes[name] = new_wallet
                threading.Thread(target=new_wallet.listen_for_peers, daemon=True).start()
                print(f"Created wallet {name} on port {port}")

                done = False
                while done == False:
                    for node_name, node in nodes.items():
                        if node_name.__contains__("leo"):
                            new_wallet.add_peer(("localhost", node.port))
                            node.add_peer(("localhost", port))
                            print(f"Connected wallet {name} to LEO {node_name}")
                            done = True

            case "exit":
                break

            case _:
                print("Unknown command.")

# ==== Main Runner ====
print("Starting Orbit with Automated Peer Discovery\n")
if __name__ == "__main__":
    # Create nodes
    heo = HEO_Node(9000)
    leo1 = LEO_Node(9001)
    leo2 = LEO_Node(9002)
    leo3 = LEO_Node(9003)
    w1 = WalletNode(9101)


    # Connect peers (initial connections can still be set manually)
    leo1.set_heo_peer(('localhost', 9000))
    leo2.set_heo_peer(('localhost', 9000))
    leo3.set_heo_peer(('localhost', 9000))

    leo1.add_peer(('localhost', 9002))
    leo1.add_peer(('localhost', 9003))
    leo2.add_peer(('localhost', 9001))
    leo2.add_peer(('localhost', 9003))
    leo3.add_peer(('localhost', 9001))
    leo3.add_peer(('localhost', 9002))

    # Start peer listeners
    threading.Thread(target=heo.listen_for_peers, daemon=True).start()
    threading.Thread(target=leo1.listen_for_peers, daemon=True).start()
    threading.Thread(target=leo2.listen_for_peers, daemon=True).start()
    threading.Thread(target=leo3.listen_for_peers, daemon=True).start()

    # Start Wallet listeners
    threading.Thread(target=w1.listen_for_peers, daemon=True).start()

    # Start peer discovery
    threading.Thread(target=heo.start_peer_discovery, daemon=True).start()
    threading.Thread(target=leo1.start_peer_discovery, daemon=True).start()
    threading.Thread(target=leo2.start_peer_discovery, daemon=True).start()
    threading.Thread(target=leo3.start_peer_discovery, daemon=True).start()

    # Init transport runner and block production
    tr = TransportRunner([leo1, leo2, leo3], heo, w1)
    threading.Thread(target=tr.start_block_production, daemon=True).start()

    # Setup REPL
    wallets = {"w1": w1}
    nodes = {"heo": heo, "leo1": leo1, "leo2": leo2, "leo3": leo3}
    run_repl(wallets, tr, nodes)
