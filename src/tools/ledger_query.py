"""
Ledger Query Tool - DuckDB-based analysis of internal exchange ledgers
Provides balance calculations and transaction history for customer accounts
"""

from pathlib import Path
import duckdb
import pandas as pd
from typing import Optional, Dict, Any
import os
from crewai.tools import tool

# Get the project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
LEDGER_DIR = PROJECT_ROOT / "ledgers"

def _get_connection():
    """Create a DuckDB connection with ledger views registered."""
    con = duckdb.connect()
    
    # Register CSV files as DuckDB views
    spot_path = LEDGER_DIR / "spot_ledger.csv"
    margin_path = LEDGER_DIR / "margin_ledger.csv"
    
    if spot_path.exists():
        con.execute(f"CREATE VIEW spot AS SELECT * FROM read_csv_auto('{spot_path}');")
    
    if margin_path.exists():
        con.execute(f"CREATE VIEW margin AS SELECT * FROM read_csv_auto('{margin_path}');")
    
    return con

@tool("ledger_balance")
def ledger_balance(customer_id: str, asset: str = None) -> str:
    """
    Calculate current balance for a customer in specific asset or all assets.
    
    Args:
        customer_id: Customer ID to query (e.g., 'C123')
        asset: Asset to query (e.g., 'BTC', 'USD'). If None, returns all assets.
    
    Returns:
        JSON string with balance information including transaction count and last activity
    """
    try:
        con = _get_connection()
        
        if asset:
            # Query specific asset balance
            query = """
                WITH all_txns AS (
                    SELECT timestamp, customer_id, asset, 
                           amount * (CASE WHEN side='credit' THEN 1 ELSE -1 END) as delta,
                           tx_id
                    FROM spot 
                    WHERE customer_id = ? AND asset = ?
                ),
                balance_calc AS (
                    SELECT asset, 
                           SUM(delta) as balance,
                           COUNT(*) as transaction_count,
                           MAX(timestamp) as last_activity
                    FROM all_txns 
                    GROUP BY asset
                )
                SELECT * FROM balance_calc;
            """
            result = con.execute(query, [customer_id, asset]).df()
        else:
            # Query all asset balances
            query = """
                WITH all_txns AS (
                    SELECT timestamp, customer_id, asset,
                           amount * (CASE WHEN side='credit' THEN 1 ELSE -1 END) as delta,
                           tx_id
                    FROM spot 
                    WHERE customer_id = ?
                ),
                balance_calc AS (
                    SELECT asset,
                           SUM(delta) as balance,
                           COUNT(*) as transaction_count,
                           MAX(timestamp) as last_activity
                    FROM all_txns 
                    GROUP BY asset
                )
                SELECT * FROM balance_calc ORDER BY asset;
            """
            result = con.execute(query, [customer_id]).df()
        
        con.close()
        
        if result.empty:
            return f"No balance found for customer {customer_id}" + (f" in asset {asset}" if asset else "")
        
        return result.to_json(orient='records', indent=2)
        
    except Exception as e:
        return f"Error querying ledger balance: {str(e)}"

@tool("ledger_movements") 
def ledger_movements(customer_id: str, limit: int = 50) -> str:
    """
    Get transaction history for a customer, ordered by timestamp.
    
    Args:
        customer_id: Customer ID to query (e.g., 'C123')
        limit: Maximum number of transactions to return (default 50)
    
    Returns:
        JSON string with transaction history including running balances
    """
    try:
        con = _get_connection()
        
        query = """
            WITH txn_data AS (
                SELECT timestamp, customer_id, asset, amount, side, tx_id, notes,
                       amount * (CASE WHEN side='credit' THEN 1 ELSE -1 END) as delta
                FROM spot 
                WHERE customer_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ),
            with_running_balance AS (
                SELECT *,
                       SUM(delta) OVER (
                           PARTITION BY asset 
                           ORDER BY timestamp DESC 
                           ROWS UNBOUNDED PRECEDING
                       ) as running_balance
                FROM txn_data
                ORDER BY timestamp DESC
            )
            SELECT * FROM with_running_balance;
        """
        
        result = con.execute(query, [customer_id, limit]).df()
        con.close()
        
        if result.empty:
            return f"No transactions found for customer {customer_id}"
        
        return result.to_json(orient='records', indent=2)
        
    except Exception as e:
        return f"Error querying ledger movements: {str(e)}"

@tool("ledger_asset_summary")
def ledger_asset_summary(asset: str = None) -> str:
    """
    Get asset summary across all customers - useful for understanding total exposure.
    
    Args:
        asset: Specific asset to analyze (e.g., 'BTC'). If None, returns all assets.
    
    Returns:
        JSON string with asset summary including total balances and customer count
    """
    try:
        con = _get_connection()
        
        if asset:
            query = """
                WITH all_txns AS (
                    SELECT customer_id, asset,
                           SUM(amount * (CASE WHEN side='credit' THEN 1 ELSE -1 END)) as customer_balance
                    FROM spot 
                    WHERE asset = ?
                    GROUP BY customer_id, asset
                )
                SELECT asset,
                       COUNT(*) as customer_count,
                       SUM(customer_balance) as total_balance,
                       MIN(customer_balance) as min_balance,
                       MAX(customer_balance) as max_balance,
                       AVG(customer_balance) as avg_balance
                FROM all_txns 
                WHERE customer_balance != 0
                GROUP BY asset;
            """
            result = con.execute(query, [asset]).df()
        else:
            query = """
                WITH all_txns AS (
                    SELECT customer_id, asset,
                           SUM(amount * (CASE WHEN side='credit' THEN 1 ELSE -1 END)) as customer_balance
                    FROM spot 
                    GROUP BY customer_id, asset
                )
                SELECT asset,
                       COUNT(*) as customer_count, 
                       SUM(customer_balance) as total_balance,
                       MIN(customer_balance) as min_balance,
                       MAX(customer_balance) as max_balance,
                       AVG(customer_balance) as avg_balance
                FROM all_txns 
                WHERE customer_balance != 0
                GROUP BY asset
                ORDER BY asset;
            """
            result = con.execute(query).df()
        
        con.close()
        
        if result.empty:
            return f"No data found" + (f" for asset {asset}" if asset else "")
        
        return result.to_json(orient='records', indent=2)
        
    except Exception as e:
        return f"Error querying asset summary: {str(e)}"

@tool("ledger_withdrawal_history")
def ledger_withdrawal_history(customer_id: str = None) -> str:
    """
    Get withdrawal transaction history - critical for asset tracing.
    
    Args:
        customer_id: Specific customer ID to query. If None, returns all withdrawals.
    
    Returns:
        JSON string with withdrawal history including destination addresses from notes
    """
    try:
        con = _get_connection()
        
        if customer_id:
            query = """
                SELECT timestamp, customer_id, asset, amount, tx_id, notes
                FROM spot 
                WHERE side = 'debit' AND customer_id = ?
                ORDER BY timestamp DESC;
            """
            result = con.execute(query, [customer_id]).df()
        else:
            query = """
                SELECT timestamp, customer_id, asset, amount, tx_id, notes
                FROM spot 
                WHERE side = 'debit'
                ORDER BY timestamp DESC;
            """
            result = con.execute(query).df()
        
        con.close()
        
        if result.empty:
            return f"No withdrawals found" + (f" for customer {customer_id}" if customer_id else "")
        
        return result.to_json(orient='records', indent=2)
        
    except Exception as e:
        return f"Error querying withdrawal history: {str(e)}"

# Utility function for direct pandas access (not a CrewAI tool)
def get_customer_transactions(customer_id: str) -> pd.DataFrame:
    """
    Direct pandas access to customer transactions - for internal use by other tools.
    
    Args:
        customer_id: Customer ID to query
        
    Returns:
        DataFrame with all transactions for the customer
    """
    try:
        con = _get_connection()
        query = """
            SELECT timestamp, customer_id, asset, amount, side, tx_id, notes
            FROM spot 
            WHERE customer_id = ?
            ORDER BY timestamp;
        """
        result = con.execute(query, [customer_id]).df()
        con.close()
        return result
    except Exception as e:
        print(f"Error in get_customer_transactions: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Test the tools
    print("Testing Ledger Query Tools:")
    print("\n1. Balance for C123:")
    print(ledger_balance("C123"))
    
    print("\n2. Movements for C123:")
    print(ledger_movements("C123", 5))
    
    print("\n3. BTC Asset Summary:")
    print(ledger_asset_summary("BTC"))
    
    print("\n4. Withdrawal History:")
    print(ledger_withdrawal_history("C123"))


