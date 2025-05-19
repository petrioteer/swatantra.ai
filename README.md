# Gem Voice API

A voice interface to interact with Gemini AI using Flask, deployed on Vercel.

## Project Structure

```
gem-voice-API/
│
├── api/                  # Main API package
│   ├── __init__.py
│   ├── app.py            # Flask application creation
│   ├── api/              # API routes
│   │   ├── __init__.py
│   │   └── routes.py     # API endpoints
│   ├── audio/            # Audio processing
│   │   ├── __init__.py
│   │   └── processor.py  # Audio processing logic
│   └── config/           # Configuration
│       ├── __init__.py
│       ├── gemini_config.py  # Gemini API configuration
│       └── settings.py   # General settings
│
├── index.py              # Entry point for Vercel
├── vercel.json           # Vercel configuration
├── requirements.txt      # Python dependencies
├── build_files.sh        # Build script for Vercel
└── .env                  # Environment variables
```

## Local Development

1. Create a virtual environment and activate it:

```
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

2. Install dependencies:

```
pip install -r requirements.txt
```

3. Run the application:

```
python index.py
```

4. The API will be available at `http://localhost:5000`.

## API Endpoints

- `POST /start_voice`: Start voice interaction with Gemini AI
- `POST /terminate_voice`: Stop voice interaction with Gemini AI

## Deploying to Vercel

1. Install the Vercel CLI:

```
npm install -g vercel
```

2. Login to Vercel:

```
vercel login
```

3. Deploy the project:

```
vercel
```

4. Set environment variables in Vercel dashboard:
   - `GEMINI_API_KEY`: Your Gemini API key

5. For production deployment:

```
vercel --prod
```

## Notes for Vercel Deployment

- This API runs on serverless functions on Vercel
- Audio streaming features are disabled in serverless environments
- The API can still serve as a backend for web applications that handle audio on the client side

## Deployment Notes

### Vercel Serverless Environment Limitations

When deployed on Vercel, this API operates in a serverless environment with the following limitations:

1. **Audio Hardware Access:** Serverless functions cannot access local audio hardware (microphones/speakers), making real-time audio streaming impossible.

2. **PyAudio Dependency:** The PyAudio library used for audio capture and playback is intentionally not loaded in the Vercel environment.

3. **Connection Duration:** Serverless functions have execution time limits (typically 10-60 seconds), making long-running audio streams impractical.

4. **Audio Processing Behavior:** The API automatically detects when running in a serverless environment (`os.environ.get('VERCEL') == '1'`) and disables local audio capture/playback functionality.

### Production Implementation Recommendations

For production applications requiring voice interaction with Gemini AI, we recommend:

1. **Client-side Audio Capture:** Implement audio recording in the client application (web, mobile, or desktop).

2. **Audio Processing:** Process audio on the client side to the required format (PCM, MP3, etc.).

3. **API Integration:** Send the processed audio data to the API endpoints as complete files or chunks.

4. **Alternative Architectures:** For continuous real-time audio streaming applications, consider deploying this API on a traditional server environment that supports persistent connections and audio hardware access.

The API will continue to function on Vercel, but with the audio streaming capabilities limited to processing pre-recorded audio files sent through HTTP requests rather than real-time streaming from local hardware.

## License

This project is licensed under the MIT License.
