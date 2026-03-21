import os
import logging
import base64
import aiohttp
from typing import Optional, AsyncGenerator
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class VoiceAIProvider:
    """Provider for voice AI - STT (Whisper) + GPT-4o + TTS (ElevenLabs)"""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.openai_model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        self.elevenlabs_api_key = os.environ.get("ELEVENLABS_API_KEY")
        self.elevenlabs_voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
        self.elevenlabs_model = os.environ.get("ELEVENLABS_MODEL", "eleven_turbo_v2_5")
    
    async def transcribe_audio(self, audio_data: bytes) -> Optional[str]:
        """Transcribe audio using OpenAI Whisper API"""
        try:
            import io
            
            # Create a file-like object
            audio_file = io.BytesIO(audio_data)
            audio_file.name = "audio.wav"
            
            response = await self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
            
            text = response.text.strip()
            logger.info(f"Transcribed: {text}")
            return text
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None
    
    async def generate_response(
        self,
        user_message: str,
        conversation_history: list,
        system_prompt: str,
        context: Optional[str] = None
    ) -> str:
        """Generate AI response using GPT-4o"""
        try:
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history (last 10 messages)
            messages.extend(conversation_history[-10:])
            
            # Add context if available
            full_message = user_message
            if context:
                full_message = f"Context from study materials:\n{context}\n\nUser: {user_message}"
            
            messages.append({"role": "user", "content": full_message})
            
            response = await self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=messages,
                max_tokens=300,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            logger.info(f"AI Response: {ai_response[:100]}...")
            return ai_response
            
        except Exception as e:
            logger.error(f"Response generation error: {e}")
            return "I'm sorry, I encountered an error. Could you please repeat that?"
    
    async def synthesize_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech using ElevenLabs"""
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}"
            
            headers = {
                "xi-api-key": self.elevenlabs_api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "text": text,
                "model_id": self.elevenlabs_model,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.3,
                    "use_speaker_boost": True
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        audio_data = await response.read()
                        logger.info(f"TTS generated: {len(audio_data)} bytes")
                        return audio_data
                    else:
                        error_text = await response.text()
                        logger.error(f"TTS error: {response.status} - {error_text}")
                        return None
                        
        except Exception as e:
            logger.error(f"TTS error: {e}")
            return None
    
    async def synthesize_speech_stream(self, text: str) -> AsyncGenerator[bytes, None]:
        """Stream TTS audio chunks"""
        try:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}/stream"
            
            headers = {
                "xi-api-key": self.elevenlabs_api_key,
                "Content-Type": "application/json"
            }
            
            payload = {
                "text": text,
                "model_id": self.elevenlabs_model,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status == 200:
                        async for chunk in response.content.iter_chunked(8192):
                            if chunk:
                                yield chunk
                    else:
                        error_text = await response.text()
                        logger.error(f"TTS stream error: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"TTS stream error: {e}")


# Singleton
_voice_ai_provider: Optional[VoiceAIProvider] = None

def get_voice_ai_provider() -> VoiceAIProvider:
    global _voice_ai_provider
    if _voice_ai_provider is None:
        _voice_ai_provider = VoiceAIProvider()
    return _voice_ai_provider