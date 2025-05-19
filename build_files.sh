#!/bin/bash
# This script is used by Vercel to install system-level dependencies

echo "Installing system-level dependencies..."
apt-get update
apt-get install -y python3-dev

# Exit on error
set -e

# Install dependencies from requirements.txt
pip install -r requirements.txt

# Create a directory for the vercel runtime
mkdir -p .vercel/python

# Print confirmation message
echo "Build script completed successfully"