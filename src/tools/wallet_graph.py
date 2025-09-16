"""
Wallet Graph Tool - NetworkX-based blockchain transaction analysis
Provides path finding, flow analysis, and graph traversal for cryptocurrency transactions
"""

import pandas as pd
import networkx as nx
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from crewai.tools import tool
import json

# Get project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
TX_FILE = PROJECT_ROOT / "mock_chain" / "tx.csv"

def _build_transaction_graph() -> nx.DiGraph:
    """
    Build a directed graph from blockchain transaction data.
    
    Returns:
        NetworkX DiGraph with transaction flows
    """
    if not TX_FILE.exists():
        print(f"Warning: Transaction file not found at {TX_FILE}")
        return nx.DiGraph()
    
    df = pd.read_csv(TX_FILE)
    g = nx.DiGraph()
    
    # Add edges with transaction data as attributes
    for _, row in df.iterrows():
        g.add_edge(
            row["from"], 
            row["to"],
            asset=row["asset"],
            amount=float(row["amount"]),
            fee=float(row["fee"]),
            tx_hash=row["tx_hash"],
            timestamp=row["timestamp"],
            notes=row["notes"]
        )
    
    return g

@tool("wallet_shortest_path")
def wallet_shortest_path(source: str, target: str) -> str:
    """
    Find the shortest path between two wallet addresses.
    
    Args:
        source: Source wallet address
        target: Target wallet address
    
    Returns:
        JSON string with path information including intermediate hops and transaction details
    """
    try:
        g = _build_transaction_graph()
        
        if source not in g.nodes():
            return f"Source wallet {source} not found in transaction graph"
        
        if target not in g.nodes():
            return f"Target wallet {target} not found in transaction graph"
        
        try:
            path = nx.shortest_path(g, source, target)
            
            # Get transaction details for each hop
            path_details = []
            total_amount = 0
            total_fees = 0
            
            for i in range(len(path) - 1):
                from_addr = path[i]
                to_addr = path[i + 1]
                edge_data = g[from_addr][to_addr]
                
                path_details.append({
                    "hop": i + 1,
                    "from": from_addr,
                    "to": to_addr,
                    "asset": edge_data["asset"],
                    "amount": edge_data["amount"],
                    "fee": edge_data["fee"],
                    "tx_hash": edge_data["tx_hash"],
                    "timestamp": edge_data["timestamp"],
                    "notes": edge_data["notes"]
                })
                
                total_amount = edge_data["amount"]  # Amount after fees
                total_fees += edge_data["fee"]
            
            result = {
                "source": source,
                "target": target,
                "path_length": len(path),
                "path_nodes": path,
                "total_hops": len(path_details),
                "total_fees": total_fees,
                "final_amount": total_amount,
                "path_details": path_details
            }
            
            return json.dumps(result, indent=2)
            
        except nx.NetworkXNoPath:
            return f"No path found between {source} and {target}"
    
    except Exception as e:
        return f"Error finding shortest path: {str(e)}"

@tool("wallet_outward_hops") 
def wallet_outward_hops(start_wallet: str, max_depth: int = 3) -> str:
    """
    Find all outward transaction hops from a starting wallet up to max_depth.
    
    Args:
        start_wallet: Starting wallet address
        max_depth: Maximum depth to traverse (default 3)
    
    Returns:
        JSON string with all reachable addresses and transaction paths
    """
    try:
        g = _build_transaction_graph()
        
        if start_wallet not in g.nodes():
            return f"Wallet {start_wallet} not found in transaction graph"
        
        # BFS traversal to find all reachable nodes within max_depth
        visited = {start_wallet: 0}  # wallet -> depth
        queue = [(start_wallet, 0)]
        edges_found = []
        
        while queue:
            current_wallet, depth = queue.pop(0)
            
            if depth >= max_depth:
                continue
            
            # Explore all outgoing edges
            for neighbor in g.successors(current_wallet):
                edge_data = g[current_wallet][neighbor]
                
                # Record this edge
                edges_found.append({
                    "from": current_wallet,
                    "to": neighbor,
                    "depth": depth + 1,
                    "asset": edge_data["asset"],
                    "amount": edge_data["amount"],
                    "fee": edge_data["fee"],
                    "tx_hash": edge_data["tx_hash"],
                    "timestamp": edge_data["timestamp"],
                    "notes": edge_data["notes"]
                })
                
                # Add to queue if not visited or found at greater depth
                if neighbor not in visited or visited[neighbor] > depth + 1:
                    visited[neighbor] = depth + 1
                    queue.append((neighbor, depth + 1))
        
        # Organize results by depth
        by_depth = {}
        for edge in edges_found:
            depth = edge["depth"]
            if depth not in by_depth:
                by_depth[depth] = []
            by_depth[depth].append(edge)
        
        # Get unique wallets at each depth
        wallets_by_depth = {}
        for depth in by_depth:
            wallets_by_depth[depth] = list(set([edge["to"] for edge in by_depth[depth]]))
        
        result = {
            "start_wallet": start_wallet,
            "max_depth": max_depth,
            "total_edges": len(edges_found),
            "total_wallets_reached": len(visited) - 1,  # Exclude start wallet
            "wallets_by_depth": wallets_by_depth,
            "edges_by_depth": by_depth,
            "all_reachable_wallets": list(visited.keys())
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error finding outward hops: {str(e)}"

@tool("wallet_inward_flows")
def wallet_inward_flows(target_wallet: str, max_depth: int = 3) -> str:
    """
    Find all inward transaction flows to a target wallet up to max_depth.
    
    Args:
        target_wallet: Target wallet address
        max_depth: Maximum depth to traverse backwards (default 3)
    
    Returns:
        JSON string with all source addresses and transaction paths leading to target
    """
    try:
        g = _build_transaction_graph()
        
        if target_wallet not in g.nodes():
            return f"Wallet {target_wallet} not found in transaction graph"
        
        # Reverse BFS to find all paths leading to target
        visited = {target_wallet: 0}
        queue = [(target_wallet, 0)]
        edges_found = []
        
        while queue:
            current_wallet, depth = queue.pop(0)
            
            if depth >= max_depth:
                continue
            
            # Explore all incoming edges
            for predecessor in g.predecessors(current_wallet):
                edge_data = g[predecessor][current_wallet]
                
                # Record this edge
                edges_found.append({
                    "from": predecessor,
                    "to": current_wallet,
                    "depth": depth + 1,
                    "asset": edge_data["asset"],
                    "amount": edge_data["amount"],
                    "fee": edge_data["fee"],
                    "tx_hash": edge_data["tx_hash"],
                    "timestamp": edge_data["timestamp"],
                    "notes": edge_data["notes"]
                })
                
                # Add to queue if not visited
                if predecessor not in visited or visited[predecessor] > depth + 1:
                    visited[predecessor] = depth + 1
                    queue.append((predecessor, depth + 1))
        
        # Organize results by depth
        by_depth = {}
        for edge in edges_found:
            depth = edge["depth"]
            if depth not in by_depth:
                by_depth[depth] = []
            by_depth[depth].append(edge)
        
        result = {
            "target_wallet": target_wallet,
            "max_depth": max_depth,
            "total_inbound_edges": len(edges_found),
            "total_source_wallets": len(visited) - 1,
            "edges_by_depth": by_depth,
            "all_source_wallets": [w for w in visited.keys() if w != target_wallet]
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error finding inward flows: {str(e)}"

@tool("wallet_transaction_summary")
def wallet_transaction_summary(wallet_address: str) -> str:
    """
    Get transaction summary for a specific wallet address.
    
    Args:
        wallet_address: Wallet address to analyze
    
    Returns:
        JSON string with transaction statistics and connected wallets
    """
    try:
        g = _build_transaction_graph()
        
        if wallet_address not in g.nodes():
            return f"Wallet {wallet_address} not found in transaction graph"
        
        # Get all edges involving this wallet
        outbound_edges = []
        inbound_edges = []
        
        # Outbound transactions
        for successor in g.successors(wallet_address):
            edge_data = g[wallet_address][successor]
            outbound_edges.append({
                "to": successor,
                "asset": edge_data["asset"],
                "amount": edge_data["amount"],
                "fee": edge_data["fee"],
                "tx_hash": edge_data["tx_hash"],
                "timestamp": edge_data["timestamp"],
                "notes": edge_data["notes"]
            })
        
        # Inbound transactions
        for predecessor in g.predecessors(wallet_address):
            edge_data = g[predecessor][wallet_address]
            inbound_edges.append({
                "from": predecessor,
                "asset": edge_data["asset"],
                "amount": edge_data["amount"],
                "fee": edge_data["fee"],
                "tx_hash": edge_data["tx_hash"],
                "timestamp": edge_data["timestamp"],
                "notes": edge_data["notes"]
            })
        
        # Calculate totals by asset
        outbound_totals = {}
        inbound_totals = {}
        
        for edge in outbound_edges:
            asset = edge["asset"]
            outbound_totals[asset] = outbound_totals.get(asset, 0) + edge["amount"]
        
        for edge in inbound_edges:
            asset = edge["asset"]
            inbound_totals[asset] = inbound_totals.get(asset, 0) + edge["amount"]
        
        result = {
            "wallet_address": wallet_address,
            "total_outbound_transactions": len(outbound_edges),
            "total_inbound_transactions": len(inbound_edges),
            "unique_outbound_wallets": len(set([e["to"] for e in outbound_edges])),
            "unique_inbound_wallets": len(set([e["from"] for e in inbound_edges])),
            "outbound_totals_by_asset": outbound_totals,
            "inbound_totals_by_asset": inbound_totals,
            "outbound_transactions": outbound_edges,
            "inbound_transactions": inbound_edges
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error getting wallet summary: {str(e)}"

# Utility function for direct graph access (not a CrewAI tool)
def get_transaction_graph() -> nx.DiGraph:
    """
    Get the transaction graph for internal use by other tools.
    
    Returns:
        NetworkX DiGraph with transaction data
    """
    return _build_transaction_graph()

if __name__ == "__main__":
    # Test the tools
    print("Testing Wallet Graph Tools:")
    
    print("\n1. Shortest path from exch_hot_1 to 0xprime:")
    print(wallet_shortest_path("exch_hot_1", "0xprime"))
    
    print("\n2. Outward hops from 0xabc (depth 2):")
    print(wallet_outward_hops("0xabc", 2))
    
    print("\n3. Transaction summary for 0xabc:")
    print(wallet_transaction_summary("0xabc"))
    
    print("\n4. Inward flows to 0xprime:")
    print(wallet_inward_flows("0xprime", 3))


