#!/usr/bin/env python3
"""
Test script for Perplexity API

Tests the Perplexity API key and configuration without running WhatsApp.

Usage:
    source venv/bin/activate && python test_perplexity.py
"""

import asyncio
import sys
import os

# Ensure we're in the right directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Check if running in venv
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print("❌ Error: Virtual environment not activated!")
    print("\nPlease run:")
    print("  source venv/bin/activate && python test_perplexity.py")
    sys.exit(1)

from config import get_config
from message_agent import PerplexityClient


async def test_perplexity():
    """Test Perplexity API with a simple query"""
    print("=" * 60)
    print("Testing Perplexity API Configuration")
    print("=" * 60)

    try:
        # Load configuration
        config = get_config()

        print(f"\n📋 Configuration:")
        print(f"  Model: {config.perplexity.model}")
        print(f"  Temperature: {config.perplexity.temperature}")
        print(f"  Max Tokens: {config.perplexity.max_tokens}")
        print(f"  API Key: {config.perplexity_api_key[:10]}...{config.perplexity_api_key[-4:]}")

        # Initialize Perplexity client
        client = PerplexityClient(
            api_key=config.perplexity_api_key,
            model=config.perplexity.model,
            temperature=config.perplexity.temperature,
            max_tokens=config.perplexity.max_tokens
        )

        # Test 1: Simple query
        print("\n" + "=" * 60)
        print("Test 1: Simple greeting")
        print("=" * 60)

        messages = [
            {"role": "system", "content": "You are a helpful assistant. Respond concisely."},
            {"role": "user", "content": "Say hello in one sentence."}
        ]

        print(f"\n📤 Sending: {messages[-1]['content']}")
        response = await client.chat_completion(messages)
        print(f"📥 Response: {response}")

        # Test 2: Context-aware query
        print("\n" + "=" * 60)
        print("Test 2: Context-aware conversation")
        print("=" * 60)

        messages = [
            {"role": "system", "content": "You are a personal assistant."},
            {"role": "user", "content": "My name is Oded"},
            {"role": "assistant", "content": "Nice to meet you, Oded!"},
            {"role": "user", "content": "What's my name?"}
        ]

        print(f"\n📤 Sending: {messages[-1]['content']}")
        print(f"   (with context of previous messages)")
        response = await client.chat_completion(messages)
        print(f"📥 Response: {response}")

        # Test 3: Empty message (should fail gracefully)
        print("\n" + "=" * 60)
        print("Test 3: Empty message (should fail)")
        print("=" * 60)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": ""}
        ]

        print(f"\n📤 Sending: (empty string)")
        try:
            response = await client.chat_completion(messages)
            print(f"📥 Response: {response}")
        except Exception as e:
            print(f"❌ Expected error: {e}")

        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_perplexity())
    sys.exit(0 if success else 1)
