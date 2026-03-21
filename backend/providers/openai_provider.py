import os
import base64
import logging
from typing import Optional, List
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class OpenAIProvider:
    """Provider for OpenAI GPT-4o Vision and text generation"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    
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
        """Semantically classify whether `text` matches `intent`. Returns True/False."""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a binary intent classifier. Reply only with 'yes' or 'no'."},
                    {"role": "user", "content": f'Does this message convey the intent: "{intent}"?\n\nMessage: "{text}"'},
                ],
                max_tokens=3,
                temperature=0,
            )
            return response.choices[0].message.content.strip().lower().startswith("yes")
        except Exception as e:
            logger.error(f"classify_intent error: {e}")
            return False


# Singleton instance
_openai_provider: Optional[OpenAIProvider] = None

def get_openai_provider() -> OpenAIProvider:
    global _openai_provider
    if _openai_provider is None:
        _openai_provider = OpenAIProvider()
    return _openai_provider