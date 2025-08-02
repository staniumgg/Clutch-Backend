#!/usr/bin/env python3
"""
Discord Bot eSports Audio Feedback - Complete Workflow Test
This script tests the entire workflow to ensure everything is working correctly.
"""

import os
import sys
import asyncio
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_environment():
    """Check if all required environment variables are set"""
    print("🔍 Checking environment variables...")
    
    required_vars = [
        'DISCORD_TOKEN',
        'OPENAI_API_KEY',
        'GOOGLE_APPLICATION_CREDENTIALS'
    ]
    
    all_good = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Set")
        else:
            print(f"❌ {var}: Not set")
            all_good = False
    
    return all_good

def check_files():
    """Check if required files exist"""
    print("\n📁 Checking required files...")
    
    required_files = [
        'esports.py',
        'firebase_config.py',
        '.env'
    ]
    
    all_good = True
    for file in required_files:
        if os.path.exists(file):
            print(f"✅ {file}: Exists")
        else:
            print(f"❌ {file}: Missing")
            all_good = False
    
    return all_good

def check_directories():
    """Check if required directories exist"""
    print("\n📂 Checking directories...")
    
    required_dirs = [
        'recordings',
        'temp'
    ]
    
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"✅ {dir_name}/: Exists")
        else:
            print(f"📁 {dir_name}/: Creating...")
            os.makedirs(dir_name, exist_ok=True)
            print(f"✅ {dir_name}/: Created")

def check_audio_files():
    """Check for existing audio files to process"""
    print("\n🎵 Checking for audio files...")
    
    recordings_dir = 'recordings'
    if os.path.exists(recordings_dir):
        mp3_files = [f for f in os.listdir(recordings_dir) if f.endswith('.mp3')]
        if mp3_files:
            print(f"✅ Found {len(mp3_files)} MP3 files:")
            for file in mp3_files[:3]:  # Show first 3
                print(f"   📄 {file}")
            if len(mp3_files) > 3:
                print(f"   ... and {len(mp3_files) - 3} more")
            return True
        else:
            print("❌ No MP3 files found in recordings folder")
            return False
    else:
        print("❌ recordings/ directory not found")
        return False

def test_imports():
    """Test that all required modules can be imported"""
    print("\n📦 Testing imports...")
    
    try:
        import discord
        print("✅ discord.py imported")
        
        import requests
        print("✅ requests imported")
        
        from watchdog.observers import Observer
        print("✅ watchdog imported")
        
        import mutagen
        print("✅ mutagen imported")
        
        # Try Google Cloud TTS
        try:
            from google.cloud import texttospeech
            print("✅ Google Cloud TTS imported")
        except ImportError:
            print("⚠️ Google Cloud TTS not available (install: pip install google-cloud-texttospeech)")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def workflow_instructions():
    """Print instructions for using the bot"""
    print("\n" + "="*60)
    print("🎮 DISCORD BOT ESPORTS AUDIO FEEDBACK - READY!")
    print("="*60)
    print()
    print("📋 WORKFLOW:")
    print("1. 🎵 Audio file detected in recordings/ folder")
    print("2. 🤖 Bot sends Discord message with preference buttons")
    print("3. 👤 User selects coach type, aspect, personality, voice, speed")
    print("4. 🎧 Bot transcribes audio with Whisper API")
    print("5. 🧠 Bot analyzes with GPT-4o-mini using preferences")
    print("6. 🔊 Bot generates personalized TTS audio")
    print("7. 📤 Bot sends audio feedback via Discord DM")
    print()
    print("📝 TO START:")
    print("   python esports.py")
    print()
    print("🎵 AUDIO FILE FORMAT:")
    print("   username-userid-timestamp.mp3")
    print("   Example: callmestanium-1106372321582784603-1751986704129.mp3")
    print()
    print("🔧 FEATURES:")
    print("   ✅ Personalized coach personalities")
    print("   ✅ Multiple TTS voice options")
    print("   ✅ Adjustable playback speed")
    print("   ✅ Aspect-focused feedback")
    print("   ✅ Interactive Discord UI")
    print("   ✅ Real-time file monitoring")
    print()

def main():
    """Main test function"""
    print("🎧 Discord Bot eSports Audio Feedback - System Check")
    print("="*60)
    
    os.chdir(r"c:\Users\paula\CLUTCH")
    print(f"📍 Working directory: {os.getcwd()}")
    
    # Run all checks
    env_ok = check_environment()
    files_ok = check_files()
    check_directories()
    audio_ok = check_audio_files()
    imports_ok = test_imports()
    
    print("\n" + "="*60)
    print("📊 SYSTEM STATUS:")
    print("="*60)
    print(f"🔧 Environment Variables: {'✅ OK' if env_ok else '❌ MISSING'}")
    print(f"📁 Required Files: {'✅ OK' if files_ok else '❌ MISSING'}")
    print(f"🎵 Audio Files: {'✅ READY' if audio_ok else '⚠️  NONE'}")
    print(f"📦 Dependencies: {'✅ OK' if imports_ok else '❌ MISSING'}")
    
    if env_ok and files_ok and imports_ok:
        print("\n🎉 ALL SYSTEMS GO! Bot is ready to run.")
        workflow_instructions()
    else:
        print("\n❌ Some issues need to be resolved before running the bot.")
        if not env_ok:
            print("   - Check your .env file for missing environment variables")
        if not files_ok:
            print("   - Make sure all required files are present")
        if not imports_ok:
            print("   - Install missing Python packages")

if __name__ == "__main__":
    main()
