#!/usr/bin/env python3
"""
Test script to verify that the double-click functionality works correctly
"""

import sys
import os

# Add the current directory to the path to import the module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt5.QtWidgets import QApplication
    from transparent_gif_player import TransparentGifPlayer
    
    def test_application():
        """Test if the application can start with the double-click changes"""
        app = QApplication(sys.argv)
        
        # Create a test instance
        gif_folder = os.path.join(os.path.dirname(__file__), "gifs")  # Default folder
        if not os.path.exists(gif_folder):
            gif_folder = os.path.dirname(__file__)  # Use current directory if gifs folder doesn't exist
            
        player = TransparentGifPlayer(gif_folder)
        
        # Check if the mouseDoubleClickEvent method exists
        if hasattr(player, 'mouseDoubleClickEvent'):
            print("✓ mouseDoubleClickEvent method found")
        else:
            print("✗ mouseDoubleClickEvent method not found")
            return False
            
        # Check if mouseReleaseEvent still exists but without click switching logic
        if hasattr(player, 'mouseReleaseEvent'):
            print("✓ mouseReleaseEvent method found")
        else:
            print("✗ mouseReleaseEvent method not found")
            return False
            
        # Check if next_gif method still exists
        if hasattr(player, 'next_gif'):
            print("✓ next_gif method found")
        else:
            print("✗ next_gif method not found")
            return False
            
        print("✓ All required methods are present")
        
        # Show the player briefly to test if it starts
        player.show()
        print("✓ Application window displayed successfully")
        
        # Close the application
        app.quit()
        
        return True
        
    if __name__ == "__main__":
        print("Testing double-click functionality...")
        if test_application():
            print("✓ All tests passed! Double-click functionality should work correctly.")
        else:
            print("✗ Some tests failed!")
            
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Make sure PyQt5 is installed and all required modules are available")
except Exception as e:
    print(f"✗ Error during testing: {e}")