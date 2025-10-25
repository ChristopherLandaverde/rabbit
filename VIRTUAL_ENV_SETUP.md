# Virtual Environment Setup Guide

## Problem
If you're getting permission errors or being asked for `sudo` privileges when installing Python packages, it means you're trying to install packages into the system-wide Python installation. This is **not recommended** and can cause system conflicts.

## Solution: Use a Virtual Environment

A virtual environment creates an isolated Python environment for your project, allowing you to install packages without needing `sudo` privileges.

## Quick Setup

### Option 1: Using the Setup Script (Recommended)

```bash
# Run the automated setup script
./setup_venv.sh

# Activate the virtual environment
source venv/bin/activate
```

### Option 2: Manual Setup

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Linux/Mac
# OR
.\venv\Scripts\activate  # On Windows
```

## Installing Dependencies

Once your virtual environment is activated (you should see `(venv)` in your terminal prompt):

```bash
# For minimal dependencies
pip install -r requirements-minimal.txt

# For full dependencies (recommended)
pip install -r requirements.txt
```

**Note**: With the virtual environment activated, you will **NOT** need `sudo` privileges to install packages.

## Using the Virtual Environment

### Activating
```bash
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate   # Windows
```

### Deactivating
```bash
deactivate
```

### Checking if Activated
You should see `(venv)` at the beginning of your terminal prompt when the virtual environment is active.

## Verification

To verify everything is working:

```bash
# Activate the virtual environment
source venv/bin/activate

# Check which Python and pip are being used
which python  # Should point to venv/bin/python
which pip     # Should point to venv/bin/pip

# Verify installation
python test_setup.py
```

## Troubleshooting

### Issue: "Permission denied" when creating venv
**Solution**: Make sure you have write permissions in the project directory. You shouldn't need `sudo` to create a virtual environment.

### Issue: Still getting permission errors
**Solution**: Make sure you've activated the virtual environment. Check for `(venv)` in your terminal prompt.

### Issue: Packages not found after installation
**Solution**: Ensure the virtual environment is activated before running your Python scripts.

## Pro Tips

1. **Always activate the virtual environment** before working on the project
2. **Add `venv/` to `.gitignore`** (already done) - never commit the virtual environment
3. **Use `requirements.txt`** to document dependencies
4. **Recreate the virtual environment** if you encounter issues: `rm -rf venv && python3 -m venv venv`

## VS Code Integration

If you're using VS Code, it should automatically detect and use the virtual environment. You can also manually select it:

1. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
2. Type "Python: Select Interpreter"
3. Choose the interpreter from `./venv/bin/python`
