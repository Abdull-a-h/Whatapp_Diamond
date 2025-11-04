import os
import requests
import json
from fastapi import Request
from fastapi.responses import PlainTextResponse, JSONResponse
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any, Optional, List
from app.database.supabase_client import get_supabase_client
from app.utils.logger import log_to_database, get_logger
from app.services.intent_detector import IntentDetector
from app.services.gia_extractor import GIAExtractor
from app.services.design_generator import DesignGenerator
from app.services.search_handler import SearchHandler
from app.services.voice_transcriber import VoiceTranscriber

logger = get_logger(__name__)

# ======================================================================
# Environment Variables
# ======================================================================
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")

# ======================================================================
# Service Initialization
# ======================================================================
intent_detector = IntentDetector()
gia_extractor = GIAExtractor()
design_generator = DesignGenerator()
search_handler = SearchHandler()
voice_transcriber = VoiceTranscriber()


# ======================================================================
# Database Helper Functions
# ======================================================================
async def get_or_create_user(whatsapp_number: str) -> Optional[Dict[str, Any]]:
    """Get existing user or create new one."""
    try:
        supabase = get_supabase_client()

        # Try to fetch existing user
        result = supabase.table("users").select("*").eq(
            "whatsapp_number", whatsapp_number).execute()

        if result.data and len(result.data) > 0:
            # Update last interaction
            user = result.data[0]
            supabase.table("users").update({
                "last_interaction":
                datetime.utcnow().isoformat()
            }).eq("id", user["id"]).execute()
            return user

        # Create new user
        new_user = {
            "whatsapp_number": whatsapp_number,
            "last_interaction": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "session_step": "idle",
            "session_context": {}
        }
        result = supabase.table("users").insert(new_user).execute()

        if result.data and len(result.data) > 0:
            logger.info(f"Created new user: {whatsapp_number}")
            return result.data[0]

        return None
    except Exception as e:
        logger.error(f"Error getting/creating user: {str(e)}")
        return None


async def get_user_session(user_id: str) -> Dict[str, Any]:
    """Get user session from database."""
    try:
        supabase = get_supabase_client()
        result = supabase.table("users").select(
            "session_step, session_context, last_diamond_id, last_design_id"
        ).eq("id", user_id).execute()

        if result.data and len(result.data) > 0:
            user_data = result.data[0]
            return {
                "step": user_data.get("session_step", "idle"),
                "context": user_data.get("session_context", {}),
                "last_diamond_id": user_data.get("last_diamond_id"),
                "last_design_id": user_data.get("last_design_id")
            }
        return {
            "step": "idle",
            "context": {},
            "last_diamond_id": None,
            "last_design_id": None
        }
    except Exception as e:
        logger.error(f"Error getting session: {str(e)}")
        return {
            "step": "idle",
            "context": {},
            "last_diamond_id": None,
            "last_design_id": None
        }


async def update_user_session(user_id: str, updates: Dict[str, Any]):
    """Update user session in database."""
    try:
        supabase = get_supabase_client()
        db_updates = {}

        if "step" in updates:
            db_updates["session_step"] = updates["step"]
        if "context" in updates:
            db_updates["session_context"] = updates["context"]
        if "last_diamond_id" in updates:
            db_updates["last_diamond_id"] = updates["last_diamond_id"]
        if "last_design_id" in updates:
            db_updates["last_design_id"] = updates["last_design_id"]

        if db_updates:
            supabase.table("users").update(db_updates).eq("id",
                                                          user_id).execute()
            logger.info(f"Updated session for user {user_id}")
    except Exception as e:
        logger.error(f"Error updating session: {str(e)}")


async def save_message_to_db(user_id: str,
                             direction: str,
                             message_type: str,
                             content: str = None,
                             media_url: str = None,
                             meta: Dict = None):
    """Save message to database."""
    try:
        supabase = get_supabase_client()
        message_data = {
            "user_id": user_id,
            "direction": direction,
            "message_type": message_type,
            "content": content,
            "media_url": media_url,
            "meta": meta or {},
            "created_at": datetime.utcnow().isoformat()
        }
        supabase.table("messages").insert(message_data).execute()
    except Exception as e:
        logger.error(f"Error saving message: {str(e)}")


# ======================================================================
# Message Sending Functions
# ======================================================================
def send_message(to: str, text: str):
    """Send a WhatsApp text message."""
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": text
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"Message sent to {to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")
        return False


def send_interactive_buttons(to: str, body_text: str, buttons: list):
    """Send interactive button message (max 3 buttons)."""
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    action_buttons = []
    for i, btn in enumerate(buttons[:3]):
        action_buttons.append({
            "type": "reply",
            "reply": {
                "id": btn.get("id", f"btn_{i}"),
                "title": btn.get("title", "Option")[:20]
            }
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {
                "text": body_text
            },
            "action": {
                "buttons": action_buttons
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"Interactive buttons sent to {to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send interactive message: {str(e)}")
        return False


def send_interactive_list(to: str, body_text: str, button_text: str,
                          sections: List[Dict]):
    """Send interactive list message (up to 10 items per section)."""
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {
                "text": body_text
            },
            "action": {
                "button": button_text,
                "sections": sections
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"Interactive list sent to {to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send interactive list: {str(e)}")
        return False


def send_image(to: str, image_url: str, caption: str = ""):
    """Send an image message."""
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {
            "link": image_url,
            "caption": caption
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        logger.info(f"Image sent to {to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send image: {str(e)}")
        return False


# ======================================================================
# Menu Handlers
# ======================================================================
async def send_gia_menu(to: str, user_id: str, diamond_data: Dict[str, Any]):
    """Send GIA processing menu with interactive buttons."""
    summary = f"""✅ *GIA Certificate Processed*

📊 *Diamond Details:*
• Shape: {diamond_data.get('shape', 'N/A')}
• Carat: {diamond_data.get('carat', 'N/A')}
• Color: {diamond_data.get('color', 'N/A') or diamond_data.get('primary_hue', 'N/A')}
• Clarity: {diamond_data.get('clarity', 'N/A')}
• Cut: {diamond_data.get('cut', 'N/A')}
• Report #: {diamond_data.get('certificate_number', 'N/A')}

What would you like to do?"""

    buttons = [{
        "id": "list_for_sale",
        "title": "📝 List for Sale"
    }, {
        "id": "design_jewelry",
        "title": "💎 Design Jewelry"
    }, {
        "id": "improve_diamond",
        "title": "✨ Improve Diamond"
    }]

    send_interactive_buttons(to, summary, buttons)
    await save_message_to_db(user_id,
                             "outgoing",
                             "interactive",
                             content=summary)


def send_raw_message(payload: dict):
    """Send a raw message payload to WhatsApp Cloud API."""
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",  # Changed
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code >= 400:
        logger.error(f"WhatsApp API error: {response.text}")


async def send_main_menu(to: str, user_id: str):
    """Send interactive main menu."""
    menu_text = "Welcome to Diamond Bot 💎"
    menu_body = "I can help you with various diamond services. Please select an option below 👇"

    menu_sections = [{
        "title":
        "Main Menu",
        "rows": [{
            "id": "upload_gia",
            "title": "📄 Upload GIA Certificate",
            "description": "Process your diamond GIA certificate."
        }, {
            "id": "design_jewelry",
            "title": "💍 Design Custom Jewelry",
            "description": "Work with us to create a unique piece."
        }, {
            "id": "search_diamonds",
            "title": "🔍 Search for Diamonds",
            "description": "Find diamonds by cut, color, and carat."
        }, {
            "id": "general_inquiry",
            "title": "💬 General Inquiries",
            "description": "Ask us anything else!"
        }]
    }]

    message_payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": menu_text
            },
            "body": {
                "text": menu_body
            },
            "footer": {
                "text": "Diamond Bot 💎"
            },
            "action": {
                "button": "Select an option",
                "sections": menu_sections
            }
        }
    }

    send_raw_message(message_payload)
    await save_message_to_db(user_id,
                             "outgoing",
                             "interactive",
                             content=menu_body)


# ======================================================================
# File Download and Upload
# ======================================================================
async def download_whatsapp_media(media_id: str) -> Optional[bytes]:
    """Download media file from WhatsApp."""
    try:
        url = f"https://graph.facebook.com/v21.0/{media_id}"
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        media_info = response.json()
        media_url = media_info.get("url")

        file_response = requests.get(media_url, headers=headers)
        file_response.raise_for_status()

        return file_response.content
    except Exception as e:
        logger.error(f"Failed to download media: {str(e)}")
        return None


async def upload_to_supabase(file_content: bytes, user_id: str, file_name: str,
                             file_type: str) -> Optional[str]:
    """Upload file to Supabase storage and save to database."""
    try:
        supabase = get_supabase_client()
        bucket_name = "whatsapp_uploads"
        file_path = f"{user_id}/{uuid4()}_{file_name}"

        # Upload file
        supabase.storage.from_(bucket_name).upload(file_path, file_content)

        # Get public URL
        file_url = supabase.storage.from_(bucket_name).get_public_url(
            file_path)

        # Save to uploads table
        upload_data = {
            "user_id": user_id,
            "file_url": file_url,
            "file_type": file_type,
            "status": "uploaded",
            "created_at": datetime.utcnow().isoformat()
        }
        result = supabase.table("uploads").insert(upload_data).execute()

        if result.data and len(result.data) > 0:
            logger.info(f"File uploaded: {file_name}")
            return result.data[0]["id"], file_url

        return None, None
    except Exception as e:
        logger.error(f"Failed to upload to Supabase: {str(e)}")
        return None, None


# ======================================================================
# Message Handlers
# ======================================================================
async def handle_text_message(from_number: str, text: str):
    """Handle incoming text messages."""
    user = await get_or_create_user(from_number)
    if not user:
        send_message(from_number,
                     "❌ Error connecting to system. Please try again.")
        return

    user_id = user["id"]
    session = await get_user_session(user_id)

    # Save incoming message
    await save_message_to_db(user_id, "incoming", "text", content=text)

    # Detect intent
    intent_result = await intent_detector.detect(text, session)
    intent = intent_result.get("intent")

    logger.info(f"Detected intent: {intent} for user {from_number}")

    if intent == "search":
        await handle_search_query(from_number, user_id, text, intent_result)

    elif intent == "design_free_input":
        await handle_free_design(from_number, user_id, text)

    elif intent == "design_with_gia":
        if session.get("last_diamond_id"):
            await handle_gia_custom_design(from_number, user_id, text)
        else:
            send_message(
                from_number,
                "Please upload a GIA certificate first to design jewelry with your diamond."
            )

    elif intent == "design_edit":
        await handle_design_edit(from_number, user_id, text)

    elif intent == "design_variation":
        await handle_design_variation(from_number, user_id)

    elif intent == "listing_intent":
        await handle_listing_flow(from_number, user_id, text, session)

    elif intent == "general_inquiry":
        await handle_general_inquiry(from_number, user_id, text)

    else:
        await send_main_menu(from_number, user_id)


async def handle_voice_message(from_number: str, media_id: str):
    """Handle voice message transcription."""
    user = await get_or_create_user(from_number)
    if not user:
        return

    user_id = user["id"]
    send_message(from_number, "🎤 Processing your voice message...")

    voice_content = await download_whatsapp_media(media_id)
    if not voice_content:
        send_message(from_number,
                     "❌ Failed to download voice message. Please try again.")
        return

    transcription = await voice_transcriber.transcribe(voice_content)

    if transcription.get("success"):
        text = transcription.get("text")
        confidence = transcription.get("confidence", 1.0)

        await save_message_to_db(user_id,
                                 "incoming",
                                 "audio",
                                 content=text,
                                 meta={"confidence": confidence})

        if confidence > 0.7:
            send_message(
                from_number,
                f"📝 Transcription: \"{text}\"\n\nProcessing your request...")
            await handle_text_message(from_number, text)
        else:
            send_message(
                from_number,
                f"📝 Transcription (low confidence): \"{text}\"\n\nIs this correct? Please confirm or rephrase."
            )
    else:
        send_message(
            from_number,
            "❌ Could not transcribe voice message. Please try sending text instead."
        )


async def handle_document_message(from_number: str, media_id: str,
                                  filename: str, mime_type: str):
    """Handle PDF/document uploads (GIA certificates)."""
    user = await get_or_create_user(from_number)
    if not user:
        return

    user_id = user["id"]
    send_message(from_number, "📄 Processing your document...")

    file_content = await download_whatsapp_media(media_id)
    if not file_content:
        send_message(from_number,
                     "❌ Failed to download document. Please try again.")
        return

    upload_id, file_url = await upload_to_supabase(file_content, user_id,
                                                   filename, "document")
    if not file_url:
        send_message(from_number,
                     "❌ Failed to process document. Please try again.")
        return

    send_message(from_number, "🔍 Extracting diamond information...")
    gia_data = await gia_extractor.extract_from_pdf(file_url)

    if gia_data.get("success"):
        diamond_data = gia_data.get("data")

        # Save to diamonds table
        try:
            supabase = get_supabase_client()
            diamond_record = {
                "upload_id":
                upload_id,
                "user_id":
                user_id,
                "shape":
                diamond_data.get("shape"),
                "carat":
                diamond_data.get("carat"),
                "color_type":
                diamond_data.get("color_type"),
                "primary_hue":
                diamond_data.get("primary_hue"),
                "modifier":
                diamond_data.get("modifier"),
                "intensity":
                diamond_data.get("intensity"),
                "clarity":
                diamond_data.get("clarity"),
                "cut":
                diamond_data.get("cut"),
                "polish":
                diamond_data.get("polish"),
                "symmetry":
                diamond_data.get("symmetry"),
                "fluorescence":
                diamond_data.get("fluorescence"),
                "certificate_number":
                diamond_data.get("report_number")
                or diamond_data.get("certificate_number"),
                "parsed_confidence":
                diamond_data.get("confidence", 0.95),
                "created_at":
                datetime.utcnow().isoformat()
            }
            result = supabase.table("diamonds").insert(
                diamond_record).execute()

            if result.data and len(result.data) > 0:
                diamond_id = result.data[0]["id"]
                await update_user_session(user_id, {
                    "last_diamond_id": diamond_id,
                    "step": "gia_menu"
                })
                await send_gia_menu(from_number, user_id, diamond_data)
            else:
                send_message(from_number, "❌ Failed to save diamond data.")
        except Exception as e:
            logger.error(f"Error saving diamond: {str(e)}")
            send_message(from_number, "❌ Failed to save diamond data.")
    else:
        error_msg = gia_data.get("error", "Unknown error")
        send_message(
            from_number,
            f"❌ Failed to extract GIA data: {error_msg}\n\nPlease ensure the document is a valid GIA certificate."
        )


async def handle_image_message(from_number: str, media_id: str):
    """Handle image uploads."""
    user = await get_or_create_user(from_number)
    if not user:
        return

    user_id = user["id"]
    session = await get_user_session(user_id)

    send_message(from_number, "🖼️ Processing your image...")

    image_content = await download_whatsapp_media(media_id)
    if not image_content:
        send_message(from_number,
                     "❌ Failed to download image. Please try again.")
        return

    # Check if we're in listing flow waiting for media
    if session.get("step") == "listing_media":
        upload_id, file_url = await upload_to_supabase(
            image_content, user_id, f"listing_{uuid4()}.jpg", "image")
        if file_url:
            # Add image to listing context
            context = session.get("context", {})
            images = context.get("images", [])
            images.append(file_url)
            context["images"] = images
            await update_user_session(user_id, {"context": context})

            send_message(
                from_number,
                f"✅ Image {len(images)} added! Send more images or type 'done' to complete the listing."
            )
        return

    # Otherwise, try to extract GIA from image
    upload_id, file_url = await upload_to_supabase(image_content, user_id,
                                                   f"image_{uuid4()}.jpg",
                                                   "image")
    if not file_url:
        send_message(from_number,
                     "❌ Failed to process image. Please try again.")
        return

    send_message(from_number, "🔍 Analyzing image...")
    gia_data = await gia_extractor.extract_from_image(file_url)

    if gia_data.get("success") and gia_data.get("data",
                                                {}).get("certificate_number"):
        diamond_data = gia_data.get("data")

        try:
            supabase = get_supabase_client()
            diamond_record = {
                "upload_id": upload_id,
                "user_id": user_id,
                "shape": diamond_data.get("shape"),
                "carat": diamond_data.get("carat"),
                "clarity": diamond_data.get("clarity"),
                "cut": diamond_data.get("cut"),
                "certificate_number": diamond_data.get("certificate_number"),
                "created_at": datetime.utcnow().isoformat()
            }
            result = supabase.table("diamonds").insert(
                diamond_record).execute()

            if result.data:
                diamond_id = result.data[0]["id"]
                await update_user_session(user_id, {
                    "last_diamond_id": diamond_id,
                    "step": "gia_menu"
                })
                await send_gia_menu(from_number, user_id, diamond_data)
        except Exception as e:
            logger.error(f"Error saving diamond: {str(e)}")
    else:
        send_message(
            from_number,
            "This doesn't appear to be a GIA certificate. If you'd like to use this as a design reference, please describe what you'd like to create."
        )


async def handle_button_response(from_number: str, button_id: str):
    """Handle interactive button or list selections."""
    user = await get_or_create_user(from_number)
    if not user:
        return

    user_id = user["id"]

    # === Main Menu Options ===
    if button_id == "upload_gia":
        send_message(from_number,
                     "📄 Please upload your GIA certificate (PDF).")
        return
    elif button_id == "design_jewelry":
        send_message(
            from_number,
            "💍 Let's design your custom jewelry! Please describe your design idea."
        )
        return
    elif button_id == "search_diamonds":
        send_message(
            from_number,
            "🔍 Please provide your diamond search criteria (e.g., 1.0ct, D color, VS1)."
        )
        return
    elif button_id == "general_inquiry":
        send_message(from_number, "💬 How can I assist you today?")
        return

    # === GIA & Diamond Options ===
    elif button_id == "list_for_sale":
        await handle_list_for_sale(from_number, user_id)
    elif button_id == "design_jewelry":
        await handle_auto_design(from_number, user_id)
    elif button_id == "improve_diamond":
        await handle_improve_diamond(from_number, user_id)
    elif button_id == "view_more_results":
        await handle_view_more_results(from_number, user_id)
    elif button_id.startswith("design_360_"):
        design_id = button_id.replace("design_360_", "")
        await handle_360_view(from_number, user_id, design_id)
    else:
        send_message(from_number,
                     "⚠️ Unknown option selected. Please try again.")


# ======================================================================
# Feature Handlers
# ======================================================================
async def handle_list_for_sale(from_number: str, user_id: str):
    """Handle listing diamond for sale."""
    session = await get_user_session(user_id)
    diamond_id = session.get("last_diamond_id")

    if not diamond_id:
        send_message(
            from_number,
            "❌ No diamond found. Please upload a GIA certificate first.")
        return

    await update_user_session(user_id, {
        "step": "listing_price",
        "context": {}
    })
    send_message(
        from_number,
        "💰 Please provide the price for this diamond, or type 'contact' if you prefer 'Contact for Price'."
    )


async def handle_listing_flow(from_number: str, user_id: str, text: str,
                              session: Dict):
    """Handle the listing creation flow."""
    step = session.get("step")

    if step == "listing_price":
        price = "Contact for Price" if text.lower() == "contact" else text
        context = session.get("context", {})
        context["price"] = price
        await update_user_session(user_id, {
            "step": "listing_contact",
            "context": context
        })
        send_message(
            from_number,
            "📞 Please provide contact information for buyers (phone/email):")

    elif step == "listing_contact":
        context = session.get("context", {})
        context["contact_info"] = text
        await update_user_session(user_id, {
            "step": "listing_media",
            "context": context
        })
        send_message(
            from_number,
            "📸 Great! Now please send one or more images of the diamond. Type 'done' when finished."
        )

    elif step == "listing_media" and text.lower() == "done":
        context = session.get("context", {})
        images = context.get("images", [])

        if not images:
            send_message(
                from_number,
                "⚠️ Please send at least one image before completing the listing."
            )
            return

        try:
            supabase = get_supabase_client()
            listing_data = {
                "user_id": user_id,
                "diamond_id": session.get("last_diamond_id"),
                "price": context.get("price"),
                "contact_info": context.get("contact_info"),
                "images": images,
                "status": "pending_review",
                "created_at": datetime.utcnow().isoformat()
            }
            supabase.table("listings").insert(listing_data).execute()

            send_message(
                from_number,
                "✅ Listing created and submitted for admin approval. You'll be notified once it's live!"
            )
            await update_user_session(user_id, {"step": "idle", "context": {}})
        except Exception as e:
            logger.error(f"Error creating listing: {str(e)}")
            send_message(from_number,
                         "❌ Failed to create listing. Please try again.")


async def handle_auto_design(from_number: str, user_id: str):
    """Handle automatic jewelry design based on GIA data."""
    session = await get_user_session(user_id)
    diamond_id = session.get("last_diamond_id")

    if not diamond_id:
        send_message(
            from_number,
            "❌ No diamond found. Please upload a GIA certificate first.")
        return

    # Fetch diamond data
    try:
        supabase = get_supabase_client()
        result = supabase.table("diamonds").select("*").eq(
            "id", diamond_id).execute()

        if not result.data:
            send_message(from_number, "❌ Diamond data not found.")
            return

        diamond_data = result.data[0]
        send_message(
            from_number,
            "🎨 Generating jewelry design based on your diamond characteristics..."
        )

        design_result = await design_generator.auto_design(diamond_data)

        if design_result.get("success"):
            image_url = design_result.get("image_url")
            prompt = design_result.get("prompt")

            # Save design to database
            design_record = {
                "user_id": user_id,
                "diamond_id": diamond_id,
                "type": "auto_design",
                "generated_prompt": prompt,
                "generated_image_url": image_url,
                "status": "completed",
                "created_at": datetime.utcnow().isoformat()
            }
            design_result_db = supabase.table("designs").insert(
                design_record).execute()

            if design_result_db.data:
                design_id = design_result_db.data[0]["id"]
                await update_user_session(user_id,
                                          {"last_design_id": design_id})

            send_image(
                from_number, image_url,
                f"✨ Your custom jewelry design\n\nBased on: {diamond_data.get('shape')} {diamond_data.get('carat')}ct"
            )

            buttons = [{
                "id": "design_variation",
                "title": "🔄 Try Variation"
            }, {
                "id": f"design_360_{design_id}",
                "title": "🔄 360° View"
            }]
            send_interactive_buttons(
                from_number, "What would you like to do with this design?",
                buttons)
        else:
            send_message(
                from_number,
                f"❌ Failed to generate design: {design_result.get('error')}")
    except Exception as e:
        logger.error(f"Error in auto design: {str(e)}")
        send_message(from_number, "❌ An error occurred. Please try again.")


async def handle_free_design(from_number: str, user_id: str, description: str):
    """Handle free-form jewelry design."""
    send_message(from_number, "🎨 Creating your custom jewelry design...")

    design_result = await design_generator.free_design(description)

    if design_result.get("success"):
        image_url = design_result.get("image_url")
        prompt = design_result.get("prompt")

        try:
            supabase = get_supabase_client()
            design_record = {
                "user_id": user_id,
                "diamond_id": None,
                "type": "free_input",
                "user_input": description,
                "generated_prompt": prompt,
                "generated_image_url": image_url,
                "status": "completed",
                "created_at": datetime.utcnow().isoformat()
            }
            design_result_db = supabase.table("designs").insert(
                design_record).execute()

            if design_result_db.data:
                design_id = design_result_db.data[0]["id"]
                await update_user_session(user_id,
                                          {"last_design_id": design_id})

            send_image(from_number, image_url, "✨ Your custom jewelry design")

            buttons = [{
                "id": "design_variation",
                "title": "🔄 Try Variation"
            }, {
                "id": f"design_360_{design_id}",
                "title": "🔄 360° View"
            }]
            send_interactive_buttons(from_number, "What would you like to do?",
                                     buttons)
        except Exception as e:
            logger.error(f"Error saving design: {str(e)}")
    else:
        send_message(
            from_number,
            f"❌ Failed to generate design: {design_result.get('error')}")


async def handle_gia_custom_design(from_number: str, user_id: str,
                                   description: str):
    """Handle custom design with GIA data."""
    session = await get_user_session(user_id)
    diamond_id = session.get("last_diamond_id")

    if not diamond_id:
        send_message(
            from_number,
            "❌ No diamond found. Please upload a GIA certificate first.")
        return

    try:
        supabase = get_supabase_client()
        result = supabase.table("diamonds").select("*").eq(
            "id", diamond_id).execute()

        if not result.data:
            send_message(from_number, "❌ Diamond data not found.")
            return

        diamond_data = result.data[0]
        send_message(from_number,
                     "🎨 Creating custom design with your diamond...")

        design_result = await design_generator.gia_custom_design(
            diamond_data, description)

        if design_result.get("success"):
            image_url = design_result.get("image_url")
            prompt = design_result.get("prompt")

            design_record = {
                "user_id": user_id,
                "diamond_id": diamond_id,
                "type": "gia_custom",
                "user_input": description,
                "generated_prompt": prompt,
                "generated_image_url": image_url,
                "status": "completed",
                "created_at": datetime.utcnow().isoformat()
            }
            design_result_db = supabase.table("designs").insert(
                design_record).execute()

            if design_result_db.data:
                design_id = design_result_db.data[0]["id"]
                await update_user_session(user_id,
                                          {"last_design_id": design_id})

            send_image(
                from_number, image_url,
                f"✨ Custom design featuring your {diamond_data.get('shape')} diamond"
            )

            buttons = [{
                "id": "design_variation",
                "title": "🔄 Try Variation"
            }, {
                "id": f"design_360_{design_id}",
                "title": "🔄 360° View"
            }]
            send_interactive_buttons(from_number, "What would you like to do?",
                                     buttons)
        else:
            send_message(
                from_number,
                f"❌ Failed to generate design: {design_result.get('error')}")
    except Exception as e:
        logger.error(f"Error in custom design: {str(e)}")
        send_message(from_number, "❌ An error occurred. Please try again.")


async def handle_design_edit(from_number: str, user_id: str,
                             edit_description: str):
    """Handle design edits."""
    session = await get_user_session(user_id)
    design_id = session.get("last_design_id")

    if not design_id:
        send_message(
            from_number,
            "❌ No previous design found. Please create a design first.")
        return

    try:
        supabase = get_supabase_client()
        result = supabase.table("designs").select("*").eq("id",
                                                          design_id).execute()

        if not result.data:
            send_message(from_number, "❌ Design not found.")
            return

        previous_design = result.data[0]
        original_prompt = previous_design.get("generated_prompt")
        original_image = previous_design.get("generated_image_url")

        send_message(from_number, "✏️ Applying your changes...")

        design_result = await design_generator.edit_design(
            original_prompt, original_image, edit_description)

        if design_result.get("success"):
            image_url = design_result.get("image_url")
            prompt = design_result.get("prompt")

            design_record = {
                "user_id": user_id,
                "diamond_id": previous_design.get("diamond_id"),
                "type": "edit",
                "user_input": edit_description,
                "previous_prompt": original_prompt,
                "generated_prompt": prompt,
                "generated_image_url": image_url,
                "status": "completed",
                "created_at": datetime.utcnow().isoformat()
            }
            design_result_db = supabase.table("designs").insert(
                design_record).execute()

            if design_result_db.data:
                new_design_id = design_result_db.data[0]["id"]
                await update_user_session(user_id,
                                          {"last_design_id": new_design_id})

            send_image(from_number, image_url, "✨ Updated design")
        else:
            send_message(
                from_number,
                f"❌ Failed to edit design: {design_result.get('error')}")
    except Exception as e:
        logger.error(f"Error editing design: {str(e)}")
        send_message(from_number, "❌ An error occurred. Please try again.")


async def handle_design_variation(from_number: str, user_id: str):
    """Generate design variation."""
    session = await get_user_session(user_id)
    design_id = session.get("last_design_id")

    if not design_id:
        send_message(from_number, "❌ No previous design found.")
        return

    try:
        supabase = get_supabase_client()
        result = supabase.table("designs").select("*").eq("id",
                                                          design_id).execute()

        if not result.data:
            send_message(from_number, "❌ Design not found.")
            return

        previous_design = result.data[0]
        original_prompt = previous_design.get("generated_prompt")

        send_message(from_number, "🎨 Generating variation...")

        design_result = await design_generator.create_variation(original_prompt
                                                                )

        if design_result.get("success"):
            image_url = design_result.get("image_url")
            prompt = design_result.get("prompt")

            design_record = {
                "user_id": user_id,
                "diamond_id": previous_design.get("diamond_id"),
                "type": "variation",
                "previous_prompt": original_prompt,
                "generated_prompt": prompt,
                "generated_image_url": image_url,
                "status": "completed",
                "created_at": datetime.utcnow().isoformat()
            }
            design_result_db = supabase.table("designs").insert(
                design_record).execute()

            if design_result_db.data:
                new_design_id = design_result_db.data[0]["id"]
                await update_user_session(user_id,
                                          {"last_design_id": new_design_id})

            send_image(from_number, image_url, "✨ Design variation")
        else:
            send_message(
                from_number,
                f"❌ Failed to create variation: {design_result.get('error')}")
    except Exception as e:
        logger.error(f"Error creating variation: {str(e)}")
        send_message(from_number, "❌ An error occurred. Please try again.")


async def handle_360_view(from_number: str, user_id: str, design_id: str):
    """Generate 360-degree view."""
    try:
        supabase = get_supabase_client()
        result = supabase.table("designs").select("*").eq("id",
                                                          design_id).execute()

        if not result.data:
            send_message(from_number, "❌ Design not found.")
            return

        design_data = result.data[0]
        original_prompt = design_data.get("generated_prompt")
        original_image = design_data.get("generated_image_url")

        send_message(from_number,
                     "🔄 Generating 360° view... This may take a moment.")

        result = await design_generator.generate_360_view(
            original_prompt, original_image)

        if result.get("success"):
            for angle, image_url in result.get("images", {}).items():
                send_image(from_number, image_url, f"View: {angle}°")
        else:
            send_message(
                from_number,
                f"❌ Failed to generate 360° view: {result.get('error')}")
    except Exception as e:
        logger.error(f"Error generating 360 view: {str(e)}")
        send_message(from_number, "❌ An error occurred. Please try again.")


async def handle_improve_diamond(from_number: str, user_id: str):
    """Handle diamond improvement suggestions."""
    session = await get_user_session(user_id)
    diamond_id = session.get("last_diamond_id")

    if not diamond_id:
        send_message(
            from_number,
            "❌ No diamond found. Please upload a GIA certificate first.")
        return

    try:
        supabase = get_supabase_client()
        result = supabase.table("diamonds").select("*").eq(
            "id", diamond_id).execute()

        if not result.data:
            send_message(from_number, "❌ Diamond data not found.")
            return

        diamond_data = result.data[0]

        improvements = f"""💎 *Diamond Enhancement Analysis*

Current Specifications:
• Shape: {diamond_data.get('shape', 'N/A')}
• Carat: {diamond_data.get('carat', 'N/A')}
• Color: {diamond_data.get('primary_hue', 'N/A')}
• Clarity: {diamond_data.get('clarity', 'N/A')}
• Cut: {diamond_data.get('cut', 'N/A')}

🔬 Potential Enhancements:
[This feature will provide AI-powered recommendations for diamond treatment, recut options, and value optimization strategies]

Would you like to consult with our diamond experts?"""

        send_message(from_number, improvements)
    except Exception as e:
        logger.error(f"Error in improve diamond: {str(e)}")
        send_message(from_number, "❌ An error occurred. Please try again.")


async def handle_search_query(from_number: str, user_id: str, query: str,
                              intent_result: Dict):
    """Handle diamond search queries."""
    send_message(from_number, "🔍 Searching for diamonds...")

    search_result = await search_handler.search(query, intent_result)

    if search_result.get("success"):
        listings = search_result.get("listings", [])

        if not listings:
            send_message(
                from_number,
                "😔 No diamonds found matching your criteria. Try adjusting your search."
            )
            return

        # Send top 3 results
        for listing in listings[:3]:
            try:
                supabase = get_supabase_client()
                diamond_result = supabase.table("diamonds").select("*").eq(
                    "id", listing.get("diamond_id")).execute()

                if diamond_result.data:
                    diamond = diamond_result.data[0]
                    message = f"""💎 {diamond.get('shape', 'N/A')} Diamond

📊 Specs:
• Carat: {diamond.get('carat', 'N/A')}
• Color: {diamond.get('primary_hue', 'N/A')}
• Clarity: {diamond.get('clarity', 'N/A')}
• Cut: {diamond.get('cut', 'N/A')}
• Price: {listing.get('price', 'Contact for Price')}

Report: {diamond.get('certificate_number', 'N/A')}"""

                    images = listing.get("images", [])
                    if images and len(images) > 0:
                        send_image(from_number, images[0], message)
                    else:
                        send_message(from_number, message)
            except Exception as e:
                logger.error(f"Error fetching diamond data: {str(e)}")

        if len(listings) > 3:
            buttons = [{
                "id": "view_more_results",
                "title": f"📋 View All ({len(listings)})"
            }]
            send_interactive_buttons(from_number,
                                     f"Showing 3 of {len(listings)} results",
                                     buttons)
    else:
        send_message(from_number,
                     f"❌ Search failed: {search_result.get('error')}")


async def handle_view_more_results(from_number: str, user_id: str):
    """Handle viewing more search results."""
    send_message(
        from_number,
        "📋 Here are more results... [Implementation needed: retrieve cached search results]"
    )


async def handle_general_inquiry(from_number: str, user_id: str,
                                 question: str):
    """Handle general questions."""
    response = """Thank you for your question! 

Our diamond experts are here to help. For immediate assistance:
• Email: support@diamondbot.com
• Phone: +1-XXX-XXX-XXXX

Or continue chatting - I'll do my best to assist you!"""

    send_message(from_number, response)


# ======================================================================
# Webhook Verification (GET)
# ======================================================================
async def verify_webhook(request: Request):
    """Verify webhook setup from Meta."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return PlainTextResponse(content=challenge, status_code=200)
    else:
        logger.error("Webhook verification failed")
        return JSONResponse(status_code=403,
                            content={"error": "Invalid verification token"})


# ======================================================================
# Main Webhook Handler (POST)
# ======================================================================
async def handle_webhook(request: Request):
    """Handle incoming WhatsApp webhooks."""
    data = await request.json()
    logger.info(f"Webhook received: {json.dumps(data, indent=2)}")

    if data.get("object") != "whatsapp_business_account":
        return JSONResponse(status_code=404,
                            content={"error": "Not a WhatsApp event"})

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])

            for message in messages:
                from_number = message["from"]
                msg_type = message.get("type")

                try:
                    if msg_type == "text":
                        text = message.get("text", {}).get("body", "")
                        await handle_text_message(from_number, text)

                    elif msg_type == "audio":
                        media_id = message.get("audio", {}).get("id")
                        await handle_voice_message(from_number, media_id)

                    elif msg_type == "document":
                        media_id = message.get("document", {}).get("id")
                        filename = message.get("document",
                                               {}).get("filename",
                                                       "document.pdf")
                        mime_type = message.get("document",
                                                {}).get("mime_type", "")
                        await handle_document_message(from_number, media_id,
                                                      filename, mime_type)

                    elif msg_type == "image":
                        media_id = message.get("image", {}).get("id")
                        await handle_image_message(from_number, media_id)

                    elif msg_type == "interactive":
                        button_reply = message.get("interactive",
                                                   {}).get("button_reply", {})
                        list_reply = message.get("interactive",
                                                 {}).get("list_reply", {})

                        if button_reply:
                            button_id = button_reply.get("id")
                            await handle_button_response(
                                from_number, button_id)
                        elif list_reply:
                            list_id = list_reply.get("id")
                            await handle_button_response(from_number, list_id)

                    else:
                        send_message(
                            from_number,
                            "⚠️ Sorry, I can only process text, voice, images, and documents."
                        )

                except Exception as e:
                    logger.error(
                        f"Error processing message from {from_number}: {str(e)}"
                    )
                    send_message(
                        from_number,
                        "❌ An error occurred while processing your message. Please try again."
                    )

    return PlainTextResponse(content="EVENT_RECEIVED", status_code=200)
