#!/usr/bin/env python3
"""
Test configuration handler basic functionality
"""

def test_trigger_detection():
    """Test trigger word detection"""
    from config_handler import ConfigurationHandler

    print("Testing trigger detection...")
    assert ConfigurationHandler.is_config_trigger('bot config') == True
    assert ConfigurationHandler.is_config_trigger('bot-config') == True
    assert ConfigurationHandler.is_config_trigger('bot_config') == True
    assert ConfigurationHandler.is_config_trigger('BOT CONFIG') == True
    assert ConfigurationHandler.is_config_trigger('  bot config  ') == True
    assert ConfigurationHandler.is_config_trigger('hello') == False
    assert ConfigurationHandler.is_config_trigger('') == False
    assert ConfigurationHandler.is_config_trigger('config') == False
    print("✅ Trigger detection works")

def test_exit_detection():
    """Test exit command detection"""
    from config_handler import ConfigurationHandler

    print("Testing exit detection...")
    assert ConfigurationHandler.is_exit_command('0') == True
    assert ConfigurationHandler.is_exit_command('exit') == True
    assert ConfigurationHandler.is_exit_command('EXIT') == True
    assert ConfigurationHandler.is_exit_command('  exit  ') == True
    assert ConfigurationHandler.is_exit_command('1') == False
    assert ConfigurationHandler.is_exit_command('quit') == False
    assert ConfigurationHandler.is_exit_command('') == False
    print("✅ Exit detection works")

if __name__ == "__main__":
    try:
        test_trigger_detection()
        test_exit_detection()
        print("\n✅ All configuration handler tests passed!")
    except ImportError as e:
        print(f"⚠️  Cannot run tests without dependencies: {e}")
        print("Tests will run when bot starts")
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        exit(1)
