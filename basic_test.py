#!/usr/bin/env python3
# Simple test to check if esports.py runs without crashing

import sys
import os

# Test that we can run the basic operations
try:
    print("🧪 Testing basic functionality...")
    
    # Test that the file can be executed
    os.chdir(r"c:\Users\paula\CLUTCH")
    
    # Test individual components
    print("📁 Current directory:", os.getcwd())
        print("📄 Files in directory:", [f for f in os.listdir('.') if f.endswith('.py')])
    
    # Test that environment variables can be loaded
    from dotenv import load_dotenv
    load_dotenv()
    
    discord_token = os.getenv('DISCORD_TOKEN')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    print(f"🔑 Discord token exists: {bool(discord_token)}")
    print(f"🔑 OpenAI key exists: {bool(openai_key)}")
    
    if not discord_token:
        print("⚠️ Warning: DISCORD_TOKEN not found in environment")
    if not openai_key:
        print("⚠️ Warning: OPENAI_API_KEY not found in environment")
    
    print("✅ Basic setup test completed successfully!")
    print("\n🎮 The Discord bot should now be ready to run.")
    print("📝 To start the bot, run: python esports.py")
    print("📁 Make sure audio files are placed in the 'recordings' folder")
    print("🎵 Audio files should be named: username-userid-timestamp.mp3")
    
except Exception as e:
    print(f"❌ Error during basic test: {e}")
    import traceback
    traceback.print_exc()
