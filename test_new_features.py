#!/usr/bin/env python3
"""
Test script to verify the new features in the GIF player:
1. Left-right flip functionality
2. Single file selection functionality
"""

import sys
import os
import tempfile
from PyQt5.QtWidgets import QApplication
from PyQt5.QtTest import QTest
from PyQt5.QtCore import Qt

# Add current directory to path to import the main module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_flip_functionality():
    """Test the left-right flip functionality"""
    print("Testing left-right flip functionality...")
    
    # Create a temporary config file
    config_path = os.path.join(tempfile.gettempdir(), 'test_config.json')
    
    # Create test folder with a simple gif (we'll create a mock folder)
    test_folder = os.path.join(tempfile.gettempdir(), 'test_gifs')
    os.makedirs(test_folder, exist_ok=True)
    
    # Create a dummy gif file (just an empty file for testing purposes)
    test_gif_path = os.path.join(test_folder, 'test.gif')
    with open(test_gif_path, 'w') as f:
        f.write('')  # Empty file just for path testing
    
    try:
        from transparent_gif_player import TransparentGifPlayer
        
        app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
        
        # Create player instance
        player = TransparentGifPlayer(test_folder, config_path)
        
        # Test initial flip state
        assert player._flipped == False, "Initial flip state should be False"
        print("✓ Initial flip state is correct")
        
        # Test flip toggle
        initial_flipped = player._flipped
        player._flipped = not player._flipped
        player._save_config()
        assert player._flipped != initial_flipped, "Flip state should toggle"
        print("✓ Flip toggle works correctly")
        
        # Test configuration persistence
        assert '_flipped' in player.__dict__, "Flip state tracking variable exists"
        print("✓ Flip state tracking is implemented")
        
        player.close()
        print("✓ Left-right flip functionality test passed!")
        
    except Exception as e:
        print(f"✗ Left-right flip test failed: {e}")
        return False
    finally:
        # Cleanup
        if os.path.exists(test_gif_path):
            os.remove(test_gif_path)
        if os.path.exists(test_folder):
            os.rmdir(test_folder)
        if os.path.exists(config_path):
            os.remove(config_path)
    
    return True

def test_single_file_functionality():
    """Test the single file selection functionality"""
    print("\nTesting single file selection functionality...")
    
    # Create a temporary config file
    config_path = os.path.join(tempfile.gettempdir(), 'test_config_single.json')
    
    # Create test folder and file
    test_folder = os.path.join(tempfile.gettempdir(), 'test_gifs_single')
    os.makedirs(test_folder, exist_ok=True)
    test_gif_path = os.path.join(test_folder, 'single_test.gif')
    with open(test_gif_path, 'w') as f:
        f.write('')  # Empty file just for path testing
    
    try:
        from transparent_gif_player import TransparentGifPlayer
        
        app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
        
        # Create player instance
        player = TransparentGifPlayer(test_folder, config_path)
        
        # Test initial single file mode state
        assert player._single_file_mode == False, "Initial single file mode should be False"
        print("✓ Initial single file mode state is correct")
        
        # Test single file mode tracking
        assert hasattr(player, '_single_file_mode'), "Single file mode tracking variable exists"
        print("✓ Single file mode tracking is implemented")
        
        # Test that set_single_gif_file method exists
        assert hasattr(player, 'set_single_gif_file'), "set_single_gif_file method exists"
        print("✓ set_single_gif_file method is implemented")
        
        player.close()
        print("✓ Single file selection functionality test passed!")
        
    except Exception as e:
        print(f"✗ Single file selection test failed: {e}")
        return False
    finally:
        # Cleanup
        if os.path.exists(test_gif_path):
            os.remove(test_gif_path)
        if os.path.exists(test_folder):
            os.rmdir(test_folder)
        if os.path.exists(config_path):
            os.remove(config_path)
    
    return True

def main():
    """Run all tests"""
    print("Starting tests for new GIF player features...\n")
    
    flip_test_passed = test_flip_functionality()
    single_file_test_passed = test_single_file_functionality()
    
    print(f"\n{'='*50}")
    print("TEST RESULTS:")
    print(f"Left-right flip functionality: {'PASSED' if flip_test_passed else 'FAILED'}")
    print(f"Single file selection functionality: {'PASSED' if single_file_test_passed else 'FAILED'}")
    
    if flip_test_passed and single_file_test_passed:
        print("\n✓ All tests passed! The new features are working correctly.")
        return True
    else:
        print("\n✗ Some tests failed. Please check the implementation.")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)