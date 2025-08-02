import discord
from discord.ext import commands
import asyncio
import PIL.ImageGrab
import os
from score_detector import ScoreDetector
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord_bot')

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Initialize score detector
score_detector = ScoreDetector()

# Store active monitoring sessions
active_monitors = {}

@bot.event
async def on_ready():
    logger.info(f'Bot is ready! Logged in as {bot.user.name}')

@bot.command()
async def join(ctx):
    """Join the user's voice channel"""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
        await ctx.send(f'Joined {channel.name}')
    else:
        await ctx.send('You need to be in a voice channel first!')

@bot.command()
async def leave(ctx):
    """Leave the voice channel"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send('Left the voice channel')
    else:
        await ctx.send('I am not in a voice channel')

@bot.command()
async def calibrate(ctx):
    """Start calibration process for score regions"""
    if not ctx.voice_client:
        await ctx.send('I need to be in a voice channel first! Use !join')
        return

    # Take a screenshot of the screen share
    screenshot = None  # TODO: Implement screen capture
    if screenshot:
        # Save screenshot temporarily
        temp_path = 'temp_calibration.png'
        screenshot.save(temp_path)
        
        # Use score detector's calibration
        score_detector.select_regions(temp_path)
        
        # Clean up
        os.remove(temp_path)
        await ctx.send('Calibration complete! Use !monitor to start score monitoring')
    else:
        await ctx.send('No screen share detected')

@bot.command()
async def monitor(ctx):
    """Start monitoring scores from the screen share"""
    if not ctx.voice_client:
        await ctx.send('I need to be in a voice channel first! Use !join')
        return

    if not score_detector.regions:
        await ctx.send('Please calibrate the score regions first using !calibrate')
        return

    # Start monitoring in this channel
    active_monitors[ctx.channel.id] = True
    await ctx.send('Score monitoring started! Use !stop to stop monitoring')

    while active_monitors.get(ctx.channel.id):
        # TODO: Implement screen capture and score detection
        await asyncio.sleep(1)  # Adjust delay as needed

@bot.command()
async def stop(ctx):
    """Stop monitoring scores"""
    if ctx.channel.id in active_monitors:
        active_monitors[ctx.channel.id] = False
        await ctx.send('Score monitoring stopped')
    else:
        await ctx.send('No active monitoring in this channel')

# Add your Discord bot token here
TOKEN = 'YOUR_BOT_TOKEN'
bot.run(TOKEN)