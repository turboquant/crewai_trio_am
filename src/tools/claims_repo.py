"""
Claims Repository Tool - CRUD operations for customer claims data
Manages customer claims, reconciliation status, and claim verification
"""

import pandas as pd
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from crewai.tools import tool
import json
from datetime import datetime

# Get project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
CLAIMS_FILE = PROJECT_ROOT / "claims" / "claims.csv"
AUDIT_DB = PROJECT_ROOT / "audit.db"

def _ensure_audit_db():
    """Ensure audit database exists with claims tracking table."""
    con = sqlite3.connect(AUDIT_DB)
    con.execute("""
        CREATE TABLE IF NOT EXISTS claims_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            claim_id TEXT,
            action TEXT,
            old_status TEXT,
            new_status TEXT,
            timestamp TEXT,
            notes TEXT
        )
    """)
    con.commit()
    con.close()

def _log_claim_action(claim_id: str, action: str, old_status: str = None, new_status: str = None, notes: str = None):
    """Log claim actions to audit database."""
    try:
        _ensure_audit_db()
        con = sqlite3.connect(AUDIT_DB)
        timestamp = datetime.now().isoformat()
        con.execute("""
            INSERT INTO claims_audit (claim_id, action, old_status, new_status, timestamp, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (claim_id, action, old_status, new_status, timestamp, notes))
        con.commit()
        con.close()
    except Exception as e:
        print(f"Warning: Could not log claim action: {e}")

@tool("list_open_claims")
def list_open_claims(customer_id: str = None, asset: str = None) -> str:
    """
    List all unreconciled claims, optionally filtered by customer or asset.
    
    Args:
        customer_id: Filter by specific customer ID (optional)
        asset: Filter by specific asset (optional)
    
    Returns:
        JSON string with open claims data
    """
    try:
        if not CLAIMS_FILE.exists():
            return "Claims file not found"
        
        df = pd.read_csv(CLAIMS_FILE)
        
        # Filter to unreconciled claims
        open_claims = df[df["status"] == "unreconciled"].copy()
        
        # Apply additional filters if provided
        if customer_id:
            open_claims = open_claims[open_claims["customer_id"] == customer_id]
        
        if asset:
            open_claims = open_claims[open_claims["asserted_asset"] == asset]
        
        if open_claims.empty:
            filter_desc = ""
            if customer_id and asset:
                filter_desc = f" for customer {customer_id} and asset {asset}"
            elif customer_id:
                filter_desc = f" for customer {customer_id}"
            elif asset:
                filter_desc = f" for asset {asset}"
            
            return f"No open claims found{filter_desc}"
        
        result = {
            "total_open_claims": len(open_claims),
            "unique_customers": open_claims["customer_id"].nunique(),
            "assets_involved": open_claims["asserted_asset"].unique().tolist(),
            "claims": open_claims.to_dict('records')
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error listing open claims: {str(e)}"

@tool("get_claim_details")
def get_claim_details(claim_id: str) -> str:
    """
    Get detailed information about a specific claim.
    
    Args:
        claim_id: Claim ID to query (e.g., 'CLM-1001')
    
    Returns:
        JSON string with claim details and related information
    """
    try:
        if not CLAIMS_FILE.exists():
            return "Claims file not found"
        
        df = pd.read_csv(CLAIMS_FILE)
        claim = df[df["claim_id"] == claim_id]
        
        if claim.empty:
            return f"Claim {claim_id} not found"
        
        claim_data = claim.iloc[0].to_dict()
        
        # Get audit history for this claim
        try:
            con = sqlite3.connect(AUDIT_DB)
            audit_query = """
                SELECT action, old_status, new_status, timestamp, notes
                FROM claims_audit 
                WHERE claim_id = ?
                ORDER BY timestamp DESC
            """
            audit_df = pd.read_sql_query(audit_query, con, params=[claim_id])
            con.close()
            audit_history = audit_df.to_dict('records') if not audit_df.empty else []
        except:
            audit_history = []
        
        # Get other claims from same customer
        customer_id = claim_data["customer_id"]
        other_claims = df[
            (df["customer_id"] == customer_id) & 
            (df["claim_id"] != claim_id)
        ].to_dict('records')
        
        result = {
            "claim_details": claim_data,
            "audit_history": audit_history,
            "other_claims_same_customer": other_claims
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error getting claim details: {str(e)}"

@tool("update_claim_status")
def update_claim_status(claim_id: str, new_status: str, notes: str = None) -> str:
    """
    Update the status of a claim with audit logging.
    
    Args:
        claim_id: Claim ID to update
        new_status: New status (e.g., 'reconciled', 'disputed', 'approved')
        notes: Optional notes about the status change
    
    Returns:
        Confirmation message with update details
    """
    try:
        if not CLAIMS_FILE.exists():
            return "Claims file not found"
        
        df = pd.read_csv(CLAIMS_FILE)
        claim_mask = df["claim_id"] == claim_id
        
        if not claim_mask.any():
            return f"Claim {claim_id} not found"
        
        # Get old status for audit
        old_status = df.loc[claim_mask, "status"].iloc[0]
        
        # Update status
        df.loc[claim_mask, "status"] = new_status
        
        # Save updated claims file
        df.to_csv(CLAIMS_FILE, index=False)
        
        # Log the action
        _log_claim_action(claim_id, "status_update", old_status, new_status, notes)
        
        result = {
            "claim_id": claim_id,
            "old_status": old_status,
            "new_status": new_status,
            "notes": notes,
            "timestamp": datetime.now().isoformat(),
            "success": True
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error updating claim status: {str(e)}"

@tool("claims_by_customer")
def claims_by_customer(customer_id: str) -> str:
    """
    Get all claims for a specific customer with summary statistics.
    
    Args:
        customer_id: Customer ID to query (e.g., 'C123')
    
    Returns:
        JSON string with customer's claims and summary
    """
    try:
        if not CLAIMS_FILE.exists():
            return "Claims file not found"
        
        df = pd.read_csv(CLAIMS_FILE)
        customer_claims = df[df["customer_id"] == customer_id]
        
        if customer_claims.empty:
            return f"No claims found for customer {customer_id}"
        
        # Calculate summary statistics
        total_claimed_by_asset = customer_claims.groupby("asserted_asset")["asserted_amount"].sum().to_dict()
        status_counts = customer_claims["status"].value_counts().to_dict()
        priority_counts = customer_claims["priority"].value_counts().to_dict()
        
        result = {
            "customer_id": customer_id,
            "total_claims": len(customer_claims),
            "total_claimed_by_asset": total_claimed_by_asset,
            "status_breakdown": status_counts,
            "priority_breakdown": priority_counts,
            "claims": customer_claims.to_dict('records')
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error getting claims for customer: {str(e)}"

@tool("claims_reconciliation_summary")
def claims_reconciliation_summary() -> str:
    """
    Get overall reconciliation summary across all claims.
    
    Returns:
        JSON string with reconciliation statistics and progress
    """
    try:
        if not CLAIMS_FILE.exists():
            return "Claims file not found"
        
        df = pd.read_csv(CLAIMS_FILE)
        
        # Overall statistics
        total_claims = len(df)
        status_counts = df["status"].value_counts().to_dict()
        priority_counts = df["priority"].value_counts().to_dict()
        
        # Asset breakdown
        asset_summary = df.groupby("asserted_asset").agg({
            "asserted_amount": ["sum", "count"],
            "status": lambda x: (x == "unreconciled").sum()
        }).round(6)
        
        # Flatten column names
        asset_summary.columns = ["total_amount", "claim_count", "unreconciled_count"]
        asset_breakdown = asset_summary.to_dict('index')
        
        # Customer breakdown
        customer_summary = df.groupby("customer_id").agg({
            "claim_id": "count",
            "status": lambda x: (x == "unreconciled").sum()
        })
        customer_summary.columns = ["total_claims", "unreconciled_claims"]
        customer_breakdown = customer_summary.to_dict('index')
        
        # Get recent audit activity
        try:
            con = sqlite3.connect(AUDIT_DB)
            recent_activity = pd.read_sql_query("""
                SELECT claim_id, action, old_status, new_status, timestamp
                FROM claims_audit 
                ORDER BY timestamp DESC 
                LIMIT 10
            """, con)
            con.close()
            recent_activity_list = recent_activity.to_dict('records') if not recent_activity.empty else []
        except:
            recent_activity_list = []
        
        result = {
            "overall_stats": {
                "total_claims": total_claims,
                "status_breakdown": status_counts,
                "priority_breakdown": priority_counts,
                "reconciliation_rate": round((status_counts.get("reconciled", 0) / total_claims) * 100, 2) if total_claims > 0 else 0
            },
            "asset_breakdown": asset_breakdown,
            "customer_breakdown": customer_breakdown,
            "recent_activity": recent_activity_list
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error generating reconciliation summary: {str(e)}"

@tool("search_claims")
def search_claims(search_term: str) -> str:
    """
    Search claims by notes content or other text fields.
    
    Args:
        search_term: Text to search for in claim notes and descriptions
    
    Returns:
        JSON string with matching claims
    """
    try:
        if not CLAIMS_FILE.exists():
            return "Claims file not found"
        
        df = pd.read_csv(CLAIMS_FILE)
        
        # Search in notes field (case-insensitive)
        mask = df["notes"].str.contains(search_term, case=False, na=False)
        
        matching_claims = df[mask]
        
        if matching_claims.empty:
            return f"No claims found matching '{search_term}'"
        
        result = {
            "search_term": search_term,
            "matches_found": len(matching_claims),
            "matching_claims": matching_claims.to_dict('records')
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error searching claims: {str(e)}"

# Utility function for direct pandas access (not a CrewAI tool)
def get_claims_dataframe() -> pd.DataFrame:
    """
    Get claims dataframe for internal use by other tools.
    
    Returns:
        DataFrame with all claims data
    """
    try:
        if not CLAIMS_FILE.exists():
            return pd.DataFrame()
        return pd.read_csv(CLAIMS_FILE)
    except Exception as e:
        print(f"Error loading claims data: {e}")
        return pd.DataFrame()

if __name__ == "__main__":
    # Test the tools
    print("Testing Claims Repository Tools:")
    
    print("\n1. List open claims:")
    print(list_open_claims())
    
    print("\n2. Claims for customer C123:")
    print(claims_by_customer("C123"))
    
    print("\n3. Get specific claim details:")
    print(get_claim_details("CLM-1001"))
    
    print("\n4. Reconciliation summary:")
    print(claims_reconciliation_summary())


