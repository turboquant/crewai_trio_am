"""
Real CrewAI Implementation
Production-ready crew orchestration with actual CrewAI framework
"""

import os
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Real CrewAI imports
from crewai import Agent, Task, Crew, Process
from crewai.tools import tool
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

# Import all tools (using actual function names)
from tools.ledger_query import (
    ledger_balance, ledger_movements, ledger_withdrawal_history, ledger_asset_summary
)
from tools.wallet_graph import (
    wallet_shortest_path, wallet_outward_hops, wallet_inward_flows, wallet_transaction_summary
)
from tools.claims_repo import (
    list_open_claims, get_claim_details, claims_by_customer, 
    claims_reconciliation_summary, update_claim_status, search_claims
)
from tools.xref_tool import (
    resolve_wallet, find_entity_wallets, get_wallet_type_summary, 
    search_by_confidence, validate_wallet_mapping, get_source_analysis
)
from tools.rag_search import (
    rag_search, search_by_document, list_knowledge_sources, search_citations
)
from tools.audit import log_task, get_audit_summary, get_task_details

load_dotenv()

# Get project root directory
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"

class RealComplianceCrewOrchestrator:
    """
    Real CrewAI orchestration for cryptocurrency bankruptcy compliance analysis.
    """
    
    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir) if config_dir else CONFIG_DIR
        self.agents_config = {}
        self.tasks_config = {}
        self.crew = None
        self.execution_results = {}
        self.llm = None
        
        # Load configurations
        self._load_configurations()
        
        # Initialize LLM
        self._initialize_llm()
        
        # Tool mapping
        self.available_tools = self._get_available_tools()
    
    def _initialize_llm(self):
        """Initialize the appropriate LLM based on configuration."""
        provider = os.getenv('LLM_PROVIDER', 'ollama').lower()
        
        try:
            if provider == 'ollama':
                self.llm = ChatOllama(
                    model=f"ollama/{os.getenv('OLLAMA_MODEL', 'llama3.1:8b')}",
                    base_url=os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
                    temperature=0.2,
                    num_ctx=8192
                )
                print(f"✓ Initialized Ollama LLM: ollama/{os.getenv('OLLAMA_MODEL', 'llama3.1:8b')}")
                
            elif provider == 'openai':
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    raise ValueError("OPENAI_API_KEY not found in environment")
                
                self.llm = ChatOpenAI(
                    model=os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview'),
                    api_key=api_key,
                    temperature=0.2,
                    max_tokens=4000
                )
                print(f"✓ Initialized OpenAI LLM: {os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')}")
                
            elif provider == 'anthropic':
                api_key = os.getenv('ANTHROPIC_API_KEY')
                if not api_key:
                    raise ValueError("ANTHROPIC_API_KEY not found in environment")
                
                self.llm = ChatAnthropic(
                    model=os.getenv('ANTHROPIC_MODEL', 'claude-3-sonnet-20240229'),
                    api_key=api_key,
                    temperature=0.2,
                    max_tokens=4000
                )
                print(f"✓ Initialized Anthropic LLM: {os.getenv('ANTHROPIC_MODEL', 'claude-3-sonnet-20240229')}")
                
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
                
        except Exception as e:
            print(f"❌ LLM initialization failed: {e}")
            print("💡 Falling back to Ollama with default settings")
            
            # Fallback to Ollama
            self.llm = ChatOllama(
                model='ollama/llama3.1:8b',
                base_url='http://localhost:11434',
                temperature=0.2
            )
    
    def _load_configurations(self):
        """Load agent and task configurations from YAML files."""
        try:
            agents_file = self.config_dir / "agents.yaml"
            tasks_file = self.config_dir / "tasks.yaml"
            
            if agents_file.exists():
                with open(agents_file, 'r') as f:
                    self.agents_config = yaml.safe_load(f)
            else:
                raise FileNotFoundError(f"Agents config not found: {agents_file}")
            
            if tasks_file.exists():
                with open(tasks_file, 'r') as f:
                    self.tasks_config = yaml.safe_load(f)
            else:
                raise FileNotFoundError(f"Tasks config not found: {tasks_file}")
                
            print(f"✓ Loaded configurations from {self.config_dir}")
            
        except Exception as e:
            print(f"❌ Error loading configurations: {e}")
            raise
    
    def _get_available_tools(self) -> Dict[str, Any]:
        """Get mapping of tool names to tool functions."""
        return {
            # Ledger query tools
            "ledger_balance": ledger_balance,
            "ledger_movements": ledger_movements,
            "ledger_withdrawal_history": ledger_withdrawal_history,
            "ledger_asset_summary": ledger_asset_summary,
            
            # Wallet graph tools
            "wallet_shortest_path": wallet_shortest_path,
            "wallet_outward_hops": wallet_outward_hops,
            "wallet_inward_flows": wallet_inward_flows,
            "wallet_transaction_summary": wallet_transaction_summary,
            
            # Claims repository tools
            "list_open_claims": list_open_claims,
            "get_claim_details": get_claim_details,
            "claims_by_customer": claims_by_customer,
            "claims_reconciliation_summary": claims_reconciliation_summary,
            "update_claim_status": update_claim_status,
            "search_claims": search_claims,
            
            # Cross-reference tools
            "resolve_wallet": resolve_wallet,
            "find_entity_wallets": find_entity_wallets,
            "get_wallet_type_summary": get_wallet_type_summary,
            "search_by_confidence": search_by_confidence,
            "validate_wallet_mapping": validate_wallet_mapping,
            "get_source_analysis": get_source_analysis,
            
            # RAG search tools
            "rag_search": rag_search,
            "search_by_document": search_by_document,
            "list_knowledge_sources": list_knowledge_sources,
            "search_citations": search_citations,
            
            # Audit tools
            "get_audit_summary": get_audit_summary,
            "get_task_details": get_task_details
        }
    
    def _create_agents(self) -> List[Agent]:
        """Create real CrewAI agents based on configuration."""
        agents = []
        
        for agent_name, config in self.agents_config.items():
            if agent_name.startswith('agent_') or agent_name == 'agent_config':
                continue  # Skip non-agent config sections
                
            # Get tools for this agent
            agent_tools = []
            tool_names = config.get('tools', [])
            
            for tool_name in tool_names:
                if tool_name in self.available_tools:
                    agent_tools.append(self.available_tools[tool_name])
                else:
                    print(f"⚠️  Warning: Tool '{tool_name}' not found for agent '{agent_name}'")
            
            # Get system prompt if available
            system_prompt = ""
            if 'agent_prompts' in self.agents_config:
                agent_prompts = self.agents_config['agent_prompts']
                if agent_name in agent_prompts:
                    system_prompt = agent_prompts[agent_name].get('system_prompt', '')
            
            # Create real CrewAI agent
            agent = Agent(
                role=config.get('role', 'Analyst'),
                goal=config.get('goal', 'Perform analysis'),
                backstory=config.get('backstory', 'Experienced analyst'),
                tools=agent_tools,
                llm=self.llm,  # Use the initialized LLM
                verbose=config.get('verbose', True),
                memory=config.get('memory', True),
                max_iter=config.get('max_iter', 15),
                allow_delegation=config.get('allow_delegation', False),
                system_message=system_prompt if system_prompt else None
            )
            
            agents.append(agent)
            print(f"✓ Created real agent: {agent_name} with {len(agent_tools)} tools")
        
        return agents
    
    def _create_tasks(self, agents: List[Agent], inputs: Dict[str, Any] = None) -> List[Task]:
        """Create real CrewAI tasks based on configuration."""
        tasks = []
        agent_map = {}
        
        # Map agent names to agent objects
        agent_names = [name for name in self.agents_config.keys() if name.endswith('_agent')]
        for i, agent in enumerate(agents):
            if i < len(agent_names):
                agent_map[agent_names[i]] = agent
        
        # Get task execution order
        task_order = self.tasks_config.get('task_config', {}).get('execution_order', [])
        if not task_order:
            task_order = [name for name in self.tasks_config.keys() if name.endswith('_task')]
        
        for task_name in task_order:
            if task_name not in self.tasks_config:
                continue
                
            config = self.tasks_config[task_name]
            agent_name = config.get('agent')
            
            if agent_name not in agent_map:
                print(f"⚠️  Warning: Agent '{agent_name}' not found for task '{task_name}'")
                continue
            
            # Format description with inputs if provided
            description = config.get('description', 'Perform analysis')
            if inputs:
                try:
                    description = description.format(**inputs)
                except KeyError as e:
                    print(f"⚠️  Warning: Could not format task description, missing key: {e}")
            
            # Create real CrewAI task
            task = Task(
                description=description,
                expected_output=config.get('expected_output', 'Analysis results'),
                agent=agent_map[agent_name],
                output_file=config.get('output_file'),
                callback=lambda output, task_name=task_name: self._task_callback(task_name, output)
            )
            
            tasks.append(task)
            print(f"✓ Created real task: {task_name} assigned to {agent_name}")
        
        return tasks
    
    def _task_callback(self, task_name: str, output: str):
        """Callback function for task completion logging."""
        try:
            # Log task completion to audit system
            task_id = log_task(
                task_name=task_name,
                output=str(output),
                agent_name="real_crew_agent",
                status="completed",
                metadata={
                    "execution_timestamp": datetime.now().isoformat(),
                    "output_length": len(str(output)),
                    "crew_orchestrated": True,
                    "llm_provider": os.getenv('LLM_PROVIDER', 'ollama')
                }
            )
            
            # Store results for later access
            self.execution_results[task_name] = {
                "output": str(output),
                "task_id": task_id,
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"✅ Task '{task_name}' completed and logged (ID: {task_id})")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not log task completion for '{task_name}': {e}")
    
    def create_crew(self, inputs: Dict[str, Any] = None) -> Crew:
        """Create and configure the real CrewAI crew."""
        try:
            # Create agents and tasks
            agents = self._create_agents()
            tasks = self._create_tasks(agents, inputs)
            
            if not agents:
                raise ValueError("No agents were created")
            if not tasks:
                raise ValueError("No tasks were created")
            
            # Create real CrewAI crew
            self.crew = Crew(
                agents=agents,
                tasks=tasks,
                process=Process.sequential,  # Sequential execution for dependencies
                verbose=True,
                memory=True,
                max_rpm=10,  # Rate limiting
                share_crew=False  # Keep data private
            )
            
            print(f"✅ Created REAL CrewAI crew with {len(agents)} agents and {len(tasks)} tasks")
            return self.crew
            
        except Exception as e:
            print(f"❌ Error creating real crew: {e}")
            return None
    
    def run_analysis(self, target_customers: List[str] = None, 
                    target_wallets: List[str] = None,
                    additional_inputs: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Run the complete compliance analysis workflow with real CrewAI.
        
        Args:
            target_customers: List of customer IDs to analyze
            target_wallets: List of wallet addresses to trace
            additional_inputs: Additional parameters for task execution
        
        Returns:
            Dictionary with execution results and metadata
        """
        try:
            start_time = datetime.now()
            
            # Prepare inputs
            inputs = {
                "target_customers": target_customers or ["C123", "C789"],
                "target_wallets": target_wallets or ["0xabc", "0xdef"],
                "analysis_date": datetime.now().strftime("%Y-%m-%d"),
                "case_name": "Crypto Exchange Bankruptcy Analysis"
            }
            
            if additional_inputs:
                inputs.update(additional_inputs)
            
            print(f"🚀 Starting REAL CrewAI compliance analysis with inputs: {inputs}")
            
            # Create crew if not already created
            if not self.crew:
                self.crew = self.create_crew(inputs)
            
            if not self.crew:
                raise RuntimeError("Could not create real CrewAI crew")
            
            # Execute the workflow with real CrewAI
            print("🤖 Executing REAL CrewAI workflow...")
            result = self.crew.kickoff(inputs=inputs)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Compile results
            analysis_results = {
                "execution_status": "completed",
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "inputs": inputs,
                "crew_result": str(result),
                "task_results": self.execution_results,
                "agents_count": len(self.crew.agents),
                "tasks_count": len(self.crew.tasks),
                "llm_provider": os.getenv('LLM_PROVIDER', 'ollama'),
                "real_crewai": True
            }
            
            print(f"🎉 REAL CrewAI analysis completed in {duration:.2f} seconds")
            return analysis_results
            
        except Exception as e:
            print(f"❌ REAL CrewAI analysis failed: {e}")
            return {
                "execution_status": "failed",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "inputs": inputs if 'inputs' in locals() else {},
                "real_crewai": True
            }

# Convenience functions
def run_real_compliance_analysis(target_customers: List[str] = None,
                                 target_wallets: List[str] = None,
                                 config_dir: str = None) -> Dict[str, Any]:
    """
    Convenience function to run the complete compliance analysis with real CrewAI.
    
    Args:
        target_customers: List of customer IDs to analyze
        target_wallets: List of wallet addresses to trace  
        config_dir: Path to configuration directory
    
    Returns:
        Analysis results dictionary
    """
    orchestrator = RealComplianceCrewOrchestrator(config_dir)
    return orchestrator.run_analysis(target_customers, target_wallets)

if __name__ == "__main__":
    # Test the real orchestrator
    print("🤖 Testing REAL CrewAI Compliance Orchestrator...")
    
    orchestrator = RealComplianceCrewOrchestrator()
    
    # Test crew creation
    crew = orchestrator.create_crew()
    
    if crew:
        print("✅ Real CrewAI crew creation successful")
        
        # Test analysis run
        results = orchestrator.run_analysis(
            target_customers=["C123"],
            target_wallets=["0xabc"]
        )
        
        print(f"📊 Analysis status: {results.get('execution_status')}")
        print(f"⏱️  Duration: {results.get('duration_seconds', 0):.2f} seconds")
        print(f"🤖 LLM Provider: {results.get('llm_provider')}")
        print(f"✅ Real CrewAI: {results.get('real_crewai', False)}")
    else:
        print("❌ Real CrewAI crew creation failed")

# Aliases for main.py compatibility
ComplianceCrewOrchestrator = RealComplianceCrewOrchestrator
run_compliance_analysis = run_real_compliance_analysis
