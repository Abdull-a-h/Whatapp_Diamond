#!/usr/bin/env python3
"""
Quick test script for WhatsApp Diamond Bot
Tests basic functionality without needing actual WhatsApp messages
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_intent_detection():
    """Test intent detection service"""
    print("\n🧪 Testing Intent Detection...")

    from app.services.intent_detector import IntentDetector

    detector = IntentDetector()

    test_queries = [
        "Show me oval diamonds", "Design a ring",
        "I want to create custom jewelry with my diamond", "Make it gold",
        "Try again", "What is diamond clarity?", "List my diamond for sale"
    ]

    for query in test_queries:
        result = await detector.detect(query, {"step": "idle"})
        print(f"  Query: '{query}'")
        print(
            f"  Intent: {result.get('intent')} (confidence: {result.get('confidence')})"
        )
        print(f"  Entities: {result.get('entities')}\n")

    print("✅ Intent Detection Test Complete\n")


async def test_gia_extraction():
    """Test GIA extraction service"""
    print("🧪 Testing GIA Extraction...")

    from app.services.gia_extractor import GIAExtractor

    extractor = GIAExtractor()

    # Test with placeholder
    result = await extractor.extract_from_image("https://example.com/gia.jpg")

    if result.get("success"):
        data = result.get("data")
        print(f"  Report Number: {data.get('report_number')}")
        print(f"  Shape: {data.get('shape')}")
        print(f"  Carat: {data.get('carat')}")
        print(f"  Color: {data.get('color')}")
        print(f"  Clarity: {data.get('clarity')}")
        print(f"  Cut: {data.get('cut')}")

    print("✅ GIA Extraction Test Complete\n")


async def test_design_generation():
    """Test design generation service"""
    print("🧪 Testing Design Generation...")

    from app.services.design_generator import DesignGenerator

    generator = DesignGenerator()

    # Test free design
    result = await generator.free_design("elegant gold ring with diamonds")

    if result.get("success"):
        print(f"  Generated Image URL: {result.get('image_url')}")
        print(f"  Prompt Used: {result.get('prompt')[:100]}...")
    else:
        print(f"  Error: {result.get('error')}")

    print("✅ Design Generation Test Complete\n")


async def test_search():
    """Test search handler"""
    print("🧪 Testing Search Handler...")

    from app.services.search_handler import SearchHandler

    handler = SearchHandler()

    intent_result = {
        "intent": "search",
        "entities": {
            "shape": "Oval",
            "carat_min": 2.0
        }
    }

    result = await handler.search("oval diamonds 2 carats", intent_result)

    if result.get("success"):
        print(f"  Found {result.get('count')} listings")
        for listing in result.get('listings', [])[:3]:
            gia = listing.get('gia_data', {})
            print(
                f"    - {gia.get('shape')} {gia.get('carat')}ct, {gia.get('color')}, {gia.get('clarity')}"
            )
    else:
        print(f"  Search Error: {result.get('error')}")

    print("✅ Search Handler Test Complete\n")


async def test_voice_transcription():
    """Test voice transcription"""
    print("🧪 Testing Voice Transcription...")

    from app.services.voice_transcriber import VoiceTranscriber

    transcriber = VoiceTranscriber()

    # Test with mock audio
    result = await transcriber.transcribe(b"mock_audio_data")

    if result.get("success"):
        print(f"  Transcribed Text: {result.get('text')}")
        print(f"  Language: {result.get('language')}")
        print(f"  Confidence: {result.get('confidence')}")
    else:
        print(f"  Error: {result.get('error')}")

    print("✅ Voice Transcription Test Complete\n")


async def test_database_connection():
    """Test database connection"""
    print("🧪 Testing Database Connection...")

    try:
        from app.database.supabase_client import get_supabase_client

        supabase = get_supabase_client()
        response = supabase.table("users").select("id").limit(1).execute()

        print(f"  ✅ Database Connected Successfully")
        print(f"  Response: {response.data}")
    except Exception as e:
        print(f"  ❌ Database Connection Failed: {str(e)}")

    print("✅ Database Connection Test Complete\n")


async def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("WhatsApp Diamond Bot - Test Suite")
    print("=" * 60)

    try:
        # Test each component
        await test_intent_detection()
        await test_gia_extraction()
        await test_design_generation()
        await test_search()
        await test_voice_transcription()
        await test_database_connection()

        print("\n" + "=" * 60)
        print("✅ All Tests Complete!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Test Suite Failed: {str(e)}\n")
        import traceback
        traceback.print_exc()


def main():
    """Main test runner"""
    print("\nStarting WhatsApp Diamond Bot Tests...\n")
    print(
        "Note: These tests use placeholder APIs when keys are not configured.\n"
    )

    # Run async tests
    asyncio.run(run_all_tests())


if __name__ == "__main__":
    main()
