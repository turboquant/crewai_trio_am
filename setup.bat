@echo off
REM CrewAI Compliance Analysis - Quick Setup Script (Windows)

echo 🚀 CrewAI Compliance Analysis - Setup
echo =====================================

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop first.
    echo    Download from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo ✅ Docker is running

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8+ first.
    echo    Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ✅ Python found
python --version

REM Install Python dependencies
echo 📦 Installing Python dependencies...
python -m pip install -r requirements_real.txt --quiet

if errorlevel 1 (
    echo ❌ Failed to install Python dependencies
    echo    Try: pip install -r requirements_real.txt
    pause
    exit /b 1
)

echo ✅ Python dependencies installed

REM Start Docker containers
echo 🐳 Starting Docker containers...
docker compose -f docker-compose.real.yml up -d

if errorlevel 1 (
    echo ❌ Failed to start Docker containers
    echo    Try manually: docker compose -f docker-compose.real.yml up -d
    pause
    exit /b 1
)

REM Wait for containers to start
echo ⏳ Waiting for containers to initialize...
timeout /t 10 /nobreak >nul

REM Check container health
echo 🔍 Checking container status...
docker compose -f docker-compose.real.yml ps

REM Initialize RAG database
echo 📚 Initializing knowledge base...
docker exec crewai-compliance python3 src/tools/initialize_rag_db.py 2>nul || echo    (Knowledge base setup - optional)

echo.
echo 🎉 Setup complete!
echo.
echo 📋 Next steps:
echo    1. Launch the application:
echo       python interactive_demo.py
echo.
echo    2. Try these commands in the chat:
echo       /test          - System health check
echo       /help          - Show all commands
echo       /balance C123 BTC - Quick data query
echo.
echo    3. For more help:
echo       type QUICKSTART.md
echo       type README.md
echo.

REM Optional environment file
if not exist ".env" (
    echo 💡 Tip: Copy env.example to .env to customize configuration
    echo    copy env.example .env
    echo.
)

echo 🚀 Ready to analyze compliance data!
pause
