#!/usr/bin/env python
"""
Main entry point for the Gem Voice API application.

This script initializes and runs the Flask application with the Gem Voice API.
"""
import argparse
import asyncio
import threading
from gem_voice_api.app import create_app, run_app, create_audio_loop


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Gem Voice API - Voice interface to Gemini AI')
    parser.add_argument('--cli', action='store_true', help='Run with CLI mode (starts audio loop directly)')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--host', default='0.0.0.0', help='Host to run the server on')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the server on')
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    
    if args.cli:
        # Run in CLI mode with audio loop directly
        print("Starting Gem Voice API in CLI mode...")
        audio_loop = create_audio_loop()
        
        # Create Gemini config
        app = create_app()
        gemini_config = app.config['GEMINI_CONFIG']
        
        # Start the audio loop
        asyncio.run(audio_loop.run(gemini_config))
    else:
        # Run as Flask web server
        print(f"Starting Gem Voice API server on {args.host}:{args.port}...")
        run_app(host=args.host, port=args.port, debug=args.debug)