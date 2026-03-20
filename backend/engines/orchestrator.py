import asyncio
import logging
from typing import Optional
from engines.vision_engine import get_vision_engine
from engines.rag_retriever import get_rag_retriever
from providers.openai_provider import get_openai_provider
from providers.tavily_provider import get_tavily_provider
from providers.elevenlabs_provider import get_elevenlabs_provider
from persistence.session_memory import get_session_memory
from core.prompts import TUTOR_SYSTEM_PROMPT, CONFUSION_RESPONSE_TEMPLATE

logger = logging.getLogger(__name__)


class Orchestrator:
    """Main orchestrator that coordinates all AI components"""
    
    def __init__(self):
        self.vision = get_vision_engine()
        self.rag = get_rag_retriever()
        self.openai = get_openai_provider()
        self.tts = get_elevenlabs_provider()
        self.memory = get_session_memory()
    
    async def process_confusion_trigger(
        self,
        screen_capture: str,
        session_id: str,
        user_query: Optional[str] = None,
        use_web_search: bool = False
    ) -> dict:
        """
        Main processing pipeline when confusion is detected.
        Uses parallel execution for Vision + Memory retrieval.
        Knowledge hierarchy: RAG > LLM > Web Search
        """
        try:
            # Step 1: Parallel execution of Vision analysis and Memory retrieval
            vision_task = asyncio.create_task(
                self.vision.analyze_screen(screen_capture)
            )
            
            # Get conversation history (sync operation wrapped)
            history_context = self.memory.get_context_summary(session_id)
            
            # Wait for vision analysis
            screen_analysis = await vision_task
            
            # Step 2: Get RAG context based on screen analysis
            topic = screen_analysis.get("topic", "the current topic")
            keywords = screen_analysis.get("keywords", [])
            
            # Build RAG query from screen context and user query
            rag_query = user_query if user_query else " ".join(keywords[:5])
            rag_context = self.rag.get_context(rag_query) if rag_query else ""
            
            # Step 3: Determine if we need web search (only if RAG has no results)
            web_context = ""
            sources_used = ["LLM Internal Knowledge"]
            
            if rag_context and rag_context != "No relevant materials found in uploaded documents.":
                sources_used.insert(0, "Uploaded Materials (RAG)")
            elif use_web_search:
                try:
                    tavily = await get_tavily_provider()
                    search_results = await tavily.search_educational(topic)
                    if search_results.get("answer"):
                        web_context = search_results["answer"]
                        sources_used.append("Web Search (Tavily)")
                except Exception as e:
                    logger.warning(f"Web search failed: {e}")
            
            # Step 4: Generate empathetic response
            prompt_context = CONFUSION_RESPONSE_TEMPLATE.format(
                screen_context=screen_analysis.get("raw_analysis", "screen content"),
                conversation_history=history_context,
                rag_context=rag_context or web_context or "No specific materials available."
            )
            
            # Get formatted history for OpenAI
            formatted_history = self.memory.get_formatted_history(session_id)
            
            text_response = await self.openai.generate_response(
                system_prompt=TUTOR_SYSTEM_PROMPT,
                user_message=prompt_context,
                conversation_history=formatted_history
            )
            
            # Step 5: Store messages in session memory
            user_content = user_query or f"[Confusion detected while viewing: {topic}]"
            self.memory.add_message(session_id, "user", user_content, emotion="confused")
            self.memory.add_message(session_id, "assistant", text_response)
            
            # Step 6: Generate audio (done after returning text for faster response)
            audio_base64 = None
            try:
                audio_base64 = self.tts.generate_speech_base64(text_response)
            except Exception as e:
                logger.warning(f"TTS generation failed: {e}")
            
            return {
                "success": True,
                "session_id": session_id,
                "text_response": text_response,
                "audio_base64": audio_base64,
                "screen_analysis": screen_analysis.get("raw_analysis"),
                "sources_used": sources_used
            }
            
        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            return {
                "success": False,
                "session_id": session_id,
                "text_response": "I'm here to help! Could you tell me what you're finding confusing?",
                "audio_base64": None,
                "screen_analysis": None,
                "sources_used": [],
                "error": str(e)
            }
    
    async def process_direct_question(
        self,
        question: str,
        session_id: str
    ) -> dict:
        """Process a direct question from the user"""
        try:
            # Get RAG context
            rag_context = self.rag.get_context(question)
            
            # Get formatted history
            formatted_history = self.memory.get_formatted_history(session_id)
            
            # Generate response
            text_response = await self.openai.generate_response(
                system_prompt=TUTOR_SYSTEM_PROMPT,
                user_message=question,
                context=rag_context,
                conversation_history=formatted_history
            )
            
            # Store in memory
            self.memory.add_message(session_id, "user", question)
            self.memory.add_message(session_id, "assistant", text_response)
            
            # Generate audio
            audio_base64 = None
            try:
                audio_base64 = self.tts.generate_speech_base64(text_response)
            except Exception as e:
                logger.warning(f"TTS generation failed: {e}")
            
            return {
                "success": True,
                "session_id": session_id,
                "text_response": text_response,
                "audio_base64": audio_base64,
                "sources_used": ["Uploaded Materials (RAG)" if rag_context else "LLM Internal Knowledge"]
            }
            
        except Exception as e:
            logger.error(f"Question processing error: {e}")
            return {
                "success": False,
                "session_id": session_id,
                "text_response": "I apologize, I encountered an error. Could you rephrase your question?",
                "audio_base64": None,
                "error": str(e)
            }


# Singleton instance
_orchestrator: Optional[Orchestrator] = None

def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator