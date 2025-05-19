#!/bin/bash
# This script is used by Vercel to install system-level dependencies

echo "Installing system-level dependencies..."
apt-get update
apt-get install -y python3-dev

echo "Building completed"