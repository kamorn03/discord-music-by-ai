"""
Configuration file for Discord Music Bot
Loads settings from environment variables / .env file
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Discord Bot Token - Get from https://discord.com/developers/applications
BOT_TOKEN = os.getenv("DISCORD_TOKEN", "")

# Discord Application ID
APP_ID = os.getenv("DISCORD_APP_ID", "")

# Command prefix for text commands
PREFIX = os.getenv("BOT_PREFIX", "!")

# Lavalink server configuration
LAVALINK_URI = os.getenv("LAVALINK_URI", "http://localhost:2333")
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")

# Debug: Print config on load
print(f"[CONFIG] LAVALINK_URI = {LAVALINK_URI}")
print(f"[CONFIG] LAVALINK_PASSWORD = {LAVALINK_PASSWORD}")

# Spotify Configuration (optional)
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET", "")

# yt-dlp cookies + cache
YTDLP_ENABLED = os.getenv("YTDLP_ENABLED", "false").lower() == "true"
YTDLP_COOKIES_PATH = os.getenv("YTDLP_COOKIES_PATH", "./cookies/cookies.txt")
YTDLP_CACHE_TTL = int(os.getenv("YTDLP_CACHE_TTL", "1800"))
