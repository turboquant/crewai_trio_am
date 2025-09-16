"""
Cross-Reference Tool - Wallet-to-entity mapping and identity resolution
Provides entity resolution, confidence scoring, and relationship mapping for blockchain addresses
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Any, Optional, List
from crewai.tools import tool
import json
from datetime import datetime

# Get project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
XREF_FILE = PROJECT_ROOT / "entities" / "xref_wallets.csv"

@tool("resolve_wallet")
def resolve_wallet(wallet_address: str) -> str:
    """
    Resolve a wallet address to its associated entity information.
    
    Args:
        wallet_address: Wallet address to resolve (e.g., '0xabc')
    
    Returns:
        JSON string with entity information including confidence score and source
    """
    try:
        if not XREF_FILE.exists():
            return "Cross-reference file not found"
        
        df = pd.read_csv(XREF_FILE)
        match = df[df["wallet"] == wallet_address]
        
        if match.empty:
            return f"No entity mapping found for wallet {wallet_address}"
        
        # Get the best match (highest confidence if multiple)
        if len(match) > 1:
            match = match.loc[match["confidence"].idxmax()]
        else:
            match = match.iloc[0]
        
        result = {
            "wallet_address": wallet_address,
            "entity": match["entity"],
            "entity_type": match["type"],
            "confidence_score": float(match["confidence"]),
            "source": match["source"],
            "resolution_quality": _get_confidence_level(match["confidence"])
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error resolving wallet: {str(e)}"

@tool("find_entity_wallets")
def find_entity_wallets(entity_name: str) -> str:
    """
    Find all wallet addresses associated with an entity.
    
    Args:
        entity_name: Entity name to search for (partial matches allowed)
    
    Returns:
        JSON string with all associated wallet addresses
    """
    try:
        if not XREF_FILE.exists():
            return "Cross-reference file not found"
        
        df = pd.read_csv(XREF_FILE)
        
        # Search for entity name (case-insensitive partial match)
        matches = df[df["entity"].str.contains(entity_name, case=False, na=False)]
        
        if matches.empty:
            return f"No wallets found for entity '{entity_name}'"
        
        # Group by entity for exact matches
        entity_wallets = {}
        for _, row in matches.iterrows():
            entity = row["entity"]
            if entity not in entity_wallets:
                entity_wallets[entity] = []
            
            entity_wallets[entity].append({
                "wallet": row["wallet"],
                "type": row["type"],
                "confidence": float(row["confidence"]),
                "source": row["source"]
            })
        
        result = {
            "search_term": entity_name,
            "entities_found": len(entity_wallets),
            "total_wallets": len(matches),
            "entity_wallet_mapping": entity_wallets
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error finding entity wallets: {str(e)}"

@tool("get_wallet_type_summary")
def get_wallet_type_summary() -> str:
    """
    Get summary of wallet types and their distribution in the cross-reference data.
    
    Returns:
        JSON string with wallet type statistics and examples
    """
    try:
        if not XREF_FILE.exists():
            return "Cross-reference file not found"
        
        df = pd.read_csv(XREF_FILE)
        
        # Type distribution
        type_counts = df["type"].value_counts().to_dict()
        
        # Average confidence by type
        avg_confidence = df.groupby("type")["confidence"].agg(["mean", "count", "min", "max"]).round(3)
        
        # Examples for each type
        type_examples = {}
        for wallet_type in df["type"].unique():
            type_data = df[df["type"] == wallet_type].head(3)
            type_examples[wallet_type] = type_data[["wallet", "entity", "confidence", "source"]].to_dict('records')
        
        result = {
            "total_mappings": len(df),
            "unique_entities": df["entity"].nunique(),
            "type_distribution": type_counts,
            "confidence_stats_by_type": avg_confidence.to_dict('index'),
            "examples_by_type": type_examples
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error getting wallet type summary: {str(e)}"

@tool("validate_wallet_mapping")
def validate_wallet_mapping(wallet_address: str, expected_entity: str) -> str:
    """
    Validate if a wallet address is correctly mapped to an expected entity.
    
    Args:
        wallet_address: Wallet address to validate
        expected_entity: Expected entity name
    
    Returns:
        JSON string with validation results and confidence assessment
    """
    try:
        if not XREF_FILE.exists():
            return "Cross-reference file not found"
        
        df = pd.read_csv(XREF_FILE)
        match = df[df["wallet"] == wallet_address]
        
        if match.empty:
            result = {
                "wallet_address": wallet_address,
                "expected_entity": expected_entity,
                "validation_status": "NO_MAPPING",
                "confidence": 0.0,
                "message": f"No mapping found for wallet {wallet_address}"
            }
            return json.dumps(result, indent=2)
        
        # Check if expected entity matches
        actual_entity = match.iloc[0]["entity"]
        confidence = float(match.iloc[0]["confidence"])
        source = match.iloc[0]["source"]
        
        if actual_entity.lower() == expected_entity.lower():
            status = "EXACT_MATCH"
            message = f"Wallet correctly mapped to {actual_entity}"
        elif expected_entity.lower() in actual_entity.lower() or actual_entity.lower() in expected_entity.lower():
            status = "PARTIAL_MATCH"
            message = f"Partial match: expected '{expected_entity}', found '{actual_entity}'"
        else:
            status = "MISMATCH"
            message = f"Mismatch: expected '{expected_entity}', but mapped to '{actual_entity}'"
        
        result = {
            "wallet_address": wallet_address,
            "expected_entity": expected_entity,
            "actual_entity": actual_entity,
            "validation_status": status,
            "confidence": confidence,
            "source": source,
            "message": message,
            "quality_assessment": _get_confidence_level(confidence)
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error validating wallet mapping: {str(e)}"

@tool("search_by_confidence")
def search_by_confidence(min_confidence: float = 0.0, max_confidence: float = 1.0) -> str:
    """
    Find wallet mappings within a specific confidence range.
    
    Args:
        min_confidence: Minimum confidence score (0.0 to 1.0)
        max_confidence: Maximum confidence score (0.0 to 1.0)
    
    Returns:
        JSON string with wallet mappings in the specified confidence range
    """
    try:
        if not XREF_FILE.exists():
            return "Cross-reference file not found"
        
        df = pd.read_csv(XREF_FILE)
        
        # Filter by confidence range
        filtered = df[(df["confidence"] >= min_confidence) & (df["confidence"] <= max_confidence)]
        
        if filtered.empty:
            return f"No wallet mappings found with confidence between {min_confidence} and {max_confidence}"
        
        # Sort by confidence (descending)
        filtered = filtered.sort_values("confidence", ascending=False)
        
        # Group by confidence level categories
        confidence_categories = {
            "high_confidence": filtered[filtered["confidence"] >= 0.8],
            "medium_confidence": filtered[(filtered["confidence"] >= 0.5) & (filtered["confidence"] < 0.8)],
            "low_confidence": filtered[filtered["confidence"] < 0.5]
        }
        
        category_counts = {k: len(v) for k, v in confidence_categories.items()}
        
        result = {
            "confidence_range": {"min": min_confidence, "max": max_confidence},
            "total_mappings": len(filtered),
            "confidence_distribution": category_counts,
            "average_confidence": round(filtered["confidence"].mean(), 3),
            "mappings": filtered.to_dict('records')
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error searching by confidence: {str(e)}"

@tool("get_source_analysis")
def get_source_analysis() -> str:
    """
    Analyze the sources of wallet-entity mappings and their reliability.
    
    Returns:
        JSON string with source analysis and reliability metrics
    """
    try:
        if not XREF_FILE.exists():
            return "Cross-reference file not found"
        
        df = pd.read_csv(XREF_FILE)
        
        # Source distribution
        source_counts = df["source"].value_counts().to_dict()
        
        # Average confidence by source
        source_confidence = df.groupby("source")["confidence"].agg(["mean", "count", "min", "max"]).round(3)
        
        # Source reliability ranking
        source_reliability = source_confidence.sort_values("mean", ascending=False)
        
        # Examples for each source type
        source_examples = {}
        for source in df["source"].unique():
            source_data = df[df["source"] == source].head(2)
            source_examples[source] = source_data[["wallet", "entity", "type", "confidence"]].to_dict('records')
        
        result = {
            "total_sources": len(source_counts),
            "source_distribution": source_counts,
            "confidence_by_source": source_confidence.to_dict('index'),
            "source_reliability_ranking": source_reliability.to_dict('index'),
            "source_examples": source_examples,
            "recommendations": _generate_source_recommendations(source_confidence)
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error analyzing sources: {str(e)}"

def _get_confidence_level(confidence: float) -> str:
    """Categorize confidence score into quality levels."""
    if confidence >= 0.9:
        return "very_high"
    elif confidence >= 0.8:
        return "high" 
    elif confidence >= 0.6:
        return "medium"
    elif confidence >= 0.4:
        return "low"
    else:
        return "very_low"

def _generate_source_recommendations(source_stats: pd.DataFrame) -> List[str]:
    """Generate recommendations based on source analysis."""
    recommendations = []
    
    if not source_stats.empty:
        best_source = source_stats.loc[source_stats["mean"].idxmax()]
        worst_source = source_stats.loc[source_stats["mean"].idxmin()]
        
        recommendations.append(f"Most reliable source: '{best_source.name}' (avg confidence: {best_source['mean']:.3f})")
        
        if best_source["mean"] - worst_source["mean"] > 0.3:
            recommendations.append(f"Consider reviewing mappings from '{worst_source.name}' (avg confidence: {worst_source['mean']:.3f})")
        
        low_confidence_sources = source_stats[source_stats["mean"] < 0.6]
        if len(low_confidence_sources) > 0:
            recommendations.append(f"{len(low_confidence_sources)} source(s) have low average confidence - may need verification")
    
    return recommendations

# Utility function for direct pandas access (not a CrewAI tool)
def get_entity_mapping(wallet_address: str) -> Optional[Dict[str, Any]]:
    """
    Get entity mapping for internal use by other tools.
    
    Args:
        wallet_address: Wallet address to resolve
        
    Returns:
        Dictionary with entity information or None if not found
    """
    try:
        if not XREF_FILE.exists():
            return None
        
        df = pd.read_csv(XREF_FILE)
        match = df[df["wallet"] == wallet_address]
        
        if match.empty:
            return None
        
        return match.iloc[0].to_dict()
    except Exception as e:
        print(f"Error in get_entity_mapping: {e}")
        return None

if __name__ == "__main__":
    # Test the tools
    print("Testing Cross-Reference Tools:")
    
    print("\n1. Resolve wallet 0xabc:")
    print(resolve_wallet("0xabc"))
    
    print("\n2. Find entity wallets for 'customer':")
    print(find_entity_wallets("customer"))
    
    print("\n3. Wallet type summary:")
    print(get_wallet_type_summary())
    
    print("\n4. Search high confidence mappings:")
    print(search_by_confidence(0.8, 1.0))
    
    print("\n5. Source analysis:")
    print(get_source_analysis())


