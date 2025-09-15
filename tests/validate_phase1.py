#!/usr/bin/env python3
"""
Phase 1 Validation Script
Verifies that all core infrastructure and mock data files are properly set up.
"""

import pandas as pd
import os
import sys
from pathlib import Path

def validate_csv_files():
    """Validate that all CSV files can be loaded and have expected structure."""
    print("Validating CSV files...")
    
    # Test ledger files
    try:
        spot_df = pd.read_csv("ledgers/spot_ledger.csv")
        assert len(spot_df) > 0, "Spot ledger should have data"
        expected_cols = ["tx_id", "timestamp", "customer_id", "asset", "amount", "side", "notes"]
        assert all(col in spot_df.columns for col in expected_cols), "Spot ledger missing columns"
        print("PASS: Spot ledger file valid")
        
        margin_df = pd.read_csv("ledgers/margin_ledger.csv") 
        assert len(margin_df) > 0, "Margin ledger should have data"
        print("PASS: Margin ledger file valid")
    except Exception as e:
        print(f"FAIL: Ledger validation failed: {e}")
        return False
    
    # Test blockchain data
    try:
        chain_df = pd.read_csv("mock_chain/tx.csv")
        assert len(chain_df) > 0, "Chain data should have transactions"
        expected_cols = ["tx_hash", "timestamp", "from", "to", "asset", "amount", "fee", "notes"]
        assert all(col in chain_df.columns for col in expected_cols), "Chain data missing columns"
        print("PASS: Blockchain transaction file valid")
    except Exception as e:
        print(f"FAIL: Blockchain validation failed: {e}")
        return False
    
    # Test claims data
    try:
        claims_df = pd.read_csv("claims/claims.csv")
        assert len(claims_df) > 0, "Claims should have data"
        expected_cols = ["claim_id", "customer_id", "asserted_asset", "asserted_amount", "priority", "status", "notes"]
        assert all(col in claims_df.columns for col in expected_cols), "Claims data missing columns"
        print("PASS: Claims file valid")
    except Exception as e:
        print(f"FAIL: Claims validation failed: {e}")
        return False
    
    # Test entity mapping
    try:
        entities_df = pd.read_csv("entities/xref_wallets.csv")
        assert len(entities_df) > 0, "Entity mapping should have data"
        expected_cols = ["wallet", "entity", "type", "confidence", "source"]
        assert all(col in entities_df.columns for col in expected_cols), "Entity mapping missing columns"
        print("PASS: Entity cross-reference file valid")
    except Exception as e:
        print(f"FAIL: Entity validation failed: {e}")
        return False
    
    return True

def validate_project_structure():
    """Verify all required directories and key files exist."""
    print("Validating project structure...")
    
    required_dirs = [
        "config", "src", "src/tools", "knowledge", "ledgers", 
        "mock_chain", "claims", "entities", "policies", 
        "catalogs", "tests"
    ]
    
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            print(f"FAIL: Missing directory: {dir_path}")
            return False
    
    print("PASS: All required directories exist")
    
    required_files = [
        "requirements.txt", "docker-compose.yml", "Dockerfile",
        "env.example", "README.md"
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"FAIL: Missing file: {file_path}")
            return False
    
    print("PASS: All required files exist")
    return True

def validate_data_consistency():
    """Check for basic data consistency between files."""
    print("Validating data consistency...")
    
    try:
        # Load data
        spot_df = pd.read_csv("ledgers/spot_ledger.csv")
        chain_df = pd.read_csv("mock_chain/tx.csv")
        claims_df = pd.read_csv("claims/claims.csv")
        entities_df = pd.read_csv("entities/xref_wallets.csv")
        
        # Check customer consistency
        ledger_customers = set(spot_df['customer_id'].unique())
        claims_customers = set(claims_df['customer_id'].unique())
        
        if not ledger_customers.intersection(claims_customers):
            print("WARNING: No customer overlap between ledgers and claims")
        else:
            print("PASS: Customer data consistent between ledgers and claims")
        
        # Check wallet consistency  
        chain_wallets = set(chain_df['from'].tolist() + chain_df['to'].tolist())
        entity_wallets = set(entities_df['wallet'].unique())
        
        if entity_wallets.issubset(chain_wallets):
            print("PASS: All entity wallets appear in blockchain data")
        else:
            missing = entity_wallets - chain_wallets
            print(f"WARNING: Entity wallets not in chain data: {missing}")
        
        return True
        
    except Exception as e:
        print(f"FAIL: Data consistency check failed: {e}")
        return False

def main():
    """Run all Phase 1 validation checks."""
    print("CrewAI Compliance Experts - Phase 1 Validation")
    print("="*50)
    
    # Change to project root if running from tests directory
    if Path.cwd().name == 'tests':
        os.chdir('..')
    
    all_passed = True
    
    # Run validation checks
    if not validate_project_structure():
        all_passed = False
    
    if not validate_csv_files():
        all_passed = False
    
    if not validate_data_consistency():
        all_passed = False
    
    print("="*50)
    if all_passed:
        print("SUCCESS: Phase 1 validation PASSED! Ready for Phase 2.")
        return 0
    else:
        print("ERROR: Phase 1 validation FAILED. Please fix issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
