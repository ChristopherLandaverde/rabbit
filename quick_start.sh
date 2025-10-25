#!/bin/bash
# Quick start script - sets up virtual environment and installs dependencies

set -e  # Exit on error

echo "🚀 Quick Start Setup for Multi-Touch Attribution API"
echo "=================================================="
echo ""

# Step 1: Create and activate virtual environment
echo "📦 Setting up virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Step 2: Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip --quiet
echo "✅ pip upgraded"
echo ""

# Step 3: Install dependencies
echo "📥 Installing dependencies..."
echo "This may take a few minutes..."
pip install -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Step 4: Run verification
echo "🧪 Running verification tests..."
if [ -f "test_setup.py" ]; then
    python test_setup.py
else
    echo "⚠️  test_setup.py not found, skipping verification"
fi
echo ""

echo "🎉 Setup complete!"
echo ""
echo "To use the application:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Run the API: python run.py"
echo "3. Access at: http://localhost:8000"
echo ""
echo "To deactivate: deactivate"
