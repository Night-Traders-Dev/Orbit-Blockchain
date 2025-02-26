import requests
import json
import sys
import time

def view_node_stats(node_url):
    """ Fetch blockchain data from a node and calculate relevant stats. """
    url = f"{node_url}/blockchain"
    try:
        response = requests.get(url, timeout=5)
        blockchain = response.json()

        if not isinstance(blockchain, list):
            print(f"[{node_url}] Invalid blockchain format.")
            return None
    except (requests.RequestException, json.JSONDecodeError) as e:
        print(f"Error fetching blockchain from {node_url}: {e}")
        return None

    total_blocks = len(blockchain)
    total_transactions = 0
    total_amount_sent = 0.0
    total_fees_collected = 0.0
    last_transactions = []

    # Process each block, skipping the genesis block (index 0)
    for block in blockchain:
        if block.get("index") == 0:
            continue  # Skip genesis block

        tx_data = block.get("data", [])
        if not isinstance(tx_data, list):
            continue  # Invalid transaction format

        for tx in tx_data:
            if not isinstance(tx, dict):
                continue  # Skip malformed transactions
            
            sender = tx.get("sender", "Unknown")
            receiver = tx.get("receiver", "Unknown")
            amount = float(tx.get("amount", 0))
            fee = float(tx.get("fee", 0))
            tx_id = tx.get("tx_id", "N/A")

            total_transactions += 1
            total_amount_sent += amount
            total_fees_collected += fee

            last_transactions.append(f"{sender} → {receiver} | {amount} units | Fee: {fee} | TX ID: {tx_id}")

    # Limit to last 5 transactions for display
    last_five_tx = last_transactions[-5:] if len(last_transactions) >= 5 else last_transactions

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
    node_urls = [url.strip() for url in nodes_arg.split(",")]

    print("Starting aggregated Block Explorer (updating stats every 10 seconds)...")
    try:
        while True:
            all_stats = []
            for node_url in node_urls:
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
