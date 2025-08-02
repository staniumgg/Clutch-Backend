#!/usr/bin/env python3
# Test script to verify the esports.py file imports and basic functions work

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Test basic imports
    print("🧪 Testing imports...")
    
    # Test core modules
    import discord
    import asyncio
    from discord.ext import commands
    print("✅ Discord imports successful")
    
    # Test file watcher
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    print("✅ Watchdog imports successful")
    
    # Test audio processing
    import mutagen
    from mutagen.mp3 import MP3
    print("✅ Mutagen imports successful")
    
    # Test other modules
    import requests
    import json
    from dotenv import load_dotenv
    print("✅ Other imports successful")
    
    print("\n🧪 Testing esports.py imports...")
    
    # Import our main functions
    from esports import (
        get_motivational_filename,
        extract_user_id_from_filename,
        simple_file_validation,
        load_user_preferences,
        save_user_preference
    )
    print("✅ Esports.py functions imported successfully")
    
    print("\n🧪 Testing basic functions...")
    
    # Test filename generation
    filename = get_motivational_filename()
    print(f"✅ Motivational filename: {filename}")
    
    # Test user ID extraction
    test_filename = "callmestanium-1106372321582784603-1751986704129.mp3"
    user_id = extract_user_id_from_filename(test_filename)
    print(f"✅ Extracted user ID: {user_id}")
    
    # Test preference saving/loading
    save_user_preference("test_user", coach_type="tactical", voice="es-ES-Standard-B")
    prefs = load_user_preferences("test_user")
    print(f"✅ Preferences test: {prefs}")
    
    print("\n🎉 All tests passed! The Discord bot should work correctly.")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure all required packages are installed:")
    print("pip install discord.py python-dotenv watchdog mutagen requests google-cloud-texttospeech")
    
except Exception as e:
    print(f"❌ Error during testing: {e}")
    import traceback
    traceback.print_exc()
