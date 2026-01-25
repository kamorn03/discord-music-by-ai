# Discord Music Bot - Deployment Handbook

A complete guide to deploying your Discord Music Bot with Lavalink.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Prerequisites](#prerequisites)
3. [Deployment Options](#deployment-options)
4. [Option A: Docker Deployment (Recommended)](#option-a-docker-deployment-recommended)
5. [Option B: Manual Deployment](#option-b-manual-deployment)
6. [Option C: Cloud Deployment (Railway/VPS)](#option-c-cloud-deployment-railwayvps)
7. [Configuration Reference](#configuration-reference)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Comparison with PrimeMusic-Lavalink](#comparison-with-primemusic-lavalink)
10. [Maintenance & Updates](#maintenance--updates)

---

## Architecture Overview

```
                    ┌─────────────────────────────────────┐
                    │           Discord Server            │
                    │  (Users join voice, send commands)  │
                    └──────────────┬──────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                         Discord Bot                               │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │   bot.py       │  │  config.py   │  │    database.py       │  │
│  │ (Main Logic)   │  │  (Settings)  │  │  (SQLite Storage)    │  │
│  └────────┬───────┘  └──────────────┘  └──────────────────────┘  │
│           │                                                       │
│           │  wavelink library                                     │
│           ▼                                                       │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              Lavalink Client Connection                    │  │
│  │              (WebSocket to Lavalink:2333)                  │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Lavalink Server (Java)                       │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  Plugins:                                                  │  │
│  │  • youtube-plugin 1.16.0 (YouTube with OAuth)              │  │
│  │  • lavasrc-plugin 4.2.0 (Spotify, SoundCloud, etc.)        │  │
│  │  • lavasearch-plugin 1.0.0 (Enhanced search)               │  │
│  └────────────────────────────────────────────────────────────┘  │
│  Port: 2333 | Memory: 512MB+                                     │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
              ┌─────────┐   ┌──────────┐   ┌────────────┐
              │ YouTube │   │ Spotify  │   │ SoundCloud │
              └─────────┘   └──────────┘   └────────────┘
```

**Key Components:**

| Component | Technology | Purpose |
|-----------|------------|---------|
| Bot | Python 3.11 + discord.py | Command handling, user interaction |
| Wavelink | Python library | Connects bot to Lavalink |
| Lavalink | Java application | Audio processing & streaming |
| Database | SQLite (aiosqlite) | Stores playlists, settings |

---

## Prerequisites

### Required
- [x] **Discord Bot Token** - From Discord Developer Portal
- [x] **Discord Application ID** - Same portal
- [x] **Docker & Docker Compose** - For containerized deployment
- [x] **512MB+ RAM** - Minimum for Lavalink
- [x] **1GB+ Storage** - For logs and plugins

### Optional (Recommended)
- [ ] **Spotify Credentials** - For Spotify track support
- [ ] **YouTube OAuth Token** - For better YouTube reliability
- [ ] **YouTube Cookies** - For age-restricted videos

---

## Deployment Options

| Method | Difficulty | Best For | Pros | Cons |
|--------|------------|----------|------|------|
| **Docker** | Easy | Most users | One command, isolated, reproducible | Requires Docker |
| **Manual** | Medium | Developers | Full control, easier debugging | More setup steps |
| **Railway** | Easy | Cloud hosting | Free tier, auto-deploy | Limited resources |
| **VPS** | Medium | Production | Full control, scalable | Requires server |

---

## Option A: Docker Deployment (Recommended)

### Step 1: Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click **"New Application"** → Name it → Create
3. Copy the **Application ID** (you'll need this)
4. Go to **"Bot"** tab → Click **"Reset Token"** → Copy **Bot Token**
5. Enable **Privileged Gateway Intents**:
   - [x] MESSAGE CONTENT INTENT
   - [x] SERVER MEMBERS INTENT (optional)
6. Go to **"OAuth2"** → **"URL Generator"**:
   - Scopes: `bot`, `applications.commands`
   - Permissions: Send Messages, Embed Links, Connect, Speak
7. Copy the generated URL and invite bot to your server

### Step 2: Configure Environment

```bash
# Clone or navigate to project directory
cd discord-music-bot

# Create .env file from template
cp .env.example .env
```

Edit `.env` with your values:

```env
# REQUIRED - Discord Configuration
DISCORD_TOKEN=MTIzNDU2Nzg5MDEyMzQ1Njc4OQ.XXXXXX.XXXXXXXXXXXXXXXX
DISCORD_APP_ID=123456789012345678

# REQUIRED - Lavalink Configuration
LAVALINK_URI=http://localhost:2333
LAVALINK_PASSWORD=youshallnotpass

# OPTIONAL - Spotify Support
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret

# OPTIONAL - YouTube OAuth (improves reliability)
YOUTUBE_REFRESH_TOKEN=

# OPTIONAL - yt-dlp for age-restricted videos
YTDLP_ENABLED=false
YTDLP_COOKIES_PATH=./cookies/cookies.txt
```

### Step 3: Configure Spotify (Optional)

If using Spotify, edit `application.yml`:

```yaml
# Lines 59-62
spotify:
  clientId: "YOUR_ACTUAL_SPOTIFY_CLIENT_ID"
  clientSecret: "YOUR_ACTUAL_SPOTIFY_CLIENT_SECRET"
  countryCode: "US"
```

### Step 4: Deploy

```bash
# Build and start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs (both services)
docker-compose logs -f

# View only bot logs
docker-compose logs -f bot

# View only Lavalink logs
docker-compose logs -f lavalink
```

### Step 5: Verify Deployment

1. Check bot is online in Discord
2. Run `/help` or `!help` command
3. Join a voice channel and try `/play never gonna give you up`
4. Expected log output:
   ```
   bot       | INFO - Logged in as YourBot#1234
   bot       | INFO - Wavelink node 'MAIN' is ready!
   lavalink  | INFO - Lavalink is ready to accept connections
   ```

### Docker Commands Reference

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# Rebuild after code changes
docker-compose up -d --build

# View real-time logs
docker-compose logs -f

# Check container health
docker-compose ps

# Remove containers and networks
docker-compose down -v
```

---

## Option B: Manual Deployment

### Step 1: Install Lavalink

**Option 1: Download JAR**
```bash
# Create directory
mkdir lavalink && cd lavalink

# Download Lavalink 4
curl -L -o Lavalink.jar https://github.com/lavalink-devs/Lavalink/releases/download/4.0.8/Lavalink.jar

# Copy application.yml
cp ../application.yml .

# Run (requires Java 17+)
java -Xmx512M -jar Lavalink.jar
```

**Option 2: Docker for Lavalink only**
```bash
docker run -d \
  --name lavalink \
  -p 2333:2333 \
  -v $(pwd)/application.yml:/opt/Lavalink/application.yml \
  -e _JAVA_OPTIONS="-Xmx512M" \
  ghcr.io/lavalink-devs/lavalink:4
```

### Step 2: Install Python Dependencies

```bash
# Python 3.10+ required
python --version

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configure and Run Bot

```bash
# Create .env file
cp .env.example .env

# Edit .env with your values
# IMPORTANT: Set LAVALINK_URI=http://localhost:2333

# Run the bot
python bot.py
```

---

## Option C: Cloud Deployment (Railway/VPS)

### Railway Deployment

1. **Fork or push** your project to GitHub
2. Go to [Railway](https://railway.app) and create new project
3. Deploy from GitHub repo
4. Add environment variables in Railway dashboard:
   ```
   DISCORD_TOKEN=your_token
   DISCORD_APP_ID=your_app_id
   LAVALINK_URI=http://lavalink.internal:2333
   ```
5. Add Lavalink as separate service using Docker image

### VPS Deployment (Ubuntu/Debian)

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose -y

# Clone project
git clone https://github.com/your-repo/discord-music-bot.git
cd discord-music-bot

# Configure and deploy
cp .env.example .env
nano .env  # Edit with your values

# Start with Docker Compose
docker-compose up -d

# Enable auto-restart on boot
sudo systemctl enable docker
```

---

## Configuration Reference

### Environment Variables (.env)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DISCORD_TOKEN` | Yes | - | Bot token from Discord Developer Portal |
| `DISCORD_APP_ID` | Yes | - | Application ID from Discord Developer Portal |
| `BOT_PREFIX` | No | `!` | Text command prefix |
| `LAVALINK_URI` | No | `http://localhost:2333` | Lavalink server URL |
| `LAVALINK_PASSWORD` | No | `youshallnotpass` | Lavalink authentication |
| `SPOTIFY_CLIENT_ID` | No | - | Spotify API client ID |
| `SPOTIFY_CLIENT_SECRET` | No | - | Spotify API client secret |
| `YOUTUBE_REFRESH_TOKEN` | No | - | YouTube OAuth token |
| `YTDLP_ENABLED` | No | `false` | Enable yt-dlp extraction |
| `YTDLP_COOKIES_PATH` | No | `./cookies/cookies.txt` | Path to cookies file |
| `YTDLP_CACHE_TTL` | No | `1800` | Cache duration (seconds) |

### Lavalink Configuration (application.yml)

Key sections:

```yaml
server:
  port: 2333              # Lavalink API port
  address: 0.0.0.0        # Listen on all interfaces

lavalink:
  server:
    password: "youshallnotpass"  # Must match LAVALINK_PASSWORD

plugins:
  youtube:
    oauth:
      enabled: true       # Enable YouTube OAuth
      refreshToken: ${YOUTUBE_REFRESH_TOKEN:-}

  lavasrc:
    spotify:
      clientId: "YOUR_ID"        # Update these!
      clientSecret: "YOUR_SECRET"
```

### Docker Compose Configuration

```yaml
services:
  bot:
    network_mode: host    # Share network with Lavalink
    restart: unless-stopped
    depends_on:
      - lavalink

  lavalink:
    image: ghcr.io/lavalink-devs/lavalink:4
    environment:
      - _JAVA_OPTIONS=-Xmx512M  # Memory limit
```

---

## Troubleshooting Guide

### Bot Issues

| Problem | Solution |
|---------|----------|
| Bot doesn't start | Check `DISCORD_TOKEN` is valid |
| Commands not working | Enable MESSAGE CONTENT INTENT in Discord Portal |
| Slash commands missing | Wait 1 hour for Discord to sync, or kick/reinvite bot |
| Bot disconnects frequently | Check internet stability, increase timeout |

### Lavalink Issues

| Problem | Solution |
|---------|----------|
| Node not connecting | Verify Lavalink is running: `docker logs lavalink` |
| Connection refused | Check `LAVALINK_URI` matches actual Lavalink address |
| Out of memory | Increase `-Xmx` value in docker-compose.yml |
| Plugins not loading | Check `./plugins` directory exists |

### Audio Issues

| Problem | Solution |
|---------|----------|
| No audio | Bot needs "Connect" and "Speak" permissions |
| YouTube 403 errors | Add `YOUTUBE_REFRESH_TOKEN` or enable yt-dlp |
| Age-restricted fails | Enable yt-dlp with valid cookies |
| Spotify not working | Update credentials in both `.env` AND `application.yml` |

### Network Issues

| Problem | Solution |
|---------|----------|
| DNS resolution fails | Try `LAVALINK_URI=http://127.0.0.1:2333` |
| Port 2333 in use | Change port in `application.yml` and `LAVALINK_URI` |
| Firewall blocking | Open port 2333 for internal traffic |

### Diagnostic Commands

```bash
# Check if Lavalink is accessible
curl http://localhost:2333/version

# Check container status
docker-compose ps

# View last 100 log lines
docker-compose logs --tail=100

# Enter bot container for debugging
docker exec -it discord-music-bot /bin/bash

# Check port usage
netstat -tlnp | grep 2333

# Test DNS resolution
nslookup lavalink
```

---

## Comparison with PrimeMusic-Lavalink

| Feature | This Bot | PrimeMusic-Lavalink |
|---------|----------|---------------------|
| **Language** | Python | JavaScript (Node.js) |
| **Structure** | Single file | Modular (commands/, events/) |
| **Database** | SQLite | MongoDB |
| **Music Card UI** | Basic embeds | Custom canvas cards |
| **Audio Filters** | Not implemented | Bassboost, nightcore, etc. |
| **Multi-language** | No | 11+ languages |
| **24/7 Mode** | No | Yes |
| **Setup Complexity** | Simpler | More configuration |
| **Memory Usage** | ~200MB | ~300MB (optimized) |

### What This Bot Does Better
- Simpler setup and configuration
- Self-contained Lavalink (local deployment)
- Python-based (easier for some developers)
- SQLite (no external database needed)

### What PrimeMusic Does Better
- More features (filters, 24/7, lyrics)
- Better UI (custom music cards)
- Multi-language support
- Modular architecture

---

## Maintenance & Updates

### Updating the Bot

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose up -d --build
```

### Updating Lavalink

```bash
# Edit docker-compose.yml to use new version
# Change: ghcr.io/lavalink-devs/lavalink:4
# To:     ghcr.io/lavalink-devs/lavalink:4.0.8

# Restart
docker-compose pull lavalink
docker-compose up -d lavalink
```

### Backup & Restore

```bash
# Backup
cp .env .env.backup
cp application.yml application.yml.backup
cp music_bot.db music_bot.db.backup

# Restore
cp .env.backup .env
docker-compose up -d --build
```

### Logs Management

```bash
# View logs
docker-compose logs -f

# Lavalink logs are in ./logs/ directory
ls -la logs/

# Clear old logs
rm -rf logs/*.log.gz
```

---

## Quick Start Checklist

- [ ] 1. Create Discord bot at Developer Portal
- [ ] 2. Copy **Bot Token** and **Application ID**
- [ ] 3. Enable **MESSAGE CONTENT INTENT**
- [ ] 4. Create invite URL and add bot to server
- [ ] 5. Copy `.env.example` to `.env`
- [ ] 6. Edit `.env` with your credentials
- [ ] 7. (Optional) Add Spotify credentials to `application.yml`
- [ ] 8. Run `docker-compose up -d`
- [ ] 9. Check logs: `docker-compose logs -f`
- [ ] 10. Test with `/play` command

---

## Support

- **Issues:** Check `docker-compose logs` first
- **GitHub:** Report issues at your repository
- **Lavalink Docs:** https://lavalink.dev/
- **Discord.py Docs:** https://discordpy.readthedocs.io/
- **Wavelink Docs:** https://wavelink.dev/

---

*Last Updated: January 2025*
