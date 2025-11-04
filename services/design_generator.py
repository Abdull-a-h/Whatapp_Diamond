import os
import json
import asyncio
import hashlib
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

IMAGE_GEN_API_KEY = os.getenv("IMAGE_GEN_API_KEY", "placeholder")
IMAGE_GEN_API_URL = os.getenv("IMAGE_GEN_API_URL",
                              "https://api.example.com/v1/generate")
IMAGE_GEN_MODEL = os.getenv("IMAGE_GEN_MODEL", "flux-pro")

OSS_120B_API_KEY = os.getenv("OSS_120B_API_KEY", "placeholder")
OSS_120B_API_URL = os.getenv("OSS_120B_API_URL",
                             "https://api.example.com/v1/chat/completions")


class DesignGenerator:
    """
    Generates photorealistic jewelry designs using AI image generation models.
    For placeholder use: returns mock URLs and refined prompts without calling real APIs.
    """

    def __init__(self):
        self.image_api_key = IMAGE_GEN_API_KEY
        self.image_api_url = IMAGE_GEN_API_URL
        self.model_name = IMAGE_GEN_MODEL
        self.prompt_api_key = OSS_120B_API_KEY
        self.prompt_api_url = OSS_120B_API_URL

    # ---------- PUBLIC DESIGN METHODS ----------

    async def auto_design(self, gia_data: Dict[str, Any]) -> Dict[str, Any]:
        """Automatically generate jewelry design based on GIA diamond characteristics."""
        try:
            jewelry_type = self._choose_jewelry_type(gia_data)
            prompt = await self._generate_auto_design_prompt(
                gia_data, jewelry_type)
            image_url = await self._generate_image(prompt)

            return {
                "success": True,
                "image_url": image_url,
                "prompt": prompt,
                "jewelry_type": jewelry_type
            }

        except Exception as e:
            logger.error(f"Auto-design error: {str(e)}")
            return {"success": False, "error": str(e)}

    async def free_design(self, description: str) -> Dict[str, Any]:
        """Generate jewelry design from free-form text description."""
        try:
            refined_prompt = await self._refine_design_prompt(description)
            image_url = await self._generate_image(refined_prompt)
            return {
                "success": True,
                "image_url": image_url,
                "prompt": refined_prompt
            }
        except Exception as e:
            logger.error(f"Free design error: {str(e)}")
            return {"success": False, "error": str(e)}

    async def gia_custom_design(self, gia_data: Dict[str, Any],
                                description: str) -> Dict[str, Any]:
        """Combine GIA data with user’s description."""
        try:
            merged_prompt = await self._merge_gia_and_description(
                gia_data, description)
            image_url = await self._generate_image(merged_prompt)
            return {
                "success": True,
                "image_url": image_url,
                "prompt": merged_prompt
            }
        except Exception as e:
            logger.error(f"GIA custom design error: {str(e)}")
            return {"success": False, "error": str(e)}

    async def edit_design(self, original_prompt: str, original_image: str,
                          edit_description: str) -> Dict[str, Any]:
        """Edit existing jewelry design."""
        try:
            updated_prompt = await self._merge_design_edits(
                original_prompt, edit_description)
            image_url = await self._generate_image(updated_prompt)
            return {
                "success": True,
                "image_url": image_url,
                "prompt": updated_prompt
            }
        except Exception as e:
            logger.error(f"Edit design error: {str(e)}")
            return {"success": False, "error": str(e)}

    async def create_variation(self, original_prompt: str) -> Dict[str, Any]:
        """Generate variation of design."""
        try:
            variation_prompt = await self._create_variation_prompt(
                original_prompt)
            image_url = await self._generate_image(variation_prompt)
            return {
                "success": True,
                "image_url": image_url,
                "prompt": variation_prompt
            }
        except Exception as e:
            logger.error(f"Variation error: {str(e)}")
            return {"success": False, "error": str(e)}

    async def generate_360_view(self, original_prompt: str,
                                original_image: str) -> Dict[str, Any]:
        """Generate placeholder 360° views."""
        try:
            logger.info("Generating placeholder 360° views")
            angles = [0, 45, 90, 135, 180, 225, 270, 315]
            images = {}

            for angle in angles:
                await asyncio.sleep(0.1)
                placeholder_text = f"{original_prompt[:30]} ({angle}°)"
                images[
                    angle] = f"https://via.placeholder.com/1024x1024?text={placeholder_text.replace(' ', '+')}"

            return {"success": True, "images": images}
        except Exception as e:
            logger.error(f"360° view error: {str(e)}")
            return {"success": False, "error": str(e)}

    # ---------- HELPER LOGIC ----------

    def _choose_jewelry_type(self, gia_data: Dict[str, Any]) -> str:
        carat = gia_data.get("carat", 1.0)
        shape = gia_data.get("shape", "Round").lower()
        if carat >= 2.0:
            return "solitaire engagement ring"
        elif carat >= 1.0:
            if "round" in shape or "oval" in shape:
                return "halo engagement ring"
            else:
                return "three-stone ring"
        elif carat >= 0.5:
            return "pendant necklace" if "round" in shape else "elegant ring"
        return "stud earrings"

    async def _generate_auto_design_prompt(self, gia_data: Dict[str, Any],
                                           jewelry_type: str) -> str:
        shape = gia_data.get("shape", "Round")
        carat = gia_data.get("carat", 1.0)
        color = gia_data.get("color", "G")
        clarity = gia_data.get("clarity", "VS1")
        cut = gia_data.get("cut", "Excellent")
        quality = self._get_quality_description(color, clarity, cut)
        metal = self._get_metal_recommendation(color)

        return (
            f"Photorealistic luxury jewelry photograph: {jewelry_type} "
            f"with a {carat}ct {shape.lower()} diamond. "
            f"Color {color} ({quality['color_desc']}), clarity {clarity}, cut {cut} ({quality['cut_desc']}). "
            f"Set in {metal}, professional lighting, white background, 8K detailed image."
        )

    async def _refine_design_prompt(self, user_description: str) -> str:
        if self.prompt_api_key == "placeholder":
            return (
                f"Photorealistic jewelry photograph: {user_description}, "
                f"white background, soft lighting, 8K resolution, elegant composition."
            )
        # In production this would call OSS 120B
        return f"Refined prompt for: {user_description}"

    async def _generate_image(self,
                              prompt: str,
                              base_image: str = None) -> str:
        """Mock image generator returning placeholder URLs."""
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]
        return f"https://via.placeholder.com/1024x1024.png?text=Jewelry+{prompt_hash}"

    async def _merge_gia_and_description(self, gia_data: Dict[str, Any],
                                         description: str) -> str:
        shape = gia_data.get("shape", "Round")
        carat = gia_data.get("carat", 1.0)
        color = gia_data.get("color", "G")
        metal = self._get_metal_recommendation(color)
        return (
            f"Photorealistic jewelry piece: {description}, featuring a {carat}ct {shape.lower()} diamond "
            f"of color {color} set in {metal}. Professional studio lighting, highly detailed 8K rendering."
        )

    async def _merge_design_edits(self, original_prompt: str,
                                  edit_description: str) -> str:
        if self.prompt_api_key == "placeholder":
            return f"{original_prompt} | Apply edits: {edit_description}"
        return f"Updated prompt: {original_prompt} + {edit_description}"

    async def _create_variation_prompt(self, original_prompt: str) -> str:
        if self.prompt_api_key == "placeholder":
            return f"{original_prompt}, alternate angle and lighting variation"
        return f"Varied prompt based on: {original_prompt}"

    def _get_quality_description(self, color: str, clarity: str,
                                 cut: str) -> Dict[str, str]:
        color_grades = {
            "D": "colorless, top-grade",
            "E": "exceptionally clear",
            "F": "colorless and brilliant",
            "G": "near colorless, excellent value",
            "H": "slightly warm tone, still bright"
        }
        cut_grades = {
            "Excellent": "maximum brilliance",
            "Very Good": "superior sparkle",
            "Good": "balanced shine",
            "Fair": "visible inclusions",
            "Poor": "limited brilliance"
        }
        return {
            "color_desc": color_grades.get(color, "beautiful color"),
            "cut_desc": cut_grades.get(cut, "fine cut")
        }

    def _get_metal_recommendation(self, color_grade: str) -> str:
        if color_grade in ["D", "E", "F"]:
            return "platinum or white gold"
        elif color_grade in ["G", "H"]:
            return "white gold"
        elif color_grade in ["I", "J"]:
            return "yellow gold"
        return "rose gold"
