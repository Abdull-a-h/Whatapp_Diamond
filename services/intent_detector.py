import os
import json
from typing import Dict, Any, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Environment variables for API configuration
OSS_120B_API_KEY = os.getenv("OSS_120B_API_KEY")  # API key for OSS 120B model
OSS_120B_API_URL = os.getenv("OSS_120B_API_URL",
                             "https://api.example.com/v1/chat/completions")


class IntentDetector:
    """
    Detects user intent from text messages using OSS 120B model.
    Classifies intents into: search, design_free_input, design_with_gia, 
    design_edit, design_variation, listing_intent, general_inquiry
    """

    def __init__(self):
        self.api_key = OSS_120B_API_KEY
        self.api_url = OSS_120B_API_URL
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt for intent detection."""
        return """You are an intent classification system for a diamond and jewelry chatbot.

Analyze the user's message and classify it into ONE of these intents:

1. **search** - User wants to find/browse diamonds
   Examples: "show me oval diamonds", "3 carat diamonds", "yellow diamonds above 2 carats"

2. **design_free_input** - User wants to design jewelry (no GIA context)
   Examples: "design a ring", "create a pendant", "make me custom jewelry"

3. **design_with_gia** - User wants to design with their uploaded diamond
   Examples: "design a ring with my diamond", "make earrings with this stone"

4. **design_edit** - User wants to modify existing design
   Examples: "make it gold", "add more stones", "change the band", "thicker"

5. **design_variation** - User wants a variation of current design
   Examples: "try again", "show another", "different style", "variation"

6. **listing_intent** - User discussing listing/selling diamonds
   Examples: "what's the price", "how much", "list for sale", "contact for price"

7. **general_inquiry** - General questions about diamonds/jewelry/service
   Examples: "how does this work", "what is clarity", "tell me about cuts"

8. **greeting** - Greetings and social niceties
   Examples: "hi", "hello", "thanks", "goodbye"

Respond ONLY with valid JSON:
{
  "intent": "intent_name",
  "confidence": 0.0-1.0,
  "entities": {
    "shape": "oval",
    "carat_min": 3.0,
    "carat_max": 5.0,
    "color": "yellow",
    "price_max": 50000
  },
  "reasoning": "brief explanation"
}

Extract relevant entities for search queries (shape, carat, color, clarity, cut, price ranges)."""

    async def detect(self, text: str, session: Dict[str,
                                                    Any]) -> Dict[str, Any]:
        """
        Detect intent from user text.

        Args:
            text: User message text
            session: Current user session for context

        Returns:
            Dict with intent, confidence, entities, and reasoning
        """
        try:
            # Add session context to help with intent detection
            context_info = ""
            if session.get("last_gia"):
                context_info = "\n[Context: User has uploaded GIA certificate]"
            if session.get("last_design_prompt"):
                context_info += "\n[Context: User has active design session]"

            user_message = f"{text}{context_info}"

            # TODO: Replace with actual API call when API key is available
            if self.api_key and self.api_key != "placeholder":
                result = await self._call_api(user_message)
            else:
                # Placeholder response for testing
                result = await self._placeholder_detection(text, session)

            logger.info(
                f"Intent detected: {result.get('intent')} (confidence: {result.get('confidence')})"
            )
            return result

        except Exception as e:
            logger.error(f"Intent detection error: {str(e)}")
            return {
                "intent": "general_inquiry",
                "confidence": 0.5,
                "entities": {},
                "reasoning":
                "Error in detection, defaulting to general inquiry"
            }

    async def _call_api(self, text: str) -> Dict[str, Any]:
        """Make actual API call to OSS 120B model."""
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model":
                    "oss-120b",  # Model identifier
                    "messages": [{
                        "role": "system",
                        "content": self.system_prompt
                    }, {
                        "role": "user",
                        "content": text
                    }],
                    "temperature":
                    0.3,
                    "max_tokens":
                    500
                })

            response.raise_for_status()
            data = response.json()

            # Parse the response
            content = data.get("choices",
                               [{}])[0].get("message",
                                            {}).get("content", "{}")
            return json.loads(content)

    async def _placeholder_detection(self, text: str,
                                     session: Dict) -> Dict[str, Any]:
        """
        Placeholder intent detection using keyword matching.
        This will be replaced with actual AI model when API is available.
        """
        text_lower = text.lower()

        # Design variation keywords
        if any(kw in text_lower for kw in
               ["try again", "variation", "another", "different style"]):
            return {
                "intent": "design_variation",
                "confidence": 0.95,
                "entities": {},
                "reasoning": "User requested design variation"
            }

        # Design edit keywords
        if any(kw in text_lower for kw in [
                "change", "make it", "add", "remove", "modify", "edit",
                "thicker", "thinner", "gold", "silver", "platinum"
        ]):
            if session.get("last_design_prompt"):
                return {
                    "intent": "design_edit",
                    "confidence": 0.9,
                    "entities": {},
                    "reasoning": "User wants to edit existing design"
                }

        # Search keywords
        search_keywords = [
            "show me", "find", "search", "looking for", "want", "need",
            "carat", "oval", "round", "emerald", "price"
        ]
        if any(kw in text_lower for kw in search_keywords):
            entities = self._extract_search_entities(text_lower)
            return {
                "intent": "search",
                "confidence": 0.85,
                "entities": entities,
                "reasoning": "User searching for diamonds"
            }

        # Design keywords with GIA context
        if any(kw in text_lower
               for kw in ["design", "create", "make", "custom"]):
            if session.get("last_gia"):
                return {
                    "intent": "design_with_gia",
                    "confidence": 0.9,
                    "entities": {},
                    "reasoning": "User wants to design with uploaded GIA"
                }
            else:
                return {
                    "intent": "design_free_input",
                    "confidence": 0.85,
                    "entities": {},
                    "reasoning": "User wants free-form design"
                }

        # Listing keywords
        if any(kw in text_lower
               for kw in ["price", "sell", "list", "cost", "contact"]):
            return {
                "intent": "listing_intent",
                "confidence": 0.8,
                "entities": {},
                "reasoning": "User discussing pricing/listing"
            }

        # Greeting keywords
        if any(
                kw in text_lower for kw in
            ["hi", "hello", "hey", "thanks", "thank you", "bye", "goodbye"]):
            return {
                "intent": "greeting",
                "confidence": 0.95,
                "entities": {},
                "reasoning": "Social greeting"
            }

        # Default to general inquiry
        return {
            "intent": "general_inquiry",
            "confidence": 0.6,
            "entities": {},
            "reasoning": "Could not determine specific intent"
        }

    def _extract_search_entities(self, text: str) -> Dict[str, Any]:
        """Extract search entities from text (simplified)."""
        entities = {}

        # Shape detection
        shapes = [
            "round", "oval", "emerald", "princess", "cushion", "radiant",
            "asscher", "marquise", "pear", "heart"
        ]
        for shape in shapes:
            if shape in text:
                entities["shape"] = shape.capitalize()

        # Color detection
        colors = ["d", "e", "f", "g", "h", "i", "j", "yellow", "pink", "blue"]
        for color in colors:
            if color in text:
                entities["color"] = color.upper() if len(
                    color) == 1 else color.capitalize()

        # Carat detection (simplified)
        import re
        carat_match = re.search(r'(\d+\.?\d*)\s*carat', text)
        if carat_match:
            entities["carat_min"] = float(carat_match.group(1))

        # Price detection
        price_match = re.search(r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
        if price_match:
            entities["price_max"] = float(
                price_match.group(1).replace(',', ''))

        return entities
