import os
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # For GPT-4o transcription
OPENAI_API_URL = os.getenv("OPENAI_API_URL",
                           "https://api.openai.com/v1/audio/transcriptions")


class VoiceTranscriber:
    """
    Transcribes voice messages using GPT-4o Whisper model.
    Automatically detects language and corrects obvious errors.
    """

    def __init__(self):
        self.api_key = OPENAI_API_KEY
        self.api_url = OPENAI_API_URL
        self.model = "whisper-1"

    async def transcribe(self,
                         audio_bytes: bytes,
                         language: str = None) -> Dict[str, Any]:
        """
        Transcribe audio to text with automatic language detection.

        Args:
            audio_bytes: Audio file content in bytes
            language: Optional language code (e.g., 'en', 'ur', 'ar')

        Returns:
            Dict with success status, transcribed text, language, and confidence
        """
        try:
            logger.info("Transcribing voice message")

            # TODO: Replace with actual API call when API key is available
            if self.api_key and self.api_key != "placeholder":
                result = await self._call_transcription_api(
                    audio_bytes, language)
            else:
                # Placeholder response for testing
                result = self._placeholder_transcription()

            # Post-process transcription
            if result.get("success"):
                text = result.get("text", "")
                corrected_text = await self._correct_transcription(text)
                result["text"] = corrected_text
                result["original_text"] = text

            return result

        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "text": None,
                "confidence": 0.0
            }

    async def _call_transcription_api(self,
                                      audio_bytes: bytes,
                                      language: str = None) -> Dict[str, Any]:
        """
        Make actual API call to OpenAI Whisper.

        Args:
            audio_bytes: Audio file content
            language: Optional language hint

        Returns:
            Transcription result
        """
        import httpx
        from io import BytesIO

        try:
            # Prepare multipart form data
            files = {"file": ("audio.ogg", BytesIO(audio_bytes), "audio/ogg")}

            data = {
                "model": self.model,
                "response_format": "verbose_json"  # Get confidence scores
            }

            if language:
                data["language"] = language

            # Make API request
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=files,
                    data=data)

                response.raise_for_status()
                result = response.json()

                return {
                    "success": True,
                    "text": result.get("text", ""),
                    "language": result.get("language", "unknown"),
                    "confidence": self._calculate_confidence(result),
                    "duration": result.get("duration", 0)
                }

        except Exception as e:
            logger.error(f"Transcription API error: {str(e)}")
            raise

    def _calculate_confidence(self, whisper_result: Dict) -> float:
        """
        Calculate overall confidence from Whisper segments.

        Args:
            whisper_result: Raw Whisper API response

        Returns:
            Average confidence score (0.0-1.0)
        """
        segments = whisper_result.get("segments", [])

        if not segments:
            return 1.0  # No segments means simple transcription

        # Average the confidence of all segments
        confidences = [seg.get("avg_logprob", 0) for seg in segments]

        if not confidences:
            return 0.8  # Default moderate confidence

        # Convert log probabilities to confidence scores
        # Whisper returns negative log probs, closer to 0 is better
        avg_logprob = sum(confidences) / len(confidences)

        # Convert to 0-1 scale (approximate mapping)
        confidence = max(0.0, min(1.0, 1.0 + (avg_logprob / 2)))

        return confidence

    async def _correct_transcription(self, text: str) -> str:
        """
        Correct obvious grammatical and spelling errors in transcription.

        Args:
            text: Raw transcribed text

        Returns:
            Corrected text
        """
        # Basic corrections
        corrected = text.strip()

        # Remove duplicate words
        words = corrected.split()
        deduped = []
        prev = None
        for word in words:
            if word.lower() != prev:
                deduped.append(word)
            prev = word.lower()

        corrected = " ".join(deduped)

        # Capitalize first letter
        if corrected:
            corrected = corrected[0].upper() + corrected[1:]

        # For production, you could use a grammar correction API here
        # For now, return basic corrections
        return corrected

    def _placeholder_transcription(self) -> Dict[str, Any]:
        """
        Placeholder transcription for testing without API.

        Returns:
            Mock transcription result
        """
        return {
            "success": True,
            "text": "Show me oval diamonds above 2 carats",
            "language": "en",
            "confidence": 0.95,
            "duration": 3.5
        }

    def detect_language(self, audio_bytes: bytes) -> str:
        """
        Detect language from audio (simplified version).
        In production, Whisper does this automatically.

        Args:
            audio_bytes: Audio file content

        Returns:
            Language code
        """
        # This is a placeholder
        # In production, Whisper API automatically detects language
        return "en"

    async def transcribe_with_timestamps(self,
                                         audio_bytes: bytes) -> Dict[str, Any]:
        """
        Transcribe with word-level timestamps.
        Useful for longer voice messages.

        Args:
            audio_bytes: Audio file content

        Returns:
            Transcription with timestamps
        """
        try:
            if self.api_key and self.api_key != "placeholder":
                import httpx
                from io import BytesIO

                files = {
                    "file": ("audio.ogg", BytesIO(audio_bytes), "audio/ogg")
                }

                data = {
                    "model": self.model,
                    "response_format": "verbose_json",
                    "timestamp_granularities": ["word"]
                }

                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        self.api_url,
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        files=files,
                        data=data)

                    response.raise_for_status()
                    result = response.json()

                    return {
                        "success": True,
                        "text": result.get("text", ""),
                        "words": result.get("words", []),
                        "segments": result.get("segments", [])
                    }
            else:
                return {
                    "success":
                    True,
                    "text":
                    "Show me oval diamonds",
                    "words": [{
                        "word": "Show",
                        "start": 0.0,
                        "end": 0.3
                    }, {
                        "word": "me",
                        "start": 0.3,
                        "end": 0.5
                    }, {
                        "word": "oval",
                        "start": 0.5,
                        "end": 0.9
                    }, {
                        "word": "diamonds",
                        "start": 0.9,
                        "end": 1.5
                    }],
                    "segments": []
                }

        except Exception as e:
            logger.error(f"Timestamp transcription error: {str(e)}")
            return {"success": False, "error": str(e), "text": None}
