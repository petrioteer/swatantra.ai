"""
Main application module for the Gem Voice API.

This module initializes the Flask application and Gemini client,
and provides functions to create and manage the application.
"""
import os
from flask import Flask
from flask_cors import CORS
from google import genai  # Fixed import to match working implementation

from api.api.routes import register_routes
from api.audio.processor import AudioLoop
from api.config.settings import CONNECTION_TIMEOUT, API_KEY, PORT
from api.config.gemini_config import get_live_connect_config


def create_gemini_client():
    """
    Create and configure the Gemini API client.
    
    Returns:
        genai.Client: Configured Gemini client
    """
    return genai.Client(
        http_options={
            "api_version": "v1beta",
            "timeout": CONNECTION_TIMEOUT,
        },
        api_key=API_KEY,
    )


def create_audio_loop():
    """
    Create a new AudioLoop instance with the Gemini client.
    
    Returns:
        AudioLoop: Configured AudioLoop instance
    """
    client = create_gemini_client()
    return AudioLoop(client)


def create_app():
    """
    Create and configure the Flask application.
    
    Returns:
        Flask: Configured Flask application
    """
    # Create Flask app
    app = Flask(__name__)
    
    # Enable CORS with proper configuration for all routes
    CORS(app, resources={r"/*": {"origins": "*", "supports_credentials": True}})
    
    # Store the Gemini configuration in app config
    app.config['GEMINI_CONFIG'] = get_live_connect_config()
    
    # Register routes
    register_routes(app)
    
    return app


def run_app(host='0.0.0.0', port=PORT, debug=False):
    """
    Run the Flask application.
    
    Args:
        host (str): Host to bind the server to
        port (int): Port to bind the server to
        debug (bool): Run app in debug mode if True
    """
    app = create_app()
    app.run(host=host, port=port, debug=debug)