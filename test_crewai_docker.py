#!/usr/bin/env python3
"""
Docker CrewAI Test - Verifies real CrewAI setup in containerized environment
"""
import os
import sys
import subprocess
from dotenv import load_dotenv

def check_imports():
    """Test all critical imports"""
    print("🧪 Testing imports...")
    try:
        import crewai
        print(f"✅ CrewAI: {crewai.__version__}")
        
        from crewai import Agent, Task, Crew, Process
        print("✅ CrewAI Core Components")
        
        import ollama
        print("✅ Ollama")
        
        from langchain_ollama import OllamaLLM
        print("✅ LangChain Ollama")
        
        import chromadb
        print("✅ ChromaDB")
        
        import duckdb
        print("✅ DuckDB")
        
        import networkx
        print("✅ NetworkX")
        
        print("✅ All imports successful!")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_ollama_connection():
    """Test connection to Ollama server"""
    print("\n🧪 Testing Ollama connection...")
    try:
        import ollama
        
        # Try to connect to Ollama
        ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
        print(f"Connecting to: {ollama_url}")
        
        # List available models
        client = ollama.Client(host=ollama_url)
        models = client.list()
        
        # Handle both dictionary and Pydantic model formats
        if hasattr(models, 'models'):
            # New Pydantic format
            model_list = models.models
            print(f"✅ Connected to Ollama - Models available: {len(model_list)}")
            
            for model in model_list:
                if hasattr(model, 'model'):
                    print(f"   - {model.model}")
                elif isinstance(model, dict) and 'name' in model:
                    print(f"   - {model['name']}")
                else:
                    print(f"   - {model}")
        else:
            # Legacy dictionary format
            model_list = models.get('models', [])
            print(f"✅ Connected to Ollama - Models available: {len(model_list)}")
            
            for model in model_list:
                if isinstance(model, dict) and 'name' in model:
                    print(f"   - {model['name']}")
                else:
                    print(f"   - {model}")
        
        return True
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        return False

def test_simple_agent():
    """Create a simple agent and test basic functionality"""
    print("\n🧪 Testing basic CrewAI agent...")
    try:
        from crewai import Agent
        from langchain_ollama import OllamaLLM
        
        # Configure LLM
        ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
        llm = OllamaLLM(
            base_url=ollama_url,
            model="llama3.1:8b",
            temperature=0.1
        )
        
        # Create simple agent
        agent = Agent(
            role="Test Agent",
            goal="Test basic CrewAI functionality",
            backstory="A simple test agent for validation",
            llm=llm,
            verbose=True
        )
        
        print("✅ Agent created successfully!")
        print(f"   Role: {agent.role}")
        print(f"   Goal: {agent.goal}")
        
        return True
    except Exception as e:
        print(f"❌ Agent creation failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🐳 Docker CrewAI Test Suite")
    print("=" * 40)
    
    # Load environment variables
    load_dotenv()
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Imports
    if check_imports():
        success_count += 1
    
    # Test 2: Ollama Connection
    if test_ollama_connection():
        success_count += 1
        
    # Test 3: Basic Agent
    if test_simple_agent():
        success_count += 1
    
    # Results
    print("\n" + "=" * 40)
    print(f"🏁 Test Results: {success_count}/{total_tests} passed")
    
    if success_count == total_tests:
        print("✅ All tests passed! CrewAI is ready!")
        return 0
    else:
        print("❌ Some tests failed. Check the logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
