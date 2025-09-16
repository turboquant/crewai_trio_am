# 🚀 **Quick Start Guide**

## **🎯 Main Entry Point**

This application has **one primary entry point**: `interactive_demo.py`

---

## **⚡ Setup Options**

### **📥 Getting Started**
```bash
# Clone the repository
git clone https://github.com/turboquant/crewai_trio_am.git
cd crewai_trio_am
```

### **🚀 Option 1: Automated Setup (Recommended)**

**For Linux/Mac:**
```bash
./setup.sh
```

**For Windows:**
```bash
setup.bat
```

This will automatically:
- Check Docker and Python
- Install dependencies  
- Start containers
- Initialize the system

### **🔧 Option 2: Manual Setup**

**1. Install Dependencies:**
```bash
pip install -r requirements_real.txt
```

**2. Start Docker Containers:**
```bash
docker compose -f docker-compose.real.yml up -d
```

**3. Launch Interactive Chat:**
```bash
python interactive_demo.py
```

**That's it!** You now have access to the full AI-powered compliance analysis system.

---

## **💬 What You Can Do**

### **Direct Tool Commands:**
- `/balance C123 BTC` - Get customer balances instantly
- `/claims` - List all open claims
- `/wallet 0xabc` - Trace blockchain transactions
- `/assets` - Portfolio overview
- `/search bankruptcy` - Search knowledge base

### **Natural Language:**
- *"How much BTC does customer C123 have?"*
- *"Show me all unreconciled claims"*
- *"What happened to the missing 0.05 BTC?"*

### **Help Commands:**
- `/help` - Complete command list
- `/tools` - Direct tool commands
- `/test` - System health check

---


*Built for Alvarez & Marsal by TurboQuant - Quick prototyping for quick results.* 🏛️