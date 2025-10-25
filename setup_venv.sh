#!/bin/bash
# Virtual environment setup and activation script

echo "🔧 Setting up virtual environment..."

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

echo "✅ Virtual environment is ready!"
echo ""
echo "To activate manually, run:"
echo "  source venv/bin/activate"
echo ""
echo "To install dependencies, run:"
echo "  pip install -r requirements.txt"
echo ""
echo "To deactivate, run:"
echo "  deactivate"
