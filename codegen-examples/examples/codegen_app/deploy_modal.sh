#!/bin/bash
# Script to deploy the codegen_app to Modal with proper environment setup

# Set up environment variables
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Print Python path for debugging
echo "Python path: $PYTHONPATH"

# Make sure codegen is importable
if python -c "import codegen" &> /dev/null; then
    echo "✅ codegen package is importable"
else
    echo "❌ codegen package is not importable"
    echo "Please install codegen: pip install git+https://github.com/codegen-sh/codegen-sdk.git@6a0e101718c247c01399c60b7abf301278a41786"
    exit 1
fi

# Deploy with Modal
cd "$SCRIPT_DIR"
modal deploy app.py

echo "Deployment completed!"