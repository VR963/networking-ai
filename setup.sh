#!/bin/bash

# Networking AI - Quick Setup Script
# This script sets up the development environment

set -e  # Exit on error

echo "🚀 Setting up Networking AI..."
echo ""

# Check Python version
echo "📋 Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    echo "❌ Error: Python not found. Please install Python 3.9 or higher."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "✅ Found Python $PYTHON_VERSION"
echo ""

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip -q
echo "✅ pip upgraded"
echo ""

# Install package in development mode
echo "📚 Installing networking-ai package..."
pip install -e . -q
echo "✅ Package installed"
echo ""

# Install development dependencies (optional)
read -p "Install development dependencies? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📚 Installing development dependencies..."
    pip install -e ".[dev]" -q
    echo "✅ Development dependencies installed"
    echo ""
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ .env file created (please edit it to add your API keys)"
    else
        echo "⚠️  .env.example not found, skipping"
    fi
else
    echo "✅ .env file already exists"
fi
echo ""

# Verify installation
echo "🧪 Verifying installation..."
python -c "import networking_ai; print('✅ networking_ai module imported successfully!')" || {
    echo "❌ Installation verification failed"
    exit 1
}
echo ""

# Print success message
echo "═══════════════════════════════════════════════"
echo "🎉 Setup complete!"
echo "═══════════════════════════════════════════════"
echo ""
echo "To activate the virtual environment, run:"
echo "  source venv/bin/activate"
echo ""
echo "To test the installation, run:"
echo "  python -c \"import networking_ai; print('Success!')\""
echo ""
echo "To run tests:"
echo "  pytest"
echo ""
echo "See SETUP_GUIDE.md for more information."
echo ""
