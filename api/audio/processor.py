"""
Audio processing module for the Gem Voice API.

This module provides classes and functions for processing audio data
and communicating with the Gemini API.
"""
import asyncio
import time
import base64
import traceback
import concurrent.futures
from logging import getLogger
import os
import json
from typing import Dict, Any, Optional, Set, List

# WebSockets imports instead of PyAudio
import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

# Proper Gemini API imports
from google import genai
try:
    from google.genai import types
    GEMINI_TYPES_AVAILABLE = True
except ImportError:
    GEMINI_TYPES_AVAILABLE = False

# We no longer use PyAudio - WebSockets will handle the audio streaming
WEBSOCKET_AVAILABLE = True
try:
    import websockets
except ImportError:
    WEBSOCKET_AVAILABLE = False

from api.config.settings import (
    FORMAT, CHANNELS, SEND_SAMPLE_RATE, RECEIVE_SAMPLE_RATE, 
    CHUNK_SIZE, MAX_RETRIES, RETRY_DELAY, CONNECTION_TIMEOUT,
    MODEL
)

# Get logger
logger = getLogger(__name__)

# Helper function for Python 3.10 compatibility (asyncio.to_thread alternative)
async def run_in_thread(func, *args, **kwargs):
    """Run a function in a separate thread and await its result."""
    loop = asyncio.get_event_loop()
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, lambda: func(*args, **kwargs))

class AudioLoop:
    """
    Handles real-time audio streaming with the Gemini API.
    
    This class manages sending audio data to the Gemini API and 
    receiving responses, handling the two-way communication.
    """
    
    def __init__(self, client):
        """
        Initialize the AudioLoop with a Gemini client.
        
        Args:
            client: The Gemini API client
        """
        self.client = client
        self.session = None
        self.is_running = False
        self.audio_in_queue = asyncio.Queue()
        self.out_queue = asyncio.Queue()
        self._processing_task = None
        
        # Check if we're running in a serverless environment
        self.is_serverless = os.environ.get('VERCEL') == '1'

    async def connect_with_retry(self, config: Dict[str, Any], max_retries: int = 3) -> bool:
        """
        Attempt to connect to the Gemini API with retries.
        
        Args:
            config: Configuration for the Gemini API session
            max_retries: Maximum number of connection attempts
            
        Returns:
            bool: True if connection was successful, False otherwise
        """
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"Connecting to Gemini API (attempt {retry_count + 1})")
                
                # Use the live.connect approach from gem-voice.py
                # Store the context manager
                self._session_ctx = self.client.aio.live.connect(
                    model=config["model"],
                    config=config["live_connect_config"]
                )
                
                # Enter the context
                self.session = await self._session_ctx.__aenter__()
                self.is_running = True
                
                logger.info("Successfully connected to Gemini API")
                return True
                
            except Exception as e:
                logger.error(f"Connection attempt {retry_count + 1} failed: {str(e)}")
                retry_count += 1
                await asyncio.sleep(1)  # Wait before retrying
        
        logger.error("Failed to connect to Gemini API after maximum retries")
        return False
    
    async def stop(self):
        """Stop all audio processing and close connections."""
        logger.info("Stopping audio processing")
        self.is_running = False
        
        # Give tasks time to notice the running flag change
        await asyncio.sleep(0.5)
        
        if hasattr(self, '_session_ctx') and self._session_ctx and self.session:
            try:
                logger.info("Closing Gemini API session")
                # Use the context manager exit method to properly close the session
                await self._session_ctx.__aexit__(None, None, None)
                logger.info("Gemini API session closed successfully")
            except Exception as e:
                logger.error(f"Error closing session: {str(e)}")
            finally:
                self.session = None
                self._session_ctx = None

        self._clear_queues()
        logger.info("Audio processing stopped completely")

    def _clear_queues(self):
        """Clear any pending items from queues."""
        for queue in [self.audio_in_queue, self.out_queue]:
            if queue:
                while not queue.empty():
                    try:
                        queue.get_nowait()
                    except:
                        pass

    async def send_realtime(self):
        """
        Send audio data from the out_queue to the Gemini API in real-time.
        """
        try:
            if not self.session or not self.is_running:
                raise ValueError("Session not initialized or not running")
            
            while self.is_running:
                if not self.out_queue.empty():
                    content = await self.out_queue.get()
                    
                    if content:
                        # Send the audio content to the Gemini API using the proper method
                        await self.session.send(input=content)
                
                await asyncio.sleep(0.01)  # Small sleep to prevent CPU hogging
                
        except Exception as e:
            logger.error(f"Error in send_realtime: {str(e)}")
            self.is_running = False

    async def receive_audio(self):
        """
        Receive audio responses from the Gemini API and put them in the audio_in_queue.
        """
        try:
            if not self.session or not self.is_running:
                raise ValueError("Session not initialized or not running")
            
            # Continuously receive responses while the loop is running
            while self.is_running:
                try:
                    # Use the turn-based approach from gem-voice.py
                    turn = self.session.receive()
                    async for response in turn:
                        if data := response.data:
                            await self.audio_in_queue.put(data)
                except asyncio.CancelledError:
                    logger.info("Receive audio operation cancelled")
                    break
                except Exception as e:
                    logger.error(f"Error receiving audio response: {str(e)}")
                    if "timeout" in str(e).lower():
                        await asyncio.sleep(1)  # Brief pause before retry
                        continue
                    break
                
                await asyncio.sleep(0.01)  # Small sleep to prevent CPU hogging
                
        except Exception as e:
            logger.error(f"Error in receive_audio: {str(e)}")
            self.is_running = False

    async def listen_audio(self):
        """
        Process audio input from WebSocket clients.
        
        Note: We don't need to actively listen here anymore since we're getting
        audio data from the Flask-Sock WebSocket connections in routes.py.
        This method now just exists for compatibility with the run method.
        """
        # In serverless mode or without WebSockets, just return
        if self.is_serverless or not WEBSOCKET_AVAILABLE:
            logger.info("Audio capture handled via WebSocket connections in routes.py")
            return
            
        try:
            # Keep the method running while the audio loop is active
            while self.is_running:
                # Audio data is now being passed to self.out_queue directly by the routes.py WebSocket handler
                await asyncio.sleep(0.5)  # Just sleep to keep the task alive
                
        except asyncio.CancelledError:
            logger.info("Listen audio task cancelled")
        except Exception as e:
            logger.error(f"Error in listen_audio: {str(e)}")
            # Don't stop the whole loop for errors here

    async def send_text(self):
        """Send text input from console to Gemini API."""
        while self.is_running:
            try:
                text = await run_in_thread(input, "message > ")
                if text.lower() == "q":
                    break
                await self.session.send(input=text or ".", end_of_turn=True)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in send_text: {str(e)}")
                if "timeout" in str(e).lower():
                    await asyncio.sleep(1)  # Brief pause before retry
                    continue
                break

    async def pause(self):
        """Pause audio processing without closing the connection."""
        logger.info("Pausing audio processing")
        self.paused = True
        self._pause_event.set()
        
        return True
        
    async def resume(self):
        """Resume audio processing."""
        logger.info("Resuming audio processing")
        self.paused = False
        self._pause_event.clear()

    async def play_audio(self):
        """
        Stream audio responses from the audio_in_queue to connected WebSocket clients.
        This replaces the previous PyAudio playback with WebSocket streaming.
        """
        try:
            if not WEBSOCKET_AVAILABLE:
                logger.info("WebSockets not available for audio playback")
                return

            logger.info("Starting audio playback via WebSockets")
            
            # Get access to active WebSocket clients from the routes module
            from api.api.routes import ws_clients
            
            while self.is_running:
                if not self.audio_in_queue.empty():
                    audio_data = await self.audio_in_queue.get()
                    
                    if audio_data and ws_clients:
                        try:
                            # Add WAV header to the raw audio data to make it decodable by Web Audio API
                            # This is needed because the Web Audio API expects a valid audio file format
                            sample_rate = RECEIVE_SAMPLE_RATE  # 24000 Hz as defined in settings
                            channels = 1  # Mono
                            sample_width = 2  # 16-bit audio
                            
                            # Create WAV header
                            wav_header = create_wav_header(
                                len(audio_data), 
                                sample_rate=sample_rate,
                                channels=channels, 
                                sample_width=sample_width
                            )
                            
                            # Combine header with audio data
                            wav_data = wav_header + audio_data
                            
                            # Send the audio data to all connected clients in Base64 format
                            encoded_audio = base64.b64encode(wav_data).decode('utf-8')
                            message = json.dumps({
                                "type": "audio",
                                "format": "audio/wav",
                                "data": encoded_audio
                            })
                            
                            # Create a list to track disconnected clients
                            disconnected = []
                            
                            # Send to all connected clients
                            for ws in list(ws_clients):
                                try:
                                    ws.send(message)
                                except Exception as e:
                                    logger.error(f"Error sending audio to client: {str(e)}")
                                    disconnected.append(ws)
                        
                        except Exception as e:
                            logger.error(f"Error preparing audio data for clients: {str(e)}")
                
                await asyncio.sleep(0.01)  # Small sleep to prevent CPU hogging
                
        except Exception as e:
            logger.error(f"Error in play_audio: {str(e)}")
            logger.error(traceback.format_exc())

    async def run(self, config):
        """
        Start the main audio processing loop.
        
        Args:
            config: Gemini API configuration object
        """
        self._loop = asyncio.get_event_loop()
        self._stop_event = asyncio.Event()  # Create the stop event
        
        try:
            await self.connect_with_retry(config)
            if not self.session:
                raise Exception("Failed to establish session")

            # Create and gather tasks instead of using TaskGroup (Python 3.11+ feature)
            tasks = [
                asyncio.create_task(self.send_realtime()),
                asyncio.create_task(self.listen_audio()),
                asyncio.create_task(self.receive_audio()),
                asyncio.create_task(self.play_audio()),
                asyncio.create_task(self.send_text())
            ]
            
            # Wait for stop signal
            await self._stop_event.wait()
            
            # Cancel all tasks when done
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks, return_exceptions=True)

        except Exception as e:
            # Standard exception handling instead of exception groups (Python 3.11+ feature)
            logger.error(f"Error in run: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            self.is_running = False
            await self.stop()

# Helper function to create a WAV header
def create_wav_header(data_length, sample_rate=24000, channels=1, sample_width=2):
    """
    Create a WAV header for raw audio data.
    
    Args:
        data_length (int): Length of the audio data in bytes
        sample_rate (int): Sample rate of the audio in Hz
        channels (int): Number of audio channels (1 for mono, 2 for stereo)
        sample_width (int): Sample width in bytes (2 for 16-bit audio)
        
    Returns:
        bytes: WAV header data
    """
    # RIFF header
    header = bytearray()
    header.extend(b'RIFF')
    header.extend((data_length + 36).to_bytes(4, 'little'))  # 36 + data_length
    header.extend(b'WAVE')
    
    # fmt chunk
    header.extend(b'fmt ')
    header.extend((16).to_bytes(4, 'little'))  # Chunk size: 16 for PCM
    header.extend((1).to_bytes(2, 'little'))   # Audio format: 1 for PCM
    header.extend(channels.to_bytes(2, 'little'))  # Channels
    header.extend(sample_rate.to_bytes(4, 'little'))  # Sample rate
    
    # Byte rate: SampleRate * NumChannels * BitsPerSample/8
    byte_rate = sample_rate * channels * sample_width
    header.extend(byte_rate.to_bytes(4, 'little'))
    
    # Block align: NumChannels * BitsPerSample/8
    block_align = channels * sample_width
    header.extend(block_align.to_bytes(2, 'little'))
    
    # Bits per sample
    bits_per_sample = sample_width * 8
    header.extend(bits_per_sample.to_bytes(2, 'little'))
    
    # Data chunk
    header.extend(b'data')
    header.extend(data_length.to_bytes(4, 'little'))
    
    return header