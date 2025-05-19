"""
Configuration settings for the Gem Voice API.
"""
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Audio settings (keeping constants for compatibility)
FORMAT = 16  # 16-bit PCM, equivalent to PyAudio's paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

# WebSocket settings
WEBSOCKET_HOST = "0.0.0.0"  # Bind to all interfaces
WEBSOCKET_PORT = 8765
WEBSOCKET_PATH = "/audio-stream"

# API connection settings
MAX_RETRIES = 3
RETRY_DELAY = 2
CONNECTION_TIMEOUT = 30

# Gemini API settings
MODEL = "models/gemini-2.0-flash-live-001"
# Use environment variable for API key (Vercel-friendly)
API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyDsACSu8MTEXfegE5XCZV0sJT3m_nbRo60")

# Flask settings
PORT = int(os.environ.get("PORT", 5000))