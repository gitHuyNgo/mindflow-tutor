import logging
from typing import Optional
from providers.openai_provider import get_openai_provider
from core.prompts import VISION_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


class VisionEngine:
    """Engine for analyzing screen captures using GPT-4o Vision"""
    
    def __init__(self):
        self.openai = get_openai_provider()
    
    async def analyze_screen(self, screen_base64: str) -> dict:
        """Analyze a screen capture and extract educational context"""
        try:
            analysis = await self.openai.analyze_image(
                image_base64=screen_base64,
                prompt=VISION_ANALYSIS_PROMPT
            )
            
            # Parse the analysis into structured format
            return {
                "raw_analysis": analysis,
                "keywords": self._extract_keywords(analysis),
                "topic": self._extract_topic(analysis)
            }
        except Exception as e:
            logger.error(f"Vision analysis failed: {e}")
            return {
                "raw_analysis": "Unable to analyze screen content",
                "keywords": [],
                "topic": "Unknown"
            }
    
    def _extract_keywords(self, analysis: str) -> list:
        """Extract keywords from analysis text"""
        # Simple extraction - in production, could use NLP
        keywords = []
        common_words = {"the", "a", "an", "is", "are", "and", "or", "but", "in", "on", "at", "to", "for"}
        
        words = analysis.lower().split()
        for word in words:
            clean_word = ''.join(c for c in word if c.isalnum())
            if len(clean_word) > 3 and clean_word not in common_words:
                keywords.append(clean_word)
        
        # Return unique keywords, limited
        return list(set(keywords))[:10]
    
    def _extract_topic(self, analysis: str) -> str:
        """Extract main topic from analysis"""
        # Simple extraction - take first sentence or first 100 chars
        first_line = analysis.split('\n')[0] if analysis else "General study"
        return first_line[:100]


# Singleton instance
_vision_engine: Optional[VisionEngine] = None

def get_vision_engine() -> VisionEngine:
    global _vision_engine
    if _vision_engine is None:
        _vision_engine = VisionEngine()
    return _vision_engine