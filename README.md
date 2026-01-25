# Discord Music Bot

A feature-rich Discord music bot that plays music from YouTube and Spotify. Built with discord.py and wavelink, inspired by [PrimeMusic-Lavalink](https://github.com/GlaceYT/PrimeMusic-Lavalink).

## Features

- Play music from YouTube (URLs and search)
- Play music from Spotify (tracks, albums, playlists)
- Play music from SoundCloud (with fallback)
- Queue management (add, remove, shuffle, clear)
- Loop modes (track, queue)
- Volume control with server defaults
- Seek functionality
- Progress bar display
- **Audio Filters** (bassboost, nightcore, vaporwave, 8D, karaoke, etc.)
- **Autoplay Mode** - Automatically plays similar songs when queue is empty
- **24/7 Mode** - Bot stays in channel even when no one is listening
- **Playlist System** - Create, save, load, and manage personal playlists
- Slash commands and text commands support
- SQLite database for persistent settings
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

4. (Optional) For improved YouTube reliability, add YouTube OAuth token:
   - Follow the guide: [YouTube OAuth Setup](https://github.com/lavalink-devs/youtube-source#oauth-setup)
   - Add to `.env`:
     ```env
     YOUTUBE_REFRESH_TOKEN=your_youtube_refresh_token
     ```
   - **Note:** This is optional but recommended for better YouTube playback reliability

5. (Optional) For age-restricted videos, enable yt-dlp:
   - Export cookies from your browser using a browser extension:
     - Chrome: [Get cookies.txt](https://chrome.google.com/webstore/detail/get-cookiestxt/bgaddhkoddajcdgocldbbfleckgcbcid)
     - Firefox: [cookies.txt](https://addons.mozilla.org/en-US/firefox/addon/cookies-txt/)
   - Save cookies file to `./cookies/cookies.txt`
   - Enable in `.env`:
     ```env
     YTDLP_ENABLED=true
     YTDLP_COOKIES_PATH=./cookies/cookies.txt
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
├── bot.py              # Main bot code with all commands
├── config.py           # Configuration loader
├── database.py         # SQLite database for playlists/settings
├── requirements.txt    # Python dependencies
├── Dockerfile          # Bot container image
├── docker-compose.yml  # Full stack deployment
├── application.yml     # Lavalink configuration
├── .env.example        # Environment template
├── .env                # Your secrets (git-ignored)
├── data/               # Database storage (Docker)
│   └── music_bot.db    # SQLite database
└── cookies/            # YouTube cookies (optional)
    └── cookies.txt
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

### Music Playback
| Command | Aliases | Description |
|---------|---------|-------------|
| `!play <query>` | `!p` | Play a song (URL or search) |
| `!pause` | - | Pause the current song |
| `!resume` | - | Resume playback |
| `!skip` | `!s` | Skip current song |
| `!stop` | - | Stop and clear queue |
| `!seek <seconds>` | - | Seek to position |

### Queue Management
| Command | Aliases | Description |
|---------|---------|-------------|
| `!queue` | `!q` | Show the queue |
| `!nowplaying` | `!np` | Show current song |
| `!shuffle` | - | Shuffle the queue |
| `!loop [mode]` | - | Loop: off/track/queue |
| `!remove <pos>` | - | Remove from queue |
| `!clear` | - | Clear the queue |

### Audio Filters
| Command | Aliases | Description |
|---------|---------|-------------|
| `!filter [name]` | `!f` | Apply audio filter |
| `!bassboost` | `!bass`, `!bb` | Apply bassboost |
| `!nightcore` | `!nc` | Apply nightcore |
| `!vaporwave` | `!vw` | Apply vaporwave |
| `!clearfilter` | `!cf` | Remove all filters |

**Available Filters:** bassboost, nightcore, vaporwave, 8d, karaoke, tremolo, vibrato, lowpass, soft, loud

### Special Features
| Command | Aliases | Description |
|---------|---------|-------------|
| `!autoplay` | `!ap` | Toggle autoplay mode |
| `!247` | `!stay` | Toggle 24/7 mode |

### Playlist Commands
| Command | Description |
|---------|-------------|
| `!playlist create <name>` | Create a new playlist |
| `!playlist delete <name>` | Delete a playlist |
| `!playlist save <name>` | Save current queue to playlist |
| `!playlist load <name>` | Load a playlist to queue |
| `!playlist list` | Show your playlists |
| `!playlist show <name>` | Show tracks in a playlist |

### General
| Command | Aliases | Description |
|---------|---------|-------------|
| `!join` | - | Join voice channel |
| `!leave` | `!dc` | Leave voice channel |
| `!volume <0-100>` | `!vol` | Set volume |
| `!setvolume <0-100>` | `!setvol` | Set default server volume |
| `!help` | - | Show all commands |

All commands also work as slash commands (e.g., `/play`, `/skip`, `/filter`)

## Examples

```
!play never gonna give you up
!play https://www.youtube.com/watch?v=dQw4w9WgXcQ
!play https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8
!play https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M
```

## Troubleshooting

### Bot doesn't respond to commands
- **Check bot status:** `docker-compose ps`
- **View bot logs:** `docker-compose logs bot`
- **Verify permissions:** Ensure bot has "Send Messages" and "Embed Links" permissions
- **Check intents:** Make sure MESSAGE CONTENT INTENT is enabled in Discord Developer Portal
- **Slash commands not showing:** Wait a few minutes after bot starts, or try kicking and re-inviting the bot

### No audio / Music doesn't play
- **Check Lavalink:** Ensure Lavalink is running: `docker-compose logs lavalink`
- **Wait for initialization:** Lavalink takes 30-60 seconds to fully start
- **Verify permissions:** Bot needs "Connect" and "Speak" permissions in voice channel
- **Check node connection:** Look for "Wavelink node is ready!" in bot logs
- **Network issues:** Ensure port 2333 is accessible between bot and Lavalink

### YouTube playback issues
- **403 Forbidden errors:**
  - Add YouTube OAuth token (see Step 2.4 in setup)
  - Or enable yt-dlp with cookies (see Step 2.5 in setup)
- **Age-restricted videos:**
  - Enable yt-dlp with valid cookies file
  - Set `YTDLP_ENABLED=true` in `.env`
- **Rate limiting:**
  - Add YouTube OAuth token for higher rate limits
  - Use yt-dlp as fallback

### Spotify not working
- **Check credentials:** Make sure you've added Spotify credentials in `.env`
- **Update application.yml:** Also add Spotify credentials in `application.yml` (lines 57-58)
- **Restart containers:** `docker-compose restart`
- **Invalid client:** Verify your Spotify Client ID and Secret are correct

### Container keeps restarting
- **Check logs:** `docker-compose logs -f`
- **Verify tokens:** Ensure your `.env` file has valid Discord token
- **Port conflicts:** Make sure ports 2333 isn't already in use
- **Memory issues:** Ensure your system has at least 512MB RAM available

### yt-dlp errors
- **Cookies file not found:** Check that `YTDLP_COOKIES_PATH` points to valid file
- **Cookies expired:** Re-export cookies from your browser
- **Disable if not needed:** Set `YTDLP_ENABLED=false` in `.env`

### High memory usage
- **Restart bot:** `docker-compose restart bot`
- **Check queue size:** Large queues consume more memory
- **Lavalink memory:** Adjust Lavalink memory in `docker-compose.yml` if needed

## License

MIT License
