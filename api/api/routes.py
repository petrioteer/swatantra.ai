"""
API routes for the Gem Voice API.

This module defines the Flask routes for interacting with the Gemini AI voice service.
"""
import asyncio
import time
import json
import base64
from threading import Thread, Lock
from flask import jsonify, render_template_string, request, current_app
from logging import getLogger
import os

# Import the WebSocket handler
from flask_sock import Sock

# Get logger
logger = getLogger(__name__)

# Global audio loop instance
audio_loop = None
# Thread for running the audio loop
audio_thread = None
# Lock for thread-safe access to globals
session_lock = Lock()
# Set to store active WebSocket connections
ws_clients = set()

# HTML template for the home page
HOME_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dr. Swatantra AI Voice API</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Roboto+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-color: #4f46e5;
            --primary-hover: #4338ca;
            --secondary-color: #0ea5e9;
            --text-color: #1e293b;
            --text-light: #64748b;
            --bg-color: #ffffff;
            --bg-light: #f1f5f9;
            --border-color: #e2e8f0;
            --code-bg: #f8fafc;
            --endpoint-bg: #f0f9ff;
            --endpoint-border: #0ea5e9;
            --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Poppins', sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--bg-color);
            max-width: 1000px;
            margin: 0 auto;
            padding: 2rem;
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }

        .container {
            flex: 1;
        }

        header {
            margin-bottom: 3rem;
            text-align: center;
        }

        .logo {
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .logo svg {
            width: 40px;
            height: 40px;
            margin-right: 12px;
        }

        .tagline {
            color: var(--text-light);
            font-weight: 300;
            font-size: 1.1rem;
        }

        h1 {
            color: var(--primary-color);
            margin-bottom: 1rem;
        }

        h2 {
            color: var(--secondary-color);
            margin: 2rem 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--border-color);
        }

        h3 {
            margin: 1.5rem 0 0.75rem;
            color: var(--text-color);
        }

        p, li {
            color: var(--text-light);
            margin-bottom: 1rem;
        }

        pre {
            background: var(--code-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1.25rem;
            overflow: auto;
            margin: 1.5rem 0;
            box-shadow: var(--shadow);
        }

        code {
            font-family: 'Roboto Mono', monospace;
            font-size: 0.9rem;
        }

        .endpoint {
            background: var(--endpoint-bg);
            border-left: 6px solid var(--endpoint-border);
            padding: 1.5rem;
            margin: 1.5rem 0;
            border-radius: 8px;
            box-shadow: var(--shadow);
            transition: transform 0.2s ease;
        }

        .endpoint:hover {
            transform: translateY(-2px);
        }

        .endpoint-title {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
        }

        .method {
            font-weight: 600;
            background: var(--primary-color);
            color: white;
            padding: 0.3rem 0.75rem;
            border-radius: 6px;
            margin-right: 1rem;
            display: inline-block;
        }

        .url {
            font-family: 'Roboto Mono', monospace;
            font-weight: 500;
            font-size: 1rem;
        }

        .api-section {
            background: var(--bg-light);
            padding: 2rem;
            border-radius: 12px;
            margin: 2rem 0;
            box-shadow: var(--shadow);
        }

        .example-section {
            display: grid;
            grid-template-columns: 1fr;
            gap: 1.5rem;
            margin: 1.5rem 0;
        }

        @media (min-width: 768px) {
            .example-section {
                grid-template-columns: 1fr 1fr;
            }
        }

        .example-card {
            background: var(--bg-color);
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: var(--shadow);
        }

        .example-title {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
            color: var(--primary-color);
            font-weight: 600;
        }

        .example-title svg {
            width: 24px;
            height: 24px;
            margin-right: 8px;
        }

        .note-box {
            background-color: #fffbeb;
            border-left: 6px solid #f59e0b;
            padding: 1.25rem;
            border-radius: 8px;
            margin: 1.5rem 0;
        }

        .note-box h4 {
            display: flex;
            align-items: center;
            color: #b45309;
            margin-bottom: 0.75rem;
        }

        .note-box h4 svg {
            width: 20px;
            height: 20px;
            margin-right: 8px;
        }

        .note-box p {
            color: #92400e;
            margin-bottom: 0.25rem;
        }

        footer {
            margin-top: 3rem;
            border-top: 1px solid var(--border-color);
            padding-top: 1.5rem;
            text-align: center;
            font-size: 0.9rem;
            color: var(--text-light);
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M11 2.05v3.04c-3.89.49-6.95 3.85-6.95 7.91 0 1.95.7 3.73 1.86 5.12L3.83 20.2C1.44 18.31 0 15.3 0 12 0 5.82 4.72.59 10.67.06L11 2.05zM21.94 4.88C19.5 1.83 15.5 0 11.22 0c-.15 0-.3 0-.45.01l-.38 2c.18-.01.35-.01.53-.01 3.6 0 6.95 1.47 9.33 3.98l1.69-1.1zm-3.55 11.24L16.3 13.5c.45-1.12.7-2.34.7-3.62 0-5.28-4.22-9.56-9.5-9.56-.32 0-.63.02-.95.05L5.39 2.62C5.86 2.54 6.34 2.5 6.83 2.5c4.42 0 8.32 2.37 10.46 5.98l1.69-1.09C16.46 3.35 11.85 0 6.83 0 6.2 0 5.58.05 4.97.14L4.59 2.13C2 2.89 0 5.5 0 8.58v10.78c0 .22.03.44.08.65l1.92-1.25v-5.51c0-4.05 3.29-7.34 7.34-7.34.17 0 .35.01.52.02l.38-2c-.3-.02-.6-.02-.9-.02-3.46 0-6.5 1.82-8.23 4.54l1.37 1.37C3.87 6.41 6.18 4.53 9 4.53c4.05 0 7.34 3.29 7.34 7.34 0 4.05-3.29 7.34-7.34 7.34-1.1 0-2.16-.25-3.1-.68l-1.42 1.42c1.28.68 2.74 1.06 4.28 1.06 4.54 0 8.34-3.33 9.04-7.67l-1.37-1.37z" />
                </svg>
                Dr. Swatantra AI Voice API
            </div>
            <p class="tagline">Conversational AI interface powered by Gemini</p>
        </header>

        <main>
            <p>
                The Dr. Swatantra AI Voice API provides a voice interface to interact with 
                Gemini AI, enabling natural conversations with an advanced AI assistant specialized in
                medical information and health-related dialogue.
            </p>

            <h2>Getting Started</h2>
            <p>
                To integrate this API into your application, you'll need to make HTTP requests to the endpoints 
                documented below. The API follows RESTful principles and returns standard JSON responses.
            </p>

            <div class="api-section">
                <h2>API Endpoints</h2>
                
                <div class="endpoint">
                    <div class="endpoint-title">
                        <span class="method">POST</span>
                        <span class="url">{{ base_url }}/start_voice</span>
                    </div>
                    <p>Initiates a new voice interaction session with Dr. Swatantra AI.</p>
                    <h4>Response:</h4>
                    <pre><code>{
  "status": "started"
}</code></pre>
                </div>

                <div class="endpoint">
                    <div class="endpoint-title">
                        <span class="method">POST</span>
                        <span class="url">{{ base_url }}/terminate_voice</span>
                    </div>
                    <p>Terminates an active voice interaction session.</p>
                    <h4>Response:</h4>
                    <pre><code>{
  "status": "terminated"
}</code></pre>
                </div>
            </div>

            <h2>Integration Examples</h2>
            <div class="example-section">
                <div class="example-card">
                    <div class="example-title">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M3 3h18v18H3V3zm16.5 1.5h-15v15h15v-15z"/>
                            <path d="M10 10h4v4h-4z"/>
                        </svg>
                        JavaScript/Web Example
                    </div>
                    <pre><code>// Start a voice session
fetch('{{ base_url }}/start_voice', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => console.log(data));

// Terminate a voice session
fetch('{{ base_url }}/terminate_voice', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  }
})
.then(response => response.json())
.then(data => console.log(data));</code></pre>
                </div>

                <div class="example-card">
                    <div class="example-title">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
                        </svg>
                        Python Example
                    </div>
                    <pre><code>import requests

# Start a voice session
response = requests.post(
    '{{ base_url }}/start_voice'
)
print(response.json())

# Terminate a voice session
response = requests.post(
    '{{ base_url }}/terminate_voice'
)
print(response.json())</code></pre>
                </div>
            </div>

            <div class="note-box">
                <h4>
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                    </svg>
                    Deployment Notes
                </h4>
                <p>
                    <strong>Will this API work after hosting on Vercel?</strong> Yes, the API will function, but with some considerations:
                </p>
                <p>
                    Vercel's serverless functions have specific limitations that affect long-running audio streaming processes:
                </p>
                <ul style="margin-left: 1.5rem; color: #92400e;">
                    <li><strong>Execution timeout:</strong> Serverless functions on Vercel have a maximum execution time of 10 seconds in the free tier and up to 60 seconds in paid plans, which may interrupt long voice conversations.</li>
                    <li><strong>Connection limitations:</strong> Persistent WebSocket connections needed for real-time audio streaming are not fully supported in serverless environments.</li>
                    <li><strong>Stateless execution:</strong> Each API call runs in an isolated environment, making it challenging to maintain audio session state between requests.</li>
                </ul>
                <p>
                    <strong>Recommended solution:</strong> For production applications, implement a hybrid architecture:
                </p>
                <ul style="margin-left: 1.5rem; color: #92400e;">
                    <li>Handle audio capture, processing, and buffering on the client side (browser or mobile app)</li>
                    <li>Send complete audio segments to the API as discrete requests</li>
                    <li>Process responses asynchronously to create a seamless experience</li>
                    <li>For high-volume applications, consider deploying the API to a platform supporting long-lived processes, such as a dedicated server or container-based service</li>
                </ul>
            </div>

        </main>
    </div>

    <footer>
        Copyright &copy; 2025 | All rights reserved.
        <p> Made with ❤️ by petrioteer </p>
    </footer>
</body>
</html>
"""

# Helper function to run async functions in the correct event loop
def run_async_task(coro_func, *args, **kwargs):
    """
    Run an async function in a new event loop safely.
    
    Args:
        coro_func: Coroutine function to run
        *args: Arguments to pass to the coroutine function
        **kwargs: Keyword arguments to pass to the coroutine function
        
    Returns:
        Result of the coroutine function
    """
    try:
        # Create a new event loop for this task
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro_func(*args, **kwargs))
    finally:
        loop.close()

def register_routes(app):
    """
    Register routes for the Flask application.
    
    Args:
        app: Flask application instance
    """
    # Initialize Flask-Sock for WebSocket support
    sock = Sock(app)
    
    @app.route('/')
    def home():
        """Home page with API documentation."""
        # Get the base URL from the request
        if request.headers.get('X-Forwarded-Host'):
            # For Vercel and other proxy setups
            proto = request.headers.get('X-Forwarded-Proto', 'https')
            host = request.headers.get('X-Forwarded-Host')
            base_url = f"{proto}://{host}"
        else:
            # For local development
            base_url = f"{request.scheme}://{request.host}"
            
        return render_template_string(
            HOME_PAGE_TEMPLATE,
            base_url=base_url
        )
    
    @sock.route('/audio-stream')
    def audio_stream_socket(ws):
        """
        WebSocket handler for audio streaming.
        
        This replaces the PyAudio approach to enable audio streaming in serverless environments.
        The client sends audio data to this WebSocket, which is then processed and sent to Gemini.
        Response audio data is sent back through the same WebSocket connection.
        
        Args:
            ws: WebSocket connection object
        """
        global audio_loop
        global ws_clients
        
        logger.info("New WebSocket client connected for audio streaming")
        
        # Add the WebSocket to our clients set
        ws_clients.add(ws)
        
        try:
            # Check if we have an active audio loop
            if not audio_loop or not audio_loop.is_running:
                logger.warning("Client connected but no active audio session. Starting one.")
                
                # Start an audio session if none exists
                if not audio_loop:
                    from api.app import create_audio_loop
                    audio_loop = create_audio_loop()
                    
                    # Start the audio loop in a new thread
                    audio_thread = Thread(
                        target=lambda: run_async_task(audio_loop.run, current_app.config['GEMINI_CONFIG']),
                        daemon=True
                    )
                    audio_thread.start()
            
            # Process WebSocket messages as long as the connection is open
            while True:
                # Wait for a message from the client
                message = ws.receive()
                
                # Process received message
                if message:
                    try:
                        # Try to parse as JSON first
                        data = json.loads(message)
                        
                        # Handle different message types
                        if data.get("type") == "audio":
                            # Decode base64 audio data
                            audio_bytes = base64.b64decode(data["data"])
                            
                            # If the audio loop is running, send the audio data to it
                            if audio_loop and audio_loop.is_running:
                                # Put this in the out_queue to be processed by the audio loop
                                asyncio.run(audio_loop.out_queue.put({
                                    "data": audio_bytes,
                                    "mime_type": data.get("format", "audio/pcm")
                                }))
                        
                        elif data.get("type") == "control":
                            # Handle control messages (start, stop, etc.)
                            if data.get("command") == "stop":
                                logger.info("Client requested audio session stop")
                                if audio_loop:
                                    asyncio.run(audio_loop.stop())
                            elif data.get("command") == "start":
                                logger.info("Client requested audio session start")
                                # Audio session is started when the WebSocket is connected
                                
                    except json.JSONDecodeError:
                        # If not JSON, treat as raw audio data
                        if audio_loop and audio_loop.is_running:
                            asyncio.run(audio_loop.out_queue.put({
                                "data": message,
                                "mime_type": "audio/pcm"  # Assume default format
                            }))
                
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
        finally:
            # Remove the WebSocket from the clients set when the connection closes
            if ws in ws_clients:
                ws_clients.remove(ws)
            logger.info("WebSocket client disconnected")
    
    @app.route('/start_voice', methods=['POST', 'OPTIONS'])
    def start_voice():
        """Start voice interaction with Gemini AI."""
        global audio_loop
        global audio_thread
        
        with session_lock:
            # If there's an existing session, terminate it first
            if audio_loop:
                try:
                    run_async_task(audio_loop.stop)
                    logger.info("Existing voice session terminated before starting new one")
                    
                    # Wait for the thread to finish
                    if audio_thread and audio_thread.is_alive():
                        audio_thread.join(timeout=2.0)
                        
                except Exception as e:
                    logger.error(f"Error terminating existing voice service: {str(e)}")
                finally:
                    # Force cleanup of resources
                    audio_loop = None
                    audio_thread = None
                    # Small delay to ensure clean startup
                    time.sleep(0.5)
            
            # Import here to avoid circular imports
            from api.app import create_audio_loop
            
            try:
                # Create a new audio loop
                audio_loop = create_audio_loop()
                
                # Start the audio loop in a new thread
                audio_thread = Thread(
                    target=lambda: run_async_task(audio_loop.run, app.config['GEMINI_CONFIG']),
                    daemon=True
                )
                audio_thread.start()
                
                logger.info("Voice session started")
                
                # Return WebSocket info in the response
                return jsonify({
                    "status": "started",
                    "websocket": {
                        "url": f"wss://{request.host}/audio-stream" if request.is_secure else f"ws://{request.host}/audio-stream",
                        "protocol": "audio-stream"
                    }
                })
            except Exception as e:
                logger.error(f"Error starting voice service: {str(e)}")
                return jsonify({"status": "error", "message": str(e)})

    @app.route('/terminate_voice', methods=['POST', 'OPTIONS'])
    def terminate_voice():
        """Completely stop the voice interaction and clean up resources."""
        global audio_loop
        global audio_thread
        global ws_clients
        
        with session_lock:
            if audio_loop:
                try:
                    # Stop the audio loop
                    run_async_task(audio_loop.stop)
                    logger.info("Voice session terminated")
                    
                    # Wait for the thread to finish
                    if audio_thread and audio_thread.is_alive():
                        audio_thread.join(timeout=2.0)
                        
                    # Close any active WebSocket connections
                    for ws in list(ws_clients):
                        try:
                            ws.close()
                        except:
                            pass
                    ws_clients.clear()
                        
                except Exception as e:
                    logger.error(f"Error terminating voice service: {str(e)}")
                finally:
                    # Clean up resources
                    audio_loop = None
                    audio_thread = None
            
        return jsonify({"status": "terminated"})

    @app.route('/get_transcription')
    def get_transcription():
        """Get transcription from Gemini AI (currently disabled)."""
        # Disabled transcription endpoint
        return jsonify({"transcription": None})
        
    return app