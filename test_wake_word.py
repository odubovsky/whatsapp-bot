#!/usr/bin/env python3
"""
Quick test for wake word detection functionality
"""

from message_agent import MessageAgent

def test_wake_word_detection():
    """Test wake word detection"""

    print("Testing wake word detection...\n")

    test_cases = [
        # (input, expected_has_wake, expected_stripped)
        # English variations
        ("hey bot what time is it", True, "what time is it"),
        ("HEY BOT hello", True, "hello"),
        ("Hey Bot test", True, "test"),
        ("hello bot how are you", True, "how are you"),
        ("HELLO BOT test", True, "test"),
        ("hi bot what's up", True, "what's up"),
        ("Hi Bot!", True, "!"),

        # Hebrew variations
        ("הי בוט מה השעה", True, "מה השעה"),
        ("היי בוט ספר לי על חברת דלתא גליל", True, "ספר לי על חברת דלתא גליל"),
        ("הלו בוט שלום", True, "שלום"),

        # Non-wake word messages
        ("hello everyone", False, "hello everyone"),
        ("", False, ""),
        ("היי", False, "היי"),
        ("I said hey bot yesterday", False, "I said hey bot yesterday"),

        # Edge cases
        ("hey bot", True, ""),
        ("hey bot   test", True, "test"),
        ("Hey bot, what time is it?", True, ", what time is it?"),
        ("hello bot", True, ""),
    ]

    passed = 0
    failed = 0

    for content, expected_has_wake, expected_stripped in test_cases:
        has_wake, stripped = MessageAgent.check_and_strip_wake_word(content)

        if has_wake == expected_has_wake and stripped == expected_stripped:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1
            print(f"  Expected: has_wake={expected_has_wake}, stripped='{expected_stripped}'")
            print(f"  Got:      has_wake={has_wake}, stripped='{stripped}'")

        input_preview = content[:30] + "..." if len(content) > 30 else content
        print(f"{status} | Input: '{input_preview}'")

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")

    return failed == 0

if __name__ == "__main__":
    success = test_wake_word_detection()
    exit(0 if success else 1)
