import requests
import json
import sys
import time

def get_nodes(node_url):
    """Fetch known nodes from the given node."""
    url = f"{node_url}/nodes"
    try:
        response = requests.get(url, timeout=5)
        nodes = response.json()
        if isinstance(nodes, list):
            return nodes
    except (requests.RequestException, json.JSONDecodeError):
        pass
    return [node_url]  # Default to the given node if discovery fails

def fetch_blockchain(node_url):
    """Fetch blockchain data from the node."""
    url = f"{node_url}/blockchain"
    try:
        response = requests.get(url, timeout=5)
        data = response.json()

        if not isinstance(data, list):  # Ensure response is a list of blocks
            print(f"[{node_url}] Unexpected API response format.")
            return None

        return data  # Return list of blocks
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Error fetching blockchain from {node_url}: {e}")
        return None

def view_node_stats(node_url):
    """Process blockchain stats based on the fetched data."""
    blockchain_data = fetch_blockchain(node_url)
    if not blockchain_data:
        return None

    total_blocks = len(blockchain_data)
    transactions = []
    total_amount_sent = 0
    total_fees_collected = 0

    for block in blockchain_data:
        tx_data = block.get("data", [])

        if not isinstance(tx_data, list):  # Ensure transactions are properly formatted
            print(f"[{node_url}] Invalid transaction format in block {block.get('block_index', 'unknown')}")
            continue

        transactions.extend(tx_data)
        total_amount_sent += sum(float(tx.get("amount", 0)) for tx in tx_data)
        total_fees_collected += sum(float(tx.get("fee", 0)) for tx in tx_data)

    total_transactions = len(transactions)

    last_five_tx = [
        f"{tx.get('sender', 'Unknown')} → {tx.get('receiver', 'Unknown')} | {tx.get('amount', 0)} units | Fee: {tx.get('fee', 0)} | TX ID: {tx.get('tx_id', 'N/A')}"
        for tx in transactions[-5:]
    ]

    return {
        "node": node_url,
        "total_blocks": total_blocks,
        "total_transactions": total_transactions,
        "total_amount_sent": total_amount_sent,
        "total_fees_collected": total_fees_collected,
        "last_transactions": last_five_tx
    }

if __name__ == '__main__':
    nodes_arg = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
    initial_nodes = [url.strip() for url in nodes_arg.split(",")]

    print("Starting Block Explorer (updating every 10 seconds)...")
    try:
        while True:
            all_stats = []
            known_nodes = set(initial_nodes)

            for node_url in list(known_nodes):
                discovered_nodes = get_nodes(node_url)
                known_nodes.update(discovered_nodes)

            for node_url in known_nodes:
                stats = view_node_stats(node_url)
                if stats:
                    all_stats.append(stats)

            if all_stats:
                agg_total_blocks = sum(stat["total_blocks"] for stat in all_stats)
                agg_total_transactions = sum(stat["total_transactions"] for stat in all_stats)
                agg_total_amount_sent = sum(stat["total_amount_sent"] for stat in all_stats)
                agg_total_fees_collected = sum(stat["total_fees_collected"] for stat in all_stats)

                combined_transactions = []
                for stat in all_stats:
                    combined_transactions.extend(stat["last_transactions"])
                last_five_tx = combined_transactions[-5:] if len(combined_transactions) >= 5 else combined_transactions

                aggregated_stats = {
                    "total_known_nodes": len(known_nodes),
                    "aggregated_total_blocks": agg_total_blocks,
                    "aggregated_total_transactions": agg_total_transactions,
                    "aggregated_total_amount_sent": agg_total_amount_sent,
                    "aggregated_total_fees_collected": agg_total_fees_collected,
                    "last_five_transactions": last_five_tx
                }

                print("\n==== 🛠 Aggregated Block Explorer Stats ====")
                print(json.dumps(aggregated_stats, indent=4))
                print("===========================================\n")
            else:
                print("❌ Could not fetch stats from any node.")

            time.sleep(10)  # Update stats every 10 seconds

    except KeyboardInterrupt:
        print("\n🛑 Block explorer terminated by user.")
