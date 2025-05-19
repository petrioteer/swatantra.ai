"""
Entry point for Vercel deployment.

This file creates the Flask application and exposes it as the 'app' variable
which Vercel will use as the WSGI application.
"""
# Fix asyncio incompatibility in Vercel environment
import sys
import os

# Create a patched sys.modules['asyncio'] before anything tries to import it
if 'VERCEL' in os.environ or 'AWS_LAMBDA_FUNCTION_NAME' in os.environ:
    # This is a minimal implementation to avoid the problematic import
    class DummyAsyncIO:
        def __getattr__(self, name):
            if name == 'async':
                # Return a replacement for the 'async' function
                return lambda *args, **kwargs: None
            raise AttributeError(f"Module 'asyncio' has no attribute '{name}'")
    
    # Only patch if asyncio is not already imported
    if 'asyncio' not in sys.modules:
        # Set a special flag to indicate we're in Vercel
        os.environ['VERCEL_ASYNCIO_PATCHED'] = '1'
        print("Patching asyncio for Vercel compatibility")
        
        # Create a mock of the asyncio module to prevent the actual import
        # This will be used for the specific problematic import
        sys.modules['asyncio'] = DummyAsyncIO()

# Proceed with normal imports
# The app module needs to check VERCEL_ASYNCIO_PATCHED and handle accordingly
from api.app import create_app

# Create the Flask application
app = create_app()

# This will be used by Vercel as the WSGI application
if __name__ == "__main__":
    # Start the app if run directly (for development)
    app.run(host="0.0.0.0", port=5000, debug=True)