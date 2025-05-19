"""
Audio processor for handling streaming audio to and from Gemini API.
"""
import asyncio
import traceback
import concurrent.futures
from logging import getLogger
import os

# Conditionally import PyAudio - it won't be available in Vercel's serverless environment
try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
    # Create a global PyAudio instance to be shared
    pya = pyaudio.PyAudio()
except ImportError:
    PYAUDIO_AVAILABLE = False
    pya = None

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
    Handles bidirectional audio streaming between user and Gemini API.
    """
    def __init__(self, client):
        """
        Initialize the AudioLoop with the Gemini client.
        
        Args:
            client: Initialized Gemini API client
        """
        self.client = client
        self.audio_in_queue = None
        self.out_queue = None
        self.session = None
        self._session_ctx = None
        self.running = True
        self.paused = False
        self.audio_stream = None
        self._stop_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._loop = None
        self.retry_count = 0
        # Use the global PyAudio instance if available
        self.pya = pya
        
        # Check if we're running in a serverless environment
        self.is_serverless = os.environ.get('VERCEL') == '1'

    async def connect_with_retry(self, config):
        """
        Establish connection to Gemini API with retry mechanism.
        
        Args:
            config: Gemini API configuration object
            
        Raises:
            Exception: If connection fails after maximum retries
        """
        while self.retry_count < MAX_RETRIES:
            try:
                # Store the context manager
                self._session_ctx = self.client.aio.live.connect(model=MODEL, config=config)
                # Enter the context
                self.session = await self._session_ctx.__aenter__()
                logger.info("Successfully created Gemini API session")
                return
            except Exception as e:
                self.retry_count += 1
                logger.error(f"Connection attempt {self.retry_count} failed: {str(e)}")
                if self.retry_count < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.error("Max retries reached, giving up")
                    raise

    async def stop(self):
        """Stop all audio processing and close connections."""
        logger.info("Stopping audio processing")
        self.running = False
        self._stop_event.set()
        
        # Give tasks time to notice the running flag change
        await asyncio.sleep(0.5)
        
        if self.audio_stream and PYAUDIO_AVAILABLE and not self.is_serverless:
            try:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
                self.audio_stream = None
                logger.info("Audio stream closed successfully")
            except Exception as e:
                logger.error(f"Error stopping audio stream: {str(e)}")

        if self._session_ctx and self.session:
            try:
                logger.info("Closing Gemini API session")
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

    # Rest of the AudioLoop class methods...
    async def listen_audio(self):
        """Capture audio from microphone and send to the output queue."""
        # Skip audio capture in serverless environments
        if self.is_serverless or not PYAUDIO_AVAILABLE:
            logger.info("Audio capture not available in serverless environment")
            return
            
        try:
            mic_info = self.pya.get_default_input_device_info()
            self.audio_stream = await run_in_thread(
                self.pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=SEND_SAMPLE_RATE,
                input=True,
                input_device_index=mic_info["index"],
                frames_per_buffer=CHUNK_SIZE,
            )
            
            kwargs = {"exception_on_overflow": False} if __debug__ else {}
            
            while self.running:
                try:
                    data = await run_in_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
                    await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error reading audio: {str(e)}")
                    break
        except Exception as e:
            logger.error(f"Error in listen_audio: {str(e)}")
        finally:
            if self.audio_stream:
                self.audio_stream.close()

    async def receive_audio(self):
        """Receive audio response from Gemini API and queue it for playback."""
        while self.running and self.session:
            try:
                turn = self.session.receive()
                async for response in turn:
                    if data := response.data:
                        await self.audio_in_queue.put(data)
            except asyncio.CancelledError:
                logger.info("Receive audio operation cancelled")
                break
            except Exception as e:
                logger.error(f"Error in receive_audio: {str(e)}")
                if "timeout" in str(e).lower():
                    await asyncio.sleep(1)  # Brief pause before retry
                    continue
                break

    async def play_audio(self):
        """Play received audio through audio output device."""
        # Skip audio playback in serverless environments
        if self.is_serverless or not PYAUDIO_AVAILABLE:
            logger.info("Audio playback not available in serverless environment")
            return
            
        try:
            stream = await run_in_thread(
                self.pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=RECEIVE_SAMPLE_RATE,
                output=True,
            )
            while self.running:
                try:
                    bytestream = await self.audio_in_queue.get()
                    await run_in_thread(stream.write, bytestream)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error playing audio: {str(e)}")
        finally:
            if 'stream' in locals():
                stream.close()

    async def send_realtime(self):
        """Send audio data from the output queue to the Gemini API."""
        while self.running and self.session:
            try:
                msg = await self.out_queue.get()
                await self.session.send(input=msg)
            except asyncio.CancelledError:
                logger.info("Send realtime operation cancelled")
                break
            except Exception as e:
                logger.error(f"Error in send_realtime: {str(e)}")
                if "timeout" in str(e).lower():
                    await asyncio.sleep(1)  # Brief pause before retry
                    continue
                break

    async def send_text(self):
        """Send text input from console to Gemini API."""
        while self.running:
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
        
        # Pause the audio stream but don't close it
        if self.audio_stream and not self.audio_stream.is_stopped():
            try:
                self.audio_stream.stop_stream()
                logger.info("Audio stream paused successfully")
            except Exception as e:
                logger.error(f"Error pausing audio stream: {str(e)}")
                # Don't propagate the error, as we want to continue with pause operation
            
        return True
        
    async def resume(self):
        """Resume audio processing."""
        logger.info("Resuming audio processing")
        self.paused = False
        self._pause_event.clear()
        
        try:
            # Check if audio stream needs to be recreated
            if self.audio_stream is None or not hasattr(self.audio_stream, 'is_active'):
                logger.info("Creating new audio stream")
                mic_info = self.pya.get_default_input_device_info()
                self.audio_stream = await run_in_thread(
                    self.pya.open,
                    format=FORMAT,
                    channels=CHANNELS,
                    rate=SEND_SAMPLE_RATE,
                    input=True,
                    input_device_index=mic_info["index"],
                    frames_per_buffer=CHUNK_SIZE,
                )
            # Otherwise resume the existing stream if it's stopped
            elif self.audio_stream.is_stopped():
                try:
                    self.audio_stream.start_stream()
                    logger.info("Audio stream resumed successfully")
                except Exception as e:
                    logger.error(f"Error resuming audio stream: {str(e)}")
                    # If resuming fails, create a new stream
                    logger.info("Recreating audio stream after resume failure")
                    mic_info = self.pya.get_default_input_device_info()
                    self.audio_stream = await run_in_thread(
                        self.pya.open,
                        format=FORMAT,
                        channels=CHANNELS,
                        rate=SEND_SAMPLE_RATE,
                        input=True,
                        input_device_index=mic_info["index"],
                        frames_per_buffer=CHUNK_SIZE,
                    )
        except Exception as e:
            logger.error(f"Error during resume: {str(e)}")
            raise
            
        return True

    async def run(self, config):
        """
        Start the main audio processing loop.
        
        Args:
            config: Gemini API configuration object
        """
        self._loop = asyncio.get_event_loop()
        try:
            await self.connect_with_retry(config)
            if not self.session:
                raise Exception("Failed to establish session")

            # Create queues
            self.audio_in_queue = asyncio.Queue()
            self.out_queue = asyncio.Queue(maxsize=5)
            
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
            self.running = False
            await self.stop()