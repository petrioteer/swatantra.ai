"""
Entry point for Vercel deployment.

This file creates the Flask application and exposes it as the 'app' variable
which Vercel will use as the WSGI application.
"""
from api.app import create_app

# Create the Flask application
app = create_app()

# This will be used by Vercel as the WSGI application
if __name__ == "__main__":
    # Start the app if run directly (for development)
    app.run(host="0.0.0.0", port=5000, debug=True)