# Gem Voice API

A streamlined API for real-time voice interaction with Google's Gemini AI, built with Flask and WebSockets.

## Overview

Gem Voice API provides a simple interface to enable voice conversations with Google's Gemini AI models. It handles real-time audio streaming through WebSockets, allowing for natural voice interaction with Dr. Swatantra AI, a virtual wellness guide.

## Key Features

- **Real-time Voice Conversations**: Two-way voice communication with Gemini AI
- **WebSocket Audio Streaming**: Low-latency audio transmission
- **WAV Audio Format**: High-quality audio responses
- **Flask-based REST API**: Simple endpoints for session management
- **Cross-Origin Support**: Works with web clients from any domain
- **Customized AI Persona**: Configured as Dr. Swatantra AI, a wellness guide

## API Endpoints

- **Home**: `GET /` - Documentation page with API information
- **Start Voice**: `POST /start_voice` - Initiates a voice session and returns WebSocket connection details
- **Terminate Voice**: `POST /terminate_voice` - Ends an active voice session
- **Status**: `GET /status` - Returns API status information
- **WebSocket**: `WS /audio-stream` - WebSocket endpoint for audio streaming

## WebSocket Protocol

The WebSocket connection supports the following message types:

### Client to Server

```json
{
  "type": "audio",
  "format": "audio/pcm",
  "data": "<base64-encoded audio data>"
}
```

### Server to Client

```json
{
  "type": "audio",
  "format": "audio/wav",
  "data": "<base64-encoded WAV audio>"
}
```

## Requirements

- Python 3.8+
- Flask and Flask-CORS
- Flask-Sock for WebSocket support
- Google Generative AI Python SDK
- Valid Google Gemini API key

## Installation

1. Clone the repository:

   ```
   git clone <repository-url>
   cd gem-voice-API
   ```

2. Create a virtual environment and activate it:

   ```
   python -m venv test
   # On Windows
   test\Scripts\activate
   # On macOS/Linux
   source test/bin/activate
   ```

3. Install dependencies:

   ```
   pip install -r requirements.txt
   ```

4. Set up your Gemini API key:

   ```
   # Windows
   set GEMINI_API_KEY=your_api_key_here
   
   # macOS/Linux
   export GEMINI_API_KEY=your_api_key_here
   ```

## Usage

1. Start the server:

   ```
   python app.py
   ```

2. The API will be available at `http://localhost:5000`

3. To start a voice conversation:
   - Send a POST request to `/start_voice`
   - Connect to the returned WebSocket URL
   - Send audio data through the WebSocket
   - Receive audio responses through the same WebSocket

4. To end a conversation:
   - Send a POST request to `/terminate_voice`

## Serverless Deployment Notes

When deployed to serverless environments like Vercel, this API has the following limitations:

1. **Execution Time Limits**: Serverless functions typically have a 10-second execution timeout, which limits continuous WebSocket connections.

2. **WebSocket Support**: While the API can establish WebSocket connections in serverless environments, they may be closed after the timeout period.

3. **Recommended Deployment**: For production use with continuous voice interaction, deploy to a platform that supports persistent connections (traditional server, container service, etc.).

## Configuration

Key configuration settings in the API:

- **Audio Format**: 16-bit PCM mono audio
- **Input Sample Rate**: 16kHz
- **Output Sample Rate**: 24kHz
- **AI Model**: Gemini-2.0-flash-live-001
- **Connection Timeout**: 30 seconds
- **Voice**: Puck (configurable)

## Example Client Implementation

A simple client implementation using JavaScript:

```html
<script>
  // Start a voice session
  async function startVoiceSession() {
    const response = await fetch('/start_voice', { method: 'POST' });
    const data = await response.json();
    
    // Connect to WebSocket
    const ws = new WebSocket(data.websocket.url);
    
    ws.onopen = () => {
      // Start capturing audio from microphone and sending it
      // Implementation depends on browser APIs
    };
    
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'audio') {
        // Play the received audio
        const audio = new Audio('data:audio/wav;base64,' + message.data);
        audio.play();
      }
    };
  }
  
  // End a voice session
  async function endVoiceSession() {
    await fetch('/terminate_voice', { method: 'POST' });
  }
</script>
```

## License

This project is licensed under the MIT License.
