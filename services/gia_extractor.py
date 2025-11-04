import os
import json
import base64
from typing import Dict, Any, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # GroQ API key for Llama model
GROQ_API_URL = os.getenv("GROQ_API_URL",
                         "https://api.groq.com/openai/v1/chat/completions")


class GIAExtractor:
    """
    Extracts structured data from GIA certificates using meta-llama/llama-4-maverick-17b-128e-instruct.
    Handles both PDF (converted to image) and direct image inputs.
    """

    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.api_url = GROQ_API_URL
        self.model_name = "meta-llama/llama-4-maverick-17b-128e-instruct"
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the system prompt for GIA extraction."""
        return """You are a GIA certificate data extraction expert.

Analyze the provided GIA diamond grading report image and extract ALL information into structured JSON.

Required fields:
- report_number: GIA report number
- shape: Diamond shape (Round, Oval, Emerald, etc.)
- measurements: Dimensions in mm (e.g., "6.52 x 6.47 x 4.01")
- carat: Carat weight (number)
- color: Color grade (D-Z or Fancy color)
- clarity: Clarity grade (FL, IF, VVS1, VVS2, VS1, VS2, SI1, SI2, I1, I2, I3)
- cut: Cut grade (Excellent, Very Good, Good, Fair, Poor) - if applicable
- polish: Polish grade
- symmetry: Symmetry grade
- fluorescence: Fluorescence (None, Faint, Medium, Strong, Very Strong)
- depth_percent: Total depth percentage
- table_percent: Table percentage
- girdle: Girdle description
- culet: Culet description
- clarity_characteristics: Array of clarity features
- inscription: Laser inscription (usually the report number)

Additional fields (if present):
- crown_angle: Crown angle in degrees
- crown_height: Crown height percentage
- pavilion_angle: Pavilion angle in degrees
- pavilion_depth: Pavilion depth percentage
- star_length: Star facet length percentage
- lower_half: Lower half facet percentage
- girdle_min: Minimum girdle thickness
- girdle_max: Maximum girdle thickness

Respond with ONLY valid JSON. If a field is not visible or not applicable, use null.

Example output:
{
  "report_number": "2141438171",
  "shape": "Round Brilliant",
  "measurements": "6.52 x 6.47 x 4.01",
  "carat": 1.01,
  "color": "E",
  "clarity": "VS2",
  "cut": "Excellent",
  "polish": "Excellent",
  "symmetry": "Very Good",
  "fluorescence": "None",
  "depth_percent": 61.8,
  "table_percent": 57.0,
  "girdle": "Medium to Slightly Thick",
  "culet": "None",
  "clarity_characteristics": ["Crystal", "Feather"],
  "inscription": "GIA 2141438171",
  "crown_angle": 34.5,
  "pavilion_angle": 40.8
}

Be precise and accurate. Extract ALL visible information."""

    async def extract_from_pdf(self, pdf_url: str) -> Dict[str, Any]:
        """
        Extract GIA data from PDF certificate.

        Args:
            pdf_url: URL to the PDF file

        Returns:
            Dict with success status and extracted data or error
        """
        try:
            logger.info(f"Extracting GIA data from PDF: {pdf_url}")

            # Convert PDF to image
            image_url = await self._convert_pdf_to_image(pdf_url)

            # Extract from image
            return await self.extract_from_image(image_url)

        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to extract from PDF: {str(e)}",
                "data": None
            }

    async def extract_from_image(self, image_url: str) -> Dict[str, Any]:
        """
        Extract GIA data from image.

        Args:
            image_url: URL to the image file

        Returns:
            Dict with success status and extracted data or error
        """
        try:
            logger.info(f"Extracting GIA data from image: {image_url}")

            # TODO: Replace with actual API call when API key is available
            if self.api_key and self.api_key != "placeholder":
                result = await self._call_vision_api(image_url)
            else:
                # Placeholder response for testing
                result = self._placeholder_extraction()

            # Validate extracted data
            if result.get("report_number"):
                logger.info(
                    f"Successfully extracted GIA report: {result.get('report_number')}"
                )
                return {"success": True, "data": result, "error": None}
            else:
                return {
                    "success": False,
                    "error": "Could not find GIA report number in image",
                    "data": result
                }

        except Exception as e:
            logger.error(f"Image extraction error: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to extract from image: {str(e)}",
                "data": None
            }

    async def _call_vision_api(self, image_url: str) -> Dict[str, Any]:
        """Make actual API call to Llama Vision model on GroQ."""
        import httpx

        # Download image and convert to base64
        async with httpx.AsyncClient() as client:
            img_response = await client.get(image_url)
            img_response.raise_for_status()
            image_data = base64.b64encode(img_response.content).decode('utf-8')

        # Make API call
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.api_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model":
                    self.model_name,
                    "messages": [{
                        "role": "system",
                        "content": self.system_prompt
                    }, {
                        "role":
                        "user",
                        "content": [{
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }, {
                            "type":
                            "text",
                            "content":
                            "Extract all GIA certificate data from this image."
                        }]
                    }],
                    "temperature":
                    0.1,
                    "max_tokens":
                    2000
                })

            response.raise_for_status()
            data = response.json()

            # Parse JSON response
            content = data.get("choices",
                               [{}])[0].get("message",
                                            {}).get("content", "{}")

            # Extract JSON from response (may be wrapped in markdown code blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)

    async def _convert_pdf_to_image(self, pdf_url: str) -> str:
        """
        Convert PDF to image using pdf2image or similar library.
        Returns URL of the converted image.
        """
        try:
            import httpx
            from pdf2image import convert_from_bytes
            from io import BytesIO
            from PIL import Image

            # Download PDF
            async with httpx.AsyncClient() as client:
                response = await client.get(pdf_url)
                response.raise_for_status()
                pdf_bytes = response.content

            # Convert first page to image
            images = convert_from_bytes(pdf_bytes,
                                        first_page=1,
                                        last_page=1,
                                        dpi=300)

            if not images:
                raise Exception("Failed to convert PDF to image")

            # Save to BytesIO
            img_io = BytesIO()
            images[0].save(img_io, format='JPEG', quality=95)
            img_io.seek(0)

            # Upload to storage and return URL
            from app.database.supabase_client import get_supabase_client
            from uuid import uuid4

            supabase = get_supabase_client()
            file_path = f"converted_pdfs/{uuid4()}.jpg"

            supabase.storage.from_("whatsapp_uploads").upload(
                file_path, img_io.getvalue(), {"content-type": "image/jpeg"})

            image_url = supabase.storage.from_(
                "whatsapp_uploads").get_public_url(file_path)

            logger.info(f"PDF converted to image: {image_url}")
            return image_url

        except ImportError:
            logger.warning(
                "pdf2image not installed, using placeholder conversion")
            # Return original URL as fallback
            return pdf_url
        except Exception as e:
            logger.error(f"PDF conversion error: {str(e)}")
            raise

    def _placeholder_extraction(self) -> Dict[str, Any]:
        """
        Placeholder extraction for testing without API.
        Returns sample GIA data.
        """
        return {
            "report_number": "PLACEHOLDER_12345",
            "shape": "Round Brilliant",
            "measurements": "6.52 x 6.47 x 4.01",
            "carat": 1.01,
            "color": "E",
            "clarity": "VS2",
            "cut": "Excellent",
            "polish": "Excellent",
            "symmetry": "Very Good",
            "fluorescence": "None",
            "depth_percent": 61.8,
            "table_percent": 57.0,
            "girdle": "Medium to Slightly Thick",
            "culet": "None",
            "clarity_characteristics": ["Crystal", "Feather", "Cloud"],
            "inscription": "GIA PLACEHOLDER_12345",
            "crown_angle": 34.5,
            "crown_height": 15.5,
            "pavilion_angle": 40.8,
            "pavilion_depth": 43.0,
            "star_length": 50,
            "lower_half": 80,
            "girdle_min": "Medium",
            "girdle_max": "Slightly Thick"
        }

    def validate_gia_data(self, data: Dict[str, Any]) -> bool:
        """
        Validate that extracted GIA data has required fields.

        Args:
            data: Extracted GIA data

        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            "report_number", "shape", "carat", "color", "clarity"
        ]

        for field in required_fields:
            if not data.get(field):
                logger.warning(f"Missing required field: {field}")
                return False

        return True
