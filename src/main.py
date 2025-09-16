#!/usr/bin/env python3
"""
Main Entry Point for CrewAI Compliance Experts
Cryptocurrency Bankruptcy Assistant
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from crew import ComplianceCrewOrchestrator, run_compliance_analysis

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CrewAI Compliance Experts - Crypto Bankruptcy Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic analysis for specific customers
  python main.py --customers C123,C789 --wallets 0xabc,0xdef
  
  # Full analysis with all available data
  python main.py --full-analysis
  
  # Run with custom case name
  python main.py --case-name "FTX Bankruptcy Analysis" --customers C123
  
  # JSON output for integration
  python main.py --output-format json --customers C123
        """
    )
    
    # Analysis targets
    parser.add_argument(
        "--customers", "-c",
        help="Comma-separated list of customer IDs to analyze (e.g., C123,C789)",
        type=str
    )
    
    parser.add_argument(
        "--wallets", "-w", 
        help="Comma-separated list of wallet addresses to trace (e.g., 0xabc,0xdef)",
        type=str
    )
    
    parser.add_argument(
        "--full-analysis", "-f",
        help="Run analysis on all available customers and wallets",
        action="store_true"
    )
    
    # Configuration
    parser.add_argument(
        "--config-dir",
        help="Path to configuration directory (default: config/)",
        type=str,
        default="config"
    )
    
    parser.add_argument(
        "--case-name",
        help="Name of the case for documentation",
        type=str,
        default="Crypto Exchange Bankruptcy Analysis"
    )
    
    # Output options
    parser.add_argument(
        "--output-dir", "-o",
        help="Directory for output files (default: current directory)",
        type=str,
        default="."
    )
    
    parser.add_argument(
        "--output-format",
        help="Output format for results",
        choices=["text", "json", "yaml"],
        default="text"
    )
    
    parser.add_argument(
        "--save-results",
        help="Save detailed results to file",
        action="store_true"
    )
    
    # Execution options
    parser.add_argument(
        "--dry-run",
        help="Show what would be analyzed without running",
        action="store_true"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        help="Verbose output",
        action="store_true"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        help="Minimal output",
        action="store_true"
    )
    
    # Analysis parameters
    parser.add_argument(
        "--max-hops",
        help="Maximum number of hops to trace in blockchain analysis",
        type=int,
        default=5
    )
    
    parser.add_argument(
        "--confidence-threshold",
        help="Minimum confidence threshold for entity resolution",
        type=float,
        default=0.3
    )
    
    return parser.parse_args()

def get_default_targets() -> Dict[str, List[str]]:
    """Get default analysis targets from available data."""
    try:
        import pandas as pd
        
        # Get available customers from claims data
        claims_df = pd.read_csv("claims/claims.csv")
        available_customers = claims_df["customer_id"].unique().tolist()
        
        # Get available wallets from entity mapping
        entities_df = pd.read_csv("entities/xref_wallets.csv")
        available_wallets = entities_df["wallet"].unique().tolist()
        
        return {
            "customers": available_customers[:5],  # Limit to first 5 for performance
            "wallets": available_wallets[:5]
        }
    except Exception as e:
        print(f"Warning: Could not load default targets: {e}")
        return {
            "customers": ["C123", "C789", "C456"],
            "wallets": ["0xabc", "0xdef", "0xghi"]
        }

def format_results(results: Dict[str, Any], format_type: str) -> str:
    """Format analysis results for output."""
    if format_type == "json":
        return json.dumps(results, indent=2, default=str)
    
    elif format_type == "yaml":
        try:
            import yaml
            return yaml.dump(results, default_flow_style=False, indent=2)
        except ImportError:
            print("Warning: PyYAML not available, using JSON format")
            return json.dumps(results, indent=2, default=str)
    
    else:  # text format
        output = []
        output.append("=" * 60)
        output.append("CREWAI COMPLIANCE EXPERTS - ANALYSIS RESULTS")
        output.append("=" * 60)
        
        # Execution summary
        status = results.get("execution_status", "unknown")
        output.append(f"Status: {status.upper()}")
        
        if "start_time" in results:
            output.append(f"Started: {results['start_time']}")
        if "duration_seconds" in results:
            output.append(f"Duration: {results['duration_seconds']:.2f} seconds")
        
        # Input summary
        inputs = results.get("inputs", {})
        if inputs:
            output.append(f"\nAnalysis Targets:")
            output.append(f"  Customers: {inputs.get('target_customers', [])}")
            output.append(f"  Wallets: {inputs.get('target_wallets', [])}")
            output.append(f"  Case: {inputs.get('case_name', 'Unknown')}")
        
        # Task results
        task_results = results.get("task_results", {})
        if task_results:
            output.append(f"\nTask Results ({len(task_results)} tasks):")
            for task_name, result in task_results.items():
                output.append(f"  {task_name}:")
                output.append(f"    ✓ Completed: {result.get('timestamp', 'Unknown')}")
                output.append(f"    ✓ Output length: {len(result.get('output', ''))} characters")
                output.append(f"    ✓ Task ID: {result.get('task_id', 'N/A')}")
        
        # Error information
        if "error" in results:
            output.append(f"\nError: {results['error']}")
        
        output.append("=" * 60)
        return "\n".join(output)

def save_results(results: Dict[str, Any], output_dir: str, format_type: str):
    """Save results to files."""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save main results
    if format_type == "json":
        results_file = output_path / f"analysis_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
    else:
        results_file = output_path / f"analysis_results_{timestamp}.txt"
        with open(results_file, 'w') as f:
            f.write(format_results(results, "text"))
    
    print(f"✓ Results saved to: {results_file}")
    
    # Save individual task outputs if available
    task_results = results.get("task_results", {})
    for task_name, result in task_results.items():
        task_file = output_path / f"{task_name}_{timestamp}.md"
        with open(task_file, 'w') as f:
            f.write(result.get("output", ""))
        print(f"✓ Task output saved to: {task_file}")

def print_analysis_plan(customers: List[str], wallets: List[str], dry_run: bool = False):
    """Print what will be analyzed."""
    print("📋 Analysis Plan:")
    print(f"   Target Customers: {customers}")
    print(f"   Target Wallets: {wallets}")
    print(f"   Total Customers: {len(customers)}")
    print(f"   Total Wallets: {len(wallets)}")
    
    if dry_run:
        print("\n🔍 Analysis Tasks:")
        print("   1. Asset Tracing Agent:")
        print("      - Analyze ledger withdrawals for target customers")
        print("      - Trace on-chain flows from target wallets")  
        print("      - Resolve wallet addresses to entities")
        print("      - Generate comprehensive flow diagrams")
        print("   2. Claims Reconciliation Agent:")
        print("      - Load all unreconciled claims")
        print("      - Reconcile against ledger balances")
        print("      - Cross-reference with tracing results")
        print("      - Generate reconciliation summary")
        print("   3. Legal Documentation Agent:")
        print("      - Integrate findings from previous tasks")
        print("      - Draft court-ready expert report")
        print("      - Include comprehensive appendices")
        print("      - Ensure proper citations throughout")

def main():
    """Main execution function."""
    args = parse_arguments()
    
    # Configure output level
    if args.quiet:
        import logging
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # Determine analysis targets
        if args.full_analysis:
            defaults = get_default_targets()
            target_customers = defaults["customers"]
            target_wallets = defaults["wallets"]
            print("🔍 Running full analysis with all available data")
        else:
            target_customers = args.customers.split(",") if args.customers else ["C123"]
            target_wallets = args.wallets.split(",") if args.wallets else ["0xabc"]
        
        # Clean up targets
        target_customers = [c.strip() for c in target_customers]
        target_wallets = [w.strip() for w in target_wallets]
        
        # Print analysis plan
        print_analysis_plan(target_customers, target_wallets, args.dry_run)
        
        if args.dry_run:
            print("\n✅ Dry run complete - no analysis executed")
            return 0
        
        # Prepare additional inputs
        additional_inputs = {
            "case_name": args.case_name,
            "max_hops": args.max_hops,
            "confidence_threshold": args.confidence_threshold,
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
            "output_directory": args.output_dir
        }
        
        # Run the analysis
        print(f"\n🚀 Starting compliance analysis...")
        print(f"   Configuration: {args.config_dir}")
        print(f"   Output format: {args.output_format}")
        
        results = run_compliance_analysis(
            target_customers=target_customers,
            target_wallets=target_wallets,
            config_dir=args.config_dir
        )
        
        # Add additional inputs to results for reference
        if "inputs" not in results:
            results["inputs"] = {}
        results["inputs"].update(additional_inputs)
        
        # Output results
        formatted_output = format_results(results, args.output_format)
        
        if not args.quiet:
            print(f"\n{formatted_output}")
        
        # Save results if requested
        if args.save_results:
            save_results(results, args.output_dir, args.output_format)
        
        # Return appropriate exit code
        if results.get("execution_status") == "completed":
            if not args.quiet:
                print("\n✅ Analysis completed successfully!")
            return 0
        else:
            if not args.quiet:
                print("\n❌ Analysis completed with errors")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)


