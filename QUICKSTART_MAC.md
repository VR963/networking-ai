# Quick Start Guide for macOS

Follow these steps to get Networking AI running on your Mac.

## Step-by-Step Setup

### 1. Open Terminal and navigate to the project

```bash
cd /path/to/networking-ai
```

### 2. Remove old virtual environment (if exists)

```bash
rm -rf venv
```

### 3. Create a fresh virtual environment

```bash
python3 -m venv venv
```

### 4. Activate the virtual environment

```bash
source venv/bin/activate
```

You should see `(venv)` appear in your terminal prompt.

### 5. Upgrade pip

```bash
pip install --upgrade pip
```

### 6. Install the package

This will take a few minutes as it installs ML libraries:

```bash
pip install -e .
```

**Note:** The installation may take 2-5 minutes because it installs:
- PyTorch/ML dependencies for sentence transformers
- Anthropic Claude SDK
- LangChain ecosystem
- ChromaDB vector database
- Other dependencies

### 7. Verify installation

```bash
python3 -c "import networking_ai; print('✅ Success!')"
```

If you see `✅ Success!`, you're all set!

### 8. Create environment file (optional)

```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

Add your Anthropic API key if you want AI features:
```
ANTHROPIC_API_KEY=sk-ant-...
```

## Quick Test

Try this simple test:

```bash
python3 << 'EOF'
from networking_ai import UserProfile, NetworkingAgent

# Create a test profile
alice = UserProfile(
    user_id="alice123",
    name="Alice Johnson",
    skills=["Python", "Machine Learning"],
    bio="ML Engineer"
)

print(f"✅ Created profile for: {alice.name}")
print(f"✅ Skills: {', '.join(alice.skills)}")
print("\n🎉 Everything is working!")
EOF
```

## Common Issues & Solutions

### Issue: `zsh: command not found: python`
**Solution:** On Mac, use `python3` instead of `python`

### Issue: `source: no such file or directory: venv/bin/activate`
**Solution:** The venv doesn't exist. Run step 3 first to create it.

### Issue: `ModuleNotFoundError: No module named 'networking_ai'`
**Solution:**
1. Make sure venv is activated (you should see `(venv)` in your prompt)
2. Run `pip install -e .` again
3. Verify with `pip list | grep networking-ai`

### Issue: Installation takes too long
**Solution:** This is normal! Installing PyTorch and ML dependencies can take 5-10 minutes on the first install.

### Issue: Permission denied
**Solution:** Don't use `sudo`. Always install within the activated venv.

## Alternative: Using the setup script

```bash
chmod +x setup.sh
./setup.sh
```

This script automates all the steps above.

## Next Steps

Once installed:

1. **Run tests** (requires dev dependencies):
   ```bash
   pip install -e ".[dev]"
   pytest
   ```

2. **Try the examples**:
   ```bash
   python3 examples/basic_usage.py
   ```

3. **Read the full README**:
   ```bash
   cat README.md
   ```

## Useful Commands

```bash
# Activate venv (do this every time you open a new terminal)
source venv/bin/activate

# Deactivate venv
deactivate

# Check installed packages
pip list

# Update package after code changes
pip install -e . --no-deps

# Run Python with venv
python  # (will use venv's Python)
```

## Still Having Issues?

If you're still having trouble:

1. Make sure you're in the `networking-ai` directory
2. Make sure Python 3.9+ is installed: `python3 --version`
3. Delete `venv` and start fresh from step 2
4. Check that you can import basic packages: `python3 -c "import sys; print(sys.version)"`

## Contact

For more help, see the main README.md or open an issue on GitHub.
