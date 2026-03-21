import os
import io
import logging
import base64
from typing import Optional
from elevenlabs import ElevenLabs, VoiceSettings
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class ElevenLabsProvider:
    """Provider for ElevenLabs text-to-speech"""
    
    def __init__(self):
        self.api_key = os.environ.get("ELEVENLABS_API_KEY")
        self.client = ElevenLabs(api_key=self.api_key)
        self.voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        self.model = os.environ.get("ELEVENLABS_MODEL", "eleven_turbo_v2_5")
    
    def generate_speech(self, text: str) -> bytes:
        """Generate speech from text and return audio bytes"""
        try:
            voice_settings = VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.3,
                use_speaker_boost=True
            )
            
            audio_generator = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id=self.model,
                voice_settings=voice_settings
            )
            
            # Collect audio bytes
            audio_data = b""
            for chunk in audio_generator:
                audio_data += chunk
            
            return audio_data
        except Exception as e:
            logger.error(f"Error generating speech: {e}")
            raise
    
    def generate_speech_stream(self, text: str):
        """Generate streaming speech from text"""
        try:
            voice_settings = VoiceSettings(
                stability=0.5,
                similarity_boost=0.75,
                style=0.3,
                use_speaker_boost=True
            )
            
            audio_stream = self.client.text_to_speech.convert(
                text=text,
                voice_id=self.voice_id,
                model_id=self.model,
                voice_settings=voice_settings
            )
            
            for chunk in audio_stream:
                yield chunk
        except Exception as e:
            logger.error(f"Error in speech stream: {e}")
            raise
    
    def generate_speech_base64(self, text: str) -> str:
        """Generate speech and return as base64 encoded string"""
        audio_bytes = self.generate_speech(text)
        return base64.b64encode(audio_bytes).decode('utf-8')
    
    def set_voice(self, voice_id: str):
        """Update the voice ID"""
        self.voice_id = voice_id

    def speech_to_text(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """Transcribe audio bytes to text using ElevenLabs Scribe v1"""
        try:
            ext = filename.rsplit(".", 1)[-1].lower()
            mime = "audio/mp4" if ext == "mp4" else "audio/webm"
            result = self.client.speech_to_text.convert(
                model_id="scribe_v1",
                file=(filename, io.BytesIO(audio_bytes), mime),
                language_code="en",
            )
            return result.text or ""
        except Exception as e:
            logger.error(f"STT error: {e}")
            raise


# Singleton instance
_elevenlabs_provider: Optional[ElevenLabsProvider] = None

def get_elevenlabs_provider() -> ElevenLabsProvider:
    global _elevenlabs_provider
    if _elevenlabs_provider is None:
        _elevenlabs_provider = ElevenLabsProvider()
    return _elevenlabs_provider