# Quick Setup Guide for Networking AI

This guide will help you get the Networking AI project up and running on your local machine.

## Prerequisites

- Python 3.9 or higher (you have Python 3.11 ✅)
- Git

## Installation Steps

### 1. Navigate to the project directory

```bash
cd networking-ai
```

### 2. Create a virtual environment

On macOS/Linux:
```bash
python3 -m venv venv
```

On Windows:
```bash
python -m venv venv
```

### 3. Activate the virtual environment

On macOS/Linux:
```bash
source venv/bin/activate
```

On Windows (Command Prompt):
```bash
venv\Scripts\activate.bat
```

On Windows (PowerShell):
```bash
venv\Scripts\Activate.ps1
```

After activation, you should see `(venv)` in your terminal prompt.

### 4. Upgrade pip

```bash
pip install --upgrade pip
```

### 5. Install the package in development mode

This will install all dependencies and make the `networking_ai` module available:

```bash
pip install -e .
```

Or if you want development dependencies too:

```bash
pip install -e ".[dev]"
```

### 6. Verify the installation

```bash
python -c "import networking_ai; print('Installation successful!')"
```

You should see: `Installation successful!`

### 7. Set up environment variables (optional, for AI features)

Copy the example environment file:

```bash
cp .env.example .env
```

Then edit `.env` and add your API keys:

```bash
# Edit with your preferred editor
nano .env
# or
vim .env
# or open in your text editor
```

Add your Anthropic API key:
```
ANTHROPIC_API_KEY=your_api_key_here
```

## Quick Test

Run a quick test to ensure everything works:

```bash
python3 -c "
from networking_ai import UserProfile, NetworkingAgent

# Create a test profile
user = UserProfile(
    user_id='test123',
    name='Test User',
    skills=['Python', 'AI'],
    bio='Test user'
)

print(f'Profile created: {user.name}')
print('✅ Everything is working!')
"
```

## Running Tests

```bash
# Make sure you're in the venv
pytest

# Or run with coverage
pytest --cov=networking_ai
```

## Troubleshooting

### "command not found: python"
Use `python3` instead of `python` on macOS/Linux.

### "No module named 'networking_ai'"
Make sure you:
1. Activated the virtual environment
2. Installed the package with `pip install -e .`

### ImportError for dependencies
Reinstall dependencies:
```bash
pip install --upgrade -r requirements.txt
```

### Permission issues
On some systems, you might need to use:
```bash
python3 -m pip install --user -e .
```

## Next Steps

Once installed, check out:
- `examples/basic_usage.py` - Basic usage examples
- `README.md` - Full documentation
- `tests/` - Test suite examples

## Development Workflow

```bash
# Activate venv (do this every time you open a new terminal)
source venv/bin/activate

# Run tests
pytest

# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type check
mypy src/
```

## Using Docker (Alternative)

If you prefer Docker:

```bash
# Build the image
docker-compose build

# Run the application
docker-compose up
```

See `DEPLOYMENT.md` for more details.
