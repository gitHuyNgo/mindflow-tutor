import io
import os
import base64
import logging
from typing import Optional, List
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv(override=True)
logger = logging.getLogger(__name__)


class OpenAIProvider:
    """Provider for OpenAI GPT-4o Vision and text generation"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        self.tts_model = os.environ.get("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
        self.tts_voice = os.environ.get("OPENAI_TTS_VOICE", "alloy")
        self.stt_model = os.environ.get("OPENAI_STT_MODEL", "gpt-4o-mini-transcribe")
    
    async def analyze_image(self, image_base64: str, prompt: str) -> str:
        """Analyze an image using GPT-4o Vision"""
        try:
            # Clean base64 string if it has data URL prefix
            if "," in image_base64:
                image_base64 = image_base64.split(",")[1]
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}",
                                    "detail": "auto"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            raise
    
    async def generate_response(
        self, 
        system_prompt: str, 
        user_message: str,
        context: Optional[str] = None,
        conversation_history: Optional[List[dict]] = None
    ) -> str:
        """Generate a text response using GPT-4o"""
        try:
            messages = [{"role": "system", "content": system_prompt}]
            
            # Add conversation history if provided
            if conversation_history:
                messages.extend(conversation_history[-5:])  # Last 5 messages
            
            # Add context if provided
            full_message = user_message
            if context:
                full_message = f"Context: {context}\n\nUser situation: {user_message}"
            
            messages.append({"role": "user", "content": full_message})
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1024,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise


    async def classify_intent(self, text: str, intent: str) -> bool:
        """
        Embedding-based yes/no classifier.
        Embeds the user's text and compares cosine similarity against
        a cluster of affirmative vs. negative reference phrases.
        Returns True if the text is closer to the 'yes' cluster.
        `intent` param is kept for API compatibility but not used.
        """
        YES_PHRASES = [
            "yes", "yeah", "yep", "yup", "sure", "correct", "right",
            "absolutely", "definitely", "of course", "indeed", "exactly",
            "ok", "okay", "affirmative", "true", "confirmed", "i do",
            "i am", "i'm confused", "i don't understand", "help me",
            "please", "i need help", "that's right", "uh huh",
        ]
        NO_PHRASES = [
            "no", "nope", "nah", "not really", "i'm fine", "i'm okay",
            "no thanks", "nevermind", "never mind", "not at all",
            "i understand", "i got it", "i know", "clear now",
            "don't worry", "all good", "i'm good", "no need",
            "false", "wrong", "negative",
        ]
        try:
            # Embed user text + all reference phrases in one batch call
            all_texts = [text] + YES_PHRASES + NO_PHRASES
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=all_texts,
            )
            vecs = [e.embedding for e in response.data]

            def cosine(a: list, b: list) -> float:
                dot = sum(x * y for x, y in zip(a, b))
                na  = sum(x * x for x in a) ** 0.5
                nb  = sum(x * x for x in b) ** 0.5
                return dot / (na * nb) if na and nb else 0.0

            user_vec  = vecs[0]
            yes_vecs  = vecs[1 : 1 + len(YES_PHRASES)]
            no_vecs   = vecs[1 + len(YES_PHRASES):]

            yes_score = sum(cosine(user_vec, v) for v in yes_vecs) / len(yes_vecs)
            no_score  = sum(cosine(user_vec, v) for v in no_vecs)  / len(no_vecs)

            logger.debug(f"classify_intent yes={yes_score:.4f} no={no_score:.4f} text={text!r}")
            return yes_score > no_score
        except Exception as e:
            logger.error(f"classify_intent error: {e}")
            return False

    async def generate_speech(self, text: str) -> bytes:
        """Generate TTS audio using OpenAI gpt-4o-mini-tts"""
        try:
            response = await self.client.audio.speech.create(
                model=self.tts_model,
                voice=self.tts_voice,
                input=text,
                response_format="mp3",
                instructions="Speak in a warm, friendly, and encouraging tutor tone.",
            )
            return response.content
        except Exception as e:
            logger.error(f"TTS error: {e}")
            raise

    async def generate_speech_base64(self, text: str) -> str:
        """Generate TTS audio and return as base64 string"""
        audio_bytes = await self.generate_speech(text)
        return base64.b64encode(audio_bytes).decode("utf-8")

    async def generate_speech_stream(self, text: str):
        """Async generator for streaming TTS audio"""
        try:
            async with self.client.audio.speech.with_streaming_response.create(
                model=self.tts_model,
                voice=self.tts_voice,
                input=text,
                response_format="mp3",
                instructions="Speak in a warm, friendly, and encouraging tutor tone.",
            ) as response:
                async for chunk in response.iter_bytes(chunk_size=4096):
                    yield chunk
        except Exception as e:
            logger.error(f"TTS stream error: {e}")
            raise

    async def speech_to_text(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """Transcribe audio using OpenAI gpt-4o-mini-transcribe"""
        try:
            ext = filename.rsplit(".", 1)[-1].lower()
            result = await self.client.audio.transcriptions.create(
                model=self.stt_model,
                file=(filename, io.BytesIO(audio_bytes), f"audio/{ext}"),
                response_format="text",
            )
            return result if isinstance(result, str) else (result.text or "")
        except Exception as e:
            logger.error(f"STT error: {e}")
            raise


# Singleton instance
_openai_provider: Optional[OpenAIProvider] = None

def get_openai_provider() -> OpenAIProvider:
    global _openai_provider
    if _openai_provider is None:
        _openai_provider = OpenAIProvider()
    return _openai_provider