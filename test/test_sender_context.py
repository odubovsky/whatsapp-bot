#!/usr/bin/env python3
"""
Test to demonstrate sender context feature
"""

def test_sender_formatting():
    """Test how sender information is formatted in messages"""

    # Simulate the formatting logic
    def format_user_message(message: str, sender: str = None) -> str:
        """Format user message with sender context"""
        if sender:
            return f"[Message from: {sender}]\n{message}"
        return message

    def format_context_entry(message: str, sender: str = None) -> str:
        """Format context entry with sender"""
        if sender:
            return f"[From: {sender}] {message}"
        return message

    # Test cases
    print("Testing sender context formatting:\n")

    # Test 1: Current message with sender
    current_msg = "היי בוט מה השעה"
    sender = "972501234567"
    formatted = format_user_message(current_msg, sender)
    print("1. Current message to LLM:")
    print(f"   {formatted}\n")

    # Test 2: Context entry with sender
    context_msg = "ספר לי על דלתא גליל"
    context_sender = "107181009580152"
    formatted_context = format_context_entry(context_msg, context_sender)
    print("2. Context entry:")
    print(f"   USER: {formatted_context}\n")

    # Test 3: Multiple senders in context
    print("3. Example conversation context with multiple senders:")
    context = [
        ("היי בוט מה קורה", "972501234567"),
        ("שלום! איך אני יכול לעזור?", None),  # Bot response
        ("תגיד לי על החברה", "107181009580152"),
        ("כמובן! מה תרצה לדעת?", None),  # Bot response
    ]

    for msg, sender in context:
        if sender:
            print(f"   USER: {format_context_entry(msg, sender)}")
        else:
            print(f"   ASSISTANT: {msg}")

    print("\n✅ All tests completed!")
    print("\nHow this helps:")
    print("- LLM can see who sent each message")
    print("- Can personalize responses based on sender")
    print("- Can use he/she/they pronouns appropriately")
    print("- Can reference 'the other person' vs 'you' correctly")

if __name__ == "__main__":
    test_sender_formatting()
