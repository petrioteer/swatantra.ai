"""
Entry point for Vercel deployment.

This file creates the Flask application and exposes it as the 'app' variable
which Vercel will use as the WSGI application.
"""
# Handle asyncio compatibility for Vercel environment
import sys
import os

# Add a version check to handle the asyncio compatibility issue
if sys.version_info < (3, 7):
    # Use a backport of asyncio for older Python versions
    os.environ["PYTHONPATH"] = os.getcwd()
    # Add warning about Python version
    print(f"Warning: Running with Python {sys.version}, which may have asyncio compatibility issues")

# Now it's safe to import the app
from api.app import create_app

# Create the Flask application
app = create_app()

# This will be used by Vercel as the WSGI application
if __name__ == "__main__":
    # Start the app if run directly (for development)
    app.run(host="0.0.0.0", port=5000, debug=True)