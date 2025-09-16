"""
Audit Tool - Task logging and traceability for compliance workflows
Provides comprehensive logging of agent actions, outputs, and decision trails
"""

import sqlite3
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from crewai.tools import tool

# Get project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DB = PROJECT_ROOT / "audit.db"

def _ensure_audit_tables():
    """Ensure all audit tables exist with proper schema."""
    con = sqlite3.connect(AUDIT_DB)
    
    # Main task audit table
    con.execute("""
        CREATE TABLE IF NOT EXISTS task_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            agent_name TEXT,
            timestamp INTEGER NOT NULL,
            duration_seconds REAL,
            output_text TEXT,
            output_hash TEXT,
            status TEXT DEFAULT 'completed',
            error_message TEXT,
            metadata TEXT
        )
    """)
    
    # Tool usage audit table
    con.execute("""
        CREATE TABLE IF NOT EXISTS tool_usage_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            tool_name TEXT NOT NULL,
            timestamp INTEGER NOT NULL,
            input_params TEXT,
            output_result TEXT,
            execution_time_ms INTEGER,
            success BOOLEAN DEFAULT 1,
            error_message TEXT,
            FOREIGN KEY (task_id) REFERENCES task_audit(id)
        )
    """)
    
    # Evidence citation tracking
    con.execute("""
        CREATE TABLE IF NOT EXISTS evidence_citations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            citation_text TEXT NOT NULL,
            source_type TEXT,  -- 'ledger', 'blockchain', 'document', 'xref'
            source_reference TEXT,
            confidence_score REAL,
            timestamp INTEGER NOT NULL,
            FOREIGN KEY (task_id) REFERENCES task_audit(id)
        )
    """)
    
    con.commit()
    con.close()

def log_task(task_name: str, output: str, agent_name: str = None, 
             duration: float = None, status: str = "completed", 
             error: str = None, metadata: Dict[str, Any] = None) -> int:
    """
    Log a completed task with its output and metadata.
    
    Args:
        task_name: Name of the task (e.g., 'asset_tracing_task')
        output: Task output text
        agent_name: Name of the agent that executed the task
        duration: Task duration in seconds
        status: Task status ('completed', 'failed', 'partial')
        error: Error message if task failed
        metadata: Additional metadata as dictionary
    
    Returns:
        Task ID for linking related audit entries
    """
    try:
        _ensure_audit_tables()
        
        # Generate hash of output for integrity checking
        output_hash = hashlib.sha256(output.encode()).hexdigest()[:16]
        
        # Truncate output if too long (keep first 1MB)
        truncated_output = output[:1_000_000] if len(output) > 1_000_000 else output
        
        con = sqlite3.connect(AUDIT_DB)
        cursor = con.execute("""
            INSERT INTO task_audit 
            (task_name, agent_name, timestamp, duration_seconds, output_text, 
             output_hash, status, error_message, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_name, agent_name, int(time.time()), duration,
            truncated_output, output_hash, status, error,
            json.dumps(metadata) if metadata else None
        ))
        
        task_id = cursor.lastrowid
        con.commit()
        con.close()
        
        return task_id
        
    except Exception as e:
        print(f"Warning: Could not log task {task_name}: {e}")
        return -1

def log_tool_usage(task_id: int, tool_name: str, input_params: Dict[str, Any],
                   output_result: str, execution_time_ms: int, 
                   success: bool = True, error: str = None):
    """
    Log tool usage within a task for detailed audit trail.
    
    Args:
        task_id: ID of the parent task
        tool_name: Name of the tool used
        input_params: Parameters passed to the tool
        output_result: Tool output/result
        execution_time_ms: Execution time in milliseconds
        success: Whether tool execution was successful
        error: Error message if tool failed
    """
    try:
        _ensure_audit_tables()
        
        con = sqlite3.connect(AUDIT_DB)
        con.execute("""
            INSERT INTO tool_usage_audit 
            (task_id, tool_name, timestamp, input_params, output_result,
             execution_time_ms, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id, tool_name, int(time.time()),
            json.dumps(input_params), output_result[:10_000],  # Truncate output
            execution_time_ms, success, error
        ))
        
        con.commit()
        con.close()
        
    except Exception as e:
        print(f"Warning: Could not log tool usage: {e}")

def log_evidence_citation(task_id: int, citation: str, source_type: str,
                         source_ref: str, confidence: float = None):
    """
    Log evidence citations for traceability.
    
    Args:
        task_id: ID of the parent task
        citation: Citation text/description
        source_type: Type of source ('ledger', 'blockchain', 'document', 'xref')
        source_ref: Specific source reference (tx_hash, file path, etc.)
        confidence: Confidence score for the citation
    """
    try:
        _ensure_audit_tables()
        
        con = sqlite3.connect(AUDIT_DB)
        con.execute("""
            INSERT INTO evidence_citations
            (task_id, citation_text, source_type, source_reference, confidence_score, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (task_id, citation, source_type, source_ref, confidence, int(time.time())))
        
        con.commit()
        con.close()
        
    except Exception as e:
        print(f"Warning: Could not log evidence citation: {e}")

@tool("get_audit_summary")
def get_audit_summary(days_back: int = 7) -> str:
    """
    Get audit summary for recent activity.
    
    Args:
        days_back: Number of days to look back (default 7)
    
    Returns:
        JSON string with audit statistics and recent activity
    """
    try:
        _ensure_audit_tables()
        
        # Calculate time threshold
        time_threshold = int(time.time()) - (days_back * 24 * 60 * 60)
        
        con = sqlite3.connect(AUDIT_DB)
        
        # Get task summary
        cursor = con.execute("""
            SELECT task_name, agent_name, status, COUNT(*) as count,
                   AVG(duration_seconds) as avg_duration,
                   MAX(timestamp) as last_execution
            FROM task_audit
            WHERE timestamp >= ?
            GROUP BY task_name, agent_name, status
            ORDER BY last_execution DESC
        """, (time_threshold,))
        
        task_summary = []
        for row in cursor.fetchall():
            task_summary.append({
                "task_name": row[0],
                "agent_name": row[1],
                "status": row[2],
                "execution_count": row[3],
                "avg_duration_seconds": round(row[4], 2) if row[4] else None,
                "last_execution": datetime.fromtimestamp(row[5]).isoformat()
            })
        
        # Get tool usage summary
        cursor = con.execute("""
            SELECT tool_name, COUNT(*) as usage_count,
                   AVG(execution_time_ms) as avg_execution_time,
                   SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                   SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failure_count
            FROM tool_usage_audit
            WHERE timestamp >= ?
            GROUP BY tool_name
            ORDER BY usage_count DESC
        """, (time_threshold,))
        
        tool_summary = []
        for row in cursor.fetchall():
            tool_summary.append({
                "tool_name": row[0],
                "usage_count": row[1],
                "avg_execution_time_ms": round(row[2], 2) if row[2] else None,
                "success_rate": round((row[3] / row[1]) * 100, 1) if row[1] > 0 else 0,
                "failure_count": row[4]
            })
        
        # Get citation statistics
        cursor = con.execute("""
            SELECT source_type, COUNT(*) as citation_count,
                   AVG(confidence_score) as avg_confidence
            FROM evidence_citations
            WHERE timestamp >= ?
            GROUP BY source_type
            ORDER BY citation_count DESC
        """, (time_threshold,))
        
        citation_summary = []
        for row in cursor.fetchall():
            citation_summary.append({
                "source_type": row[0],
                "citation_count": row[1],
                "avg_confidence": round(row[2], 3) if row[2] else None
            })
        
        con.close()
        
        result = {
            "audit_period_days": days_back,
            "audit_timestamp": datetime.now().isoformat(),
            "task_summary": task_summary,
            "tool_usage_summary": tool_summary,
            "citation_summary": citation_summary,
            "total_tasks": len(task_summary),
            "total_tool_uses": sum([t["usage_count"] for t in tool_summary]),
            "total_citations": sum([c["citation_count"] for c in citation_summary])
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error generating audit summary: {str(e)}"

@tool("get_task_details")
def get_task_details(task_name: str, limit: int = 10) -> str:
    """
    Get detailed audit information for a specific task.
    
    Args:
        task_name: Name of the task to audit
        limit: Maximum number of recent executions to return
    
    Returns:
        JSON string with task execution details and related tool usage
    """
    try:
        _ensure_audit_tables()
        
        con = sqlite3.connect(AUDIT_DB)
        
        # Get recent task executions
        cursor = con.execute("""
            SELECT id, agent_name, timestamp, duration_seconds, status, 
                   error_message, metadata, output_hash
            FROM task_audit
            WHERE task_name = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (task_name, limit))
        
        executions = []
        task_ids = []
        
        for row in cursor.fetchall():
            task_id = row[0]
            task_ids.append(task_id)
            
            executions.append({
                "task_id": task_id,
                "agent_name": row[1],
                "timestamp": datetime.fromtimestamp(row[2]).isoformat(),
                "duration_seconds": row[3],
                "status": row[4],
                "error_message": row[5],
                "metadata": json.loads(row[6]) if row[6] else None,
                "output_hash": row[7]
            })
        
        # Get tool usage for these tasks
        if task_ids:
            placeholders = ",".join(["?"] * len(task_ids))
            cursor = con.execute(f"""
                SELECT task_id, tool_name, timestamp, input_params, 
                       execution_time_ms, success, error_message
                FROM tool_usage_audit
                WHERE task_id IN ({placeholders})
                ORDER BY timestamp DESC
            """, task_ids)
            
            tool_usage = []
            for row in cursor.fetchall():
                tool_usage.append({
                    "task_id": row[0],
                    "tool_name": row[1],
                    "timestamp": datetime.fromtimestamp(row[2]).isoformat(),
                    "input_params": json.loads(row[3]) if row[3] else None,
                    "execution_time_ms": row[4],
                    "success": bool(row[5]),
                    "error_message": row[6]
                })
        else:
            tool_usage = []
        
        # Get citations for these tasks
        if task_ids:
            cursor = con.execute(f"""
                SELECT task_id, citation_text, source_type, source_reference, 
                       confidence_score, timestamp
                FROM evidence_citations
                WHERE task_id IN ({placeholders})
                ORDER BY timestamp DESC
            """, task_ids)
            
            citations = []
            for row in cursor.fetchall():
                citations.append({
                    "task_id": row[0],
                    "citation_text": row[1],
                    "source_type": row[2],
                    "source_reference": row[3],
                    "confidence_score": row[4],
                    "timestamp": datetime.fromtimestamp(row[5]).isoformat()
                })
        else:
            citations = []
        
        con.close()
        
        result = {
            "task_name": task_name,
            "executions_found": len(executions),
            "recent_executions": executions,
            "tool_usage": tool_usage,
            "evidence_citations": citations
        }
        
        return json.dumps(result, indent=2)
        
    except Exception as e:
        return f"Error getting task details: {str(e)}"

@tool("validate_output_integrity")
def validate_output_integrity(task_name: str, expected_hash: str = None) -> str:
    """
    Validate the integrity of task outputs using stored hashes.
    
    Args:
        task_name: Name of the task to validate
        expected_hash: Expected hash to compare against (optional)
    
    Returns:
        JSON string with integrity check results
    """
    try:
        _ensure_audit_tables()
        
        con = sqlite3.connect(AUDIT_DB)
        
        # Get recent executions with their hashes
        cursor = con.execute("""
            SELECT id, timestamp, output_hash, status
            FROM task_audit
            WHERE task_name = ?
            ORDER BY timestamp DESC
            LIMIT 5
        """, (task_name,))
        
        executions = cursor.fetchall()
        con.close()
        
        if not executions:
            return f"No audit records found for task: {task_name}"
        
        # Check for consistency across executions
        hashes = [row[2] for row in executions if row[2]]
        unique_hashes = set(hashes)
        
        integrity_results = []
        for row in executions:
            task_id, timestamp, output_hash, status = row
            
            result = {
                "task_id": task_id,
                "timestamp": datetime.fromtimestamp(timestamp).isoformat(),
                "output_hash": output_hash,
                "status": status
            }
            
            if expected_hash:
                result["hash_match"] = output_hash == expected_hash
            
            integrity_results.append(result)
        
        summary = {
            "task_name": task_name,
            "total_executions_checked": len(executions),
            "unique_output_hashes": len(unique_hashes),
            "output_consistency": len(unique_hashes) <= 1,  # All outputs same
            "expected_hash_provided": expected_hash is not None,
            "integrity_results": integrity_results
        }
        
        if expected_hash:
            matching_count = sum(1 for r in integrity_results if r.get("hash_match", False))
            summary["expected_hash_matches"] = matching_count
        
        return json.dumps(summary, indent=2)
        
    except Exception as e:
        return f"Error validating output integrity: {str(e)}"

if __name__ == "__main__":
    # Test the audit tools
    print("Testing Audit Tools:")
    
    # Log a sample task
    task_id = log_task(
        task_name="test_task",
        output="Sample output for testing",
        agent_name="test_agent",
        duration=1.5,
        metadata={"test": True}
    )
    
    print(f"Logged test task with ID: {task_id}")
    
    print("\n1. Audit summary:")
    print(get_audit_summary(30))
    
    print("\n2. Task details:")
    print(get_task_details("test_task"))
    
    print("\n3. Integrity validation:")
    print(validate_output_integrity("test_task"))


