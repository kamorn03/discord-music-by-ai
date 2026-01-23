# Discord Music Bot

A Discord music bot that plays music from YouTube and Spotify. Built with discord.py and wavelink.

## Features

- Play music from YouTube (URLs and search)
- Play music from Spotify (tracks, albums, playlists)
- Queue management (add, remove, shuffle, clear)
- Loop modes (track, queue)
- Volume control
- Seek functionality
- Progress bar display
- Slash commands and text commands support
- Docker deployment ready

## Quick Start with Docker (Recommended)

### Step 1: Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Copy the **Application ID** from the General Information page
4. Go to the "Bot" tab
5. Click "Reset Token" and copy your **Bot Token**
6. Enable these **Privileged Gateway Intents**:
   - MESSAGE CONTENT INTENT
   - SERVER MEMBERS INTENT (optional)
7. Go to "OAuth2" > "URL Generator"
8. Select scopes: `bot`, `applications.commands`
9. Select permissions:
   - Send Messages
   - Embed Links
   - Connect
   - Speak
   - Use Voice Activity
10. Copy the generated URL and open it to invite the bot to your server

### Step 2: Configure Environment

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your values:
   ```env
   DISCORD_TOKEN=your_discord_bot_token_here
   DISCORD_APP_ID=your_application_id_here
   ```

3. (Optional) For Spotify support, add Spotify credentials from [Spotify Developer Dashboard](https://developer.spotify.com/dashboard):
   ```env
   SPOTIFY_CLIENT_ID=your_spotify_client_id
   SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
   ```

### Step 3: Deploy with Docker

```bash
# Build and start both bot and Lavalink
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the bot
docker-compose down
```

That's it! The bot should now be online in your Discord server.

## Manual Setup (Without Docker)

### Step 1: Set Up Lavalink Server

The bot requires a Lavalink server for audio playback.

#### Option A: Use Docker for Lavalink only

```bash
docker run -d \
  --name lavalink \
  -p 2333:2333 \
  -v $(pwd)/application.yml:/opt/Lavalink/application.yml \
  ghcr.io/lavalink-devs/lavalink:4
```

#### Option B: Run Lavalink Manually

1. Download [Lavalink.jar](https://github.com/lavalink-devs/Lavalink/releases)
2. Place it in the same folder as `application.yml`
3. Run: `java -jar Lavalink.jar`

### Step 2: Configure and Run Bot

1. Copy `.env.example` to `.env` and fill in your values
2. Update `LAVALINK_URI` in `.env` to `http://localhost:2333`
3. Install dependencies and run:
   ```bash
   pip install -r requirements.txt
   python bot.py
   ```

## Project Structure

```
discord-music-bot/
├── bot.py              # Main bot code
├── config.py           # Configuration loader
├── requirements.txt    # Python dependencies
├── Dockerfile          # Bot container image
├── docker-compose.yml  # Full stack deployment
├── application.yml     # Lavalink configuration
├── .env.example        # Environment template
└── .env                # Your secrets (git-ignored)
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DISCORD_TOKEN` | Your Discord bot token | Yes |
| `DISCORD_APP_ID` | Your Discord application ID | Yes |
| `BOT_PREFIX` | Command prefix (default: `!`) | No |
| `LAVALINK_URI` | Lavalink server URL | No |
| `LAVALINK_PASSWORD` | Lavalink password | No |
| `SPOTIFY_CLIENT_ID` | Spotify client ID | No |
| `SPOTIFY_CLIENT_SECRET` | Spotify client secret | No |

## Commands

| Command | Aliases | Description |
|---------|---------|-------------|
| `!play <query>` | `!p` | Play a song (URL or search) |
| `!pause` | - | Pause the current song |
| `!resume` | - | Resume playback |
| `!skip` | `!s` | Skip current song |
| `!stop` | - | Stop and clear queue |
| `!queue` | `!q` | Show the queue |
| `!nowplaying` | `!np` | Show current song |
| `!volume <0-100>` | `!vol` | Set volume |
| `!shuffle` | - | Shuffle the queue |
| `!loop [mode]` | - | Loop: off/track/queue |
| `!seek <seconds>` | - | Seek to position |
| `!remove <pos>` | - | Remove from queue |
| `!clear` | - | Clear the queue |
| `!join` | - | Join voice channel |
| `!leave` | `!dc` | Leave voice channel |
| `!help` | - | Show all commands |

All commands also work as slash commands (e.g., `/play`, `/skip`)

## Examples

```
!play never gonna give you up
!play https://www.youtube.com/watch?v=dQw4w9WgXcQ
!play https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8
!play https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
```

## Troubleshooting

### Bot doesn't respond
- Check if the bot is online: `docker-compose ps`
- View bot logs: `docker-compose logs bot`
- Verify the bot has the correct permissions
- Make sure MESSAGE CONTENT INTENT is enabled

### No audio
- Ensure Lavalink is running: `docker-compose logs lavalink`
- Wait 30 seconds after starting for Lavalink to fully initialize
- Verify the bot has Connect and Speak permissions in voice channel

### Spotify not working
- Make sure you've added Spotify credentials in `.env`
- Also update `application.yml` with Spotify credentials
- Restart containers: `docker-compose restart`

### Container keeps restarting
- Check logs: `docker-compose logs -f`
- Verify your `.env` file has valid tokens
- Ensure ports aren't already in use

## License

MIT License
