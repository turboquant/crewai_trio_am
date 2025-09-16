#!/bin/bash

# CrewAI Compliance Analysis - Quick Setup Script
echo "🚀 CrewAI Compliance Analysis - Setup"
echo "====================================="

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    echo "   Download from: https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo "✅ Docker is running"

# Check Python
if ! python3 --version >/dev/null 2>&1 && ! python --version >/dev/null 2>&1; then
    echo "❌ Python is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python"
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
fi

echo "✅ Python found: $($PYTHON_CMD --version)"

# Install Python dependencies
echo "📦 Installing Python dependencies..."
$PYTHON_CMD -m pip install -r requirements_real.txt --quiet

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Python dependencies"
    echo "   Try: pip install -r requirements_real.txt"
    exit 1
fi

echo "✅ Python dependencies installed"

# Start Docker containers
echo "🐳 Starting Docker containers..."
docker compose -f docker-compose.real.yml up -d

if [ $? -ne 0 ]; then
    echo "❌ Failed to start Docker containers"
    echo "   Try manually: docker compose -f docker-compose.real.yml up -d"
    exit 1
fi

# Wait a moment for containers to start
echo "⏳ Waiting for containers to initialize..."
sleep 10

# Check container health
echo "🔍 Checking container status..."
docker compose -f docker-compose.real.yml ps

# Initialize RAG database
echo "📚 Initializing knowledge base..."
docker exec crewai-compliance python3 src/tools/initialize_rag_db.py 2>/dev/null || echo "   (Knowledge base setup - optional)"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Launch the application:"
echo "      $PYTHON_CMD interactive_demo.py"
echo ""
echo "   2. Try these commands in the chat:"
echo "      /test          - System health check"
echo "      /help          - Show all commands"
echo "      /balance C123 BTC - Quick data query"
echo ""
echo "   3. For more help:"
echo "      cat QUICKSTART.md"
echo "      cat README.md"
echo ""

# Optional environment file
if [ ! -f ".env" ]; then
    echo "💡 Tip: Copy env.example to .env to customize configuration"
    echo "   cp env.example .env"
    echo ""
fi

echo "🚀 Ready to analyze compliance data!"
