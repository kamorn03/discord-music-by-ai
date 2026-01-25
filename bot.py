"""
Discord Music Bot - Plays music from YouTube and Spotify
Uses discord.py and wavelink with Lavalink backend
Features: Audio filters, playlists, autoplay, 24/7 mode
"""

import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import asyncio
import re
import time
import os
import yt_dlp
from typing import Optional, Literal
import config
import logging
from database import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

YTDLP_CACHE = {}


async def yt_dlp_extract(query: str) -> str | None:
    if not config.YTDLP_ENABLED:
        return None
    cache_key = query.lower().strip()
    now = time.time()
    cached = YTDLP_CACHE.get(cache_key)
    if cached and cached[1] > now:
        return cached[0]

    if not os.path.exists(config.YTDLP_COOKIES_PATH):
        logger.warning("yt-dlp cookies file not found at %s", config.YTDLP_COOKIES_PATH)
        return None

    ytdlp_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "format": "bestaudio/best",
        "cookiefile": config.YTDLP_COOKIES_PATH,
    }

    def _extract():
        with yt_dlp.YoutubeDL(ytdlp_opts) as ytdlp:
            return ytdlp.extract_info(query, download=False)

    try:
        info = await asyncio.to_thread(_extract)
    except Exception as exc:
        logger.warning("yt-dlp extraction failed: %s", exc)
        return None

    if not info:
        return None

    if "entries" in info and info["entries"]:
        info = info["entries"][0]

    url = info.get("url")
    if not url:
        return None

    YTDLP_CACHE[cache_key] = (url, now + config.YTDLP_CACHE_TTL)
    return url


# Spotify URL pattern
SPOTIFY_REGEX = re.compile(
    r'https?://open\.spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)'
)


# Audio Filter Presets (similar to PrimeMusic)
# These are created as functions since wavelink 3.x uses .set() method
def create_filter_bassboost() -> wavelink.Filters:
    filters = wavelink.Filters()
    filters.equalizer.set(bands=[
        {"band": 0, "gain": 0.6},
        {"band": 1, "gain": 0.7},
        {"band": 2, "gain": 0.8},
        {"band": 3, "gain": 0.55},
        {"band": 4, "gain": 0.25},
    ])
    return filters

def create_filter_nightcore() -> wavelink.Filters:
    filters = wavelink.Filters()
    filters.timescale.set(speed=1.3, pitch=1.3, rate=1.0)
    return filters

def create_filter_vaporwave() -> wavelink.Filters:
    filters = wavelink.Filters()
    filters.timescale.set(speed=0.85, pitch=0.9, rate=1.0)
    filters.equalizer.set(bands=[{"band": 0, "gain": 0.3}, {"band": 1, "gain": 0.3}])
    return filters

def create_filter_8d() -> wavelink.Filters:
    filters = wavelink.Filters()
    filters.rotation.set(rotation_hz=0.2)
    return filters

def create_filter_karaoke() -> wavelink.Filters:
    filters = wavelink.Filters()
    filters.karaoke.set(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)
    return filters

def create_filter_tremolo() -> wavelink.Filters:
    filters = wavelink.Filters()
    filters.tremolo.set(frequency=4.0, depth=0.75)
    return filters

def create_filter_vibrato() -> wavelink.Filters:
    filters = wavelink.Filters()
    filters.vibrato.set(frequency=4.0, depth=0.75)
    return filters

def create_filter_lowpass() -> wavelink.Filters:
    filters = wavelink.Filters()
    filters.low_pass.set(smoothing=20.0)
    return filters

def create_filter_soft() -> wavelink.Filters:
    filters = wavelink.Filters()
    filters.equalizer.set(bands=[
        {"band": 0, "gain": -0.25},
        {"band": 1, "gain": -0.25},
        {"band": 2, "gain": -0.125},
        {"band": 8, "gain": 0.25},
        {"band": 9, "gain": 0.25},
    ])
    return filters

def create_filter_loud() -> wavelink.Filters:
    filters = wavelink.Filters()
    filters.equalizer.set(bands=[
        {"band": 0, "gain": 0.5},
        {"band": 1, "gain": 0.4},
        {"band": 2, "gain": 0.3},
        {"band": 3, "gain": 0.2},
        {"band": 8, "gain": 0.35},
        {"band": 9, "gain": 0.4},
    ])
    return filters

FILTER_CREATORS = {
    "bassboost": create_filter_bassboost,
    "nightcore": create_filter_nightcore,
    "vaporwave": create_filter_vaporwave,
    "8d": create_filter_8d,
    "karaoke": create_filter_karaoke,
    "tremolo": create_filter_tremolo,
    "vibrato": create_filter_vibrato,
    "lowpass": create_filter_lowpass,
    "soft": create_filter_soft,
    "loud": create_filter_loud,
}


class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True

        super().__init__(
            command_prefix=config.PREFIX,
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        """Setup wavelink nodes and database when bot starts."""
        # Connect to database
        await db.connect()

        # Setup Lavalink
        node = wavelink.Node(
            uri=config.LAVALINK_URI,
            password=config.LAVALINK_PASSWORD
        )
        await wavelink.Pool.connect(nodes=[node], client=self, cache_capacity=100)

        # Sync slash commands
        await self.tree.sync()
        print(f"Synced slash commands!")

    async def on_ready(self):
        print(f"Bot is ready! Logged in as {self.user}")
        print(f"Bot is in {len(self.guilds)} guilds")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=f"{config.PREFIX}help"
            )
        )

    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"Wavelink node '{payload.node.identifier}' is ready!")

    async def on_wavelink_node_disconnected(self, payload):
        """Handle node disconnection - wavelink 3.x handles reconnection automatically."""
        logger.warning(f"A Lavalink node disconnected. Wavelink will attempt to reconnect automatically.")

    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Auto-play next track in queue or use autoplay when current track ends."""
        player = payload.player

        if not player:
            return

        # Check if 24/7 mode and queue is empty - don't disconnect
        if hasattr(player, 'twentyfourseven') and player.twentyfourseven:
            if player.queue.is_empty and not hasattr(player, 'autoplay_enabled'):
                return  # Stay connected but don't play anything

        # Play next track from queue
        if not player.queue.is_empty:
            try:
                next_track = player.queue.get()
                await player.play(next_track)

                # Send now playing message
                if hasattr(player, 'text_channel') and player.text_channel:
                    embed = discord.Embed(
                        title="Now Playing",
                        description=f"[{next_track.title}]({next_track.uri})",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Duration", value=format_duration(next_track.length), inline=True)
                    if next_track.artwork:
                        embed.set_thumbnail(url=next_track.artwork)
                    await player.text_channel.send(embed=embed)

            except wavelink.LavalinkException as e:
                logger.error(f"Failed to play next track: {e}")
            except Exception as e:
                logger.error(f"Unexpected error in track end handler: {e}")
        # Autoplay: find related track if enabled
        elif hasattr(player, 'autoplay_enabled') and player.autoplay_enabled and payload.track:
            try:
                # Search for related tracks
                query = f"ytsearch:{payload.track.title} {payload.track.author}"
                tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTube)

                if tracks and len(tracks) > 1:
                    # Play second result (first is likely the same song)
                    await player.play(tracks[1])
                    if hasattr(player, 'text_channel') and player.text_channel:
                        embed = discord.Embed(
                            title="Autoplay",
                            description=f"[{tracks[1].title}]({tracks[1].uri})",
                            color=discord.Color.purple()
                        )
                        if tracks[1].artwork:
                            embed.set_thumbnail(url=tracks[1].artwork)
                        await player.text_channel.send(embed=embed)
            except Exception as e:
                logger.error(f"Autoplay failed: {e}")

    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice state updates for 24/7 mode and auto-disconnect."""
        if member.bot:
            return

        # Check if bot is in the voice channel
        if before.channel and before.channel.guild.voice_client:
            voice_client = before.channel.guild.voice_client

            # Count non-bot members in the channel
            non_bot_members = [m for m in before.channel.members if not m.bot]

            # If channel is empty (only bot) and not in 24/7 mode, start disconnect timer
            if len(non_bot_members) == 0:
                if hasattr(voice_client, 'twentyfourseven') and voice_client.twentyfourseven:
                    return  # Don't disconnect in 24/7 mode

                # Wait 2 minutes before disconnecting
                await asyncio.sleep(120)

                # Check again if still empty
                if voice_client.channel:
                    non_bot_members = [m for m in voice_client.channel.members if not m.bot]
                    if len(non_bot_members) == 0 and not (hasattr(voice_client, 'twentyfourseven') and voice_client.twentyfourseven):
                        await voice_client.disconnect()


def format_duration(milliseconds: int) -> str:
    """Format milliseconds to MM:SS or HH:MM:SS."""
    seconds = milliseconds // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


bot = MusicBot()


# ============== Music Commands ==============

@bot.hybrid_command(name="join", description="Join your voice channel")
async def join(ctx: commands.Context):
    """Join the user's voice channel."""
    if not ctx.author.voice:
        return await ctx.send("You need to be in a voice channel!")

    channel = ctx.author.voice.channel

    if ctx.voice_client:
        if ctx.voice_client.channel == channel:
            return await ctx.send("I'm already in your channel!")
        await ctx.voice_client.move_to(channel)
    else:
        player = await channel.connect(cls=wavelink.Player)
        # Set default volume from database
        default_vol = await db.get_default_volume(str(ctx.guild.id))
        await player.set_volume(default_vol)

    await ctx.send(f"Joined **{channel.name}**!")


@bot.hybrid_command(name="leave", aliases=["disconnect", "dc"], description="Leave the voice channel")
async def leave(ctx: commands.Context):
    """Leave the voice channel."""
    if not ctx.voice_client:
        return await ctx.send("I'm not in a voice channel!")

    await ctx.voice_client.disconnect()
    await ctx.send("Disconnected!")


@bot.hybrid_command(name="play", aliases=["p"], description="Play a song from YouTube or Spotify")
@app_commands.describe(query="Song name, YouTube URL, or Spotify URL")
async def play(ctx: commands.Context, *, query: str):
    """Play a song from YouTube or Spotify."""
    if not ctx.author.voice:
        return await ctx.send("You need to be in a voice channel!")

    # Connect to voice channel if not connected
    if not ctx.voice_client:
        player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        # Set default volume from database
        default_vol = await db.get_default_volume(str(ctx.guild.id))
        await player.set_volume(default_vol)
        # Load autoplay setting
        autoplay = await db.get_autoplay(str(ctx.guild.id))
        player.autoplay_enabled = autoplay
    else:
        player = ctx.voice_client

    # Store the text channel for now playing messages
    player.text_channel = ctx.channel

    await ctx.defer()

    # Sanitize query to avoid invalid URLs (strip newlines/extra text)
    query = query.strip()
    url_match = re.search(r"https?://\S+", query)
    if url_match:
        query = url_match.group(0)

    # Check if it's a Spotify URL
    spotify_match = SPOTIFY_REGEX.match(query)

    try:
        if spotify_match:
            # Handle Spotify URLs
            tracks = await wavelink.Playable.search(query)
        elif query.startswith("scsearch:"):
            # Handle SoundCloud searches explicitly
            sc_query = query[len("scsearch:"):].strip()
            tracks = await wavelink.Playable.search(sc_query, source=wavelink.TrackSource.SoundCloud)
        elif query.startswith(("http://", "https://")):
            # Handle direct URLs (YouTube, etc.)
            if "youtube.com" in query or "youtu.be" in query:
                direct_url = await yt_dlp_extract(query)
                if direct_url:
                    tracks = await wavelink.Playable.search(direct_url)
                else:
                    tracks = await wavelink.Playable.search(query)
            else:
                tracks = await wavelink.Playable.search(query)
        else:
            # Search YouTube via yt-dlp first, fallback to ytsearch then scsearch
            direct_url = await yt_dlp_extract(f"ytsearch1:{query}")
            if direct_url:
                tracks = await wavelink.Playable.search(direct_url)
            else:
                # Try YouTube first
                try:
                    tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTube)
                except wavelink.LavalinkException as e:
                    logger.warning(f"YouTube search failed: {e}")
                    tracks = None

                # Fallback to SoundCloud if no tracks or error
                if not tracks:
                    logger.info("Falling back to SoundCloud search...")
                    tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.SoundCloud)

        if not tracks:
            return await ctx.send("No tracks found! Try a different search term.")

        # Handle playlists
        if isinstance(tracks, wavelink.Playlist):
            added = 0
            for track in tracks.tracks:
                await player.queue.put_wait(track)
                added += 1

            embed = discord.Embed(
                title="Playlist Added",
                description=f"Added **{added}** tracks from **{tracks.name}**",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            track = tracks[0]
            await player.queue.put_wait(track)

            if player.playing:
                embed = discord.Embed(
                    title="Added to Queue",
                    description=f"[{track.title}]({track.uri})",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Duration", value=format_duration(track.length), inline=True)
                embed.add_field(name="Position", value=str(player.queue.count), inline=True)

                if track.artwork:
                    embed.set_thumbnail(url=track.artwork)

                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="Now Playing",
                    description=f"[{track.title}]({track.uri})",
                    color=discord.Color.green()
                )
                embed.add_field(name="Duration", value=format_duration(track.length), inline=True)

                if track.artwork:
                    embed.set_thumbnail(url=track.artwork)

                await ctx.send(embed=embed)

        # Start playing if not already
        if not player.playing:
            await player.play(player.queue.get())

    except wavelink.LavalinkLoadException:
        await ctx.send("Failed to load track. The source may be unavailable or restricted.")
    except wavelink.LavalinkException as e:
        logger.error(f"Lavalink error: {e}")
        await ctx.send("Playback error occurred. Please try again.")
    except Exception as e:
        logger.error(f"Unexpected error in play command: {e}")
        await ctx.send("An unexpected error occurred. Please try again.")


@bot.hybrid_command(name="pause", description="Pause the current song")
async def pause(ctx: commands.Context):
    """Pause the current song."""
    if not ctx.voice_client or not ctx.voice_client.playing:
        return await ctx.send("Nothing is playing!")

    await ctx.voice_client.pause(True)
    await ctx.send("Paused!")


@bot.hybrid_command(name="resume", description="Resume the paused song")
async def resume(ctx: commands.Context):
    """Resume the paused song."""
    if not ctx.voice_client:
        return await ctx.send("I'm not in a voice channel!")

    if not ctx.voice_client.paused:
        return await ctx.send("The music is not paused!")

    await ctx.voice_client.pause(False)
    await ctx.send("Resumed!")


@bot.hybrid_command(name="skip", aliases=["s"], description="Skip the current song")
async def skip(ctx: commands.Context):
    """Skip the current song."""
    if not ctx.voice_client or not ctx.voice_client.playing:
        return await ctx.send("Nothing is playing!")

    await ctx.voice_client.skip()
    await ctx.send("Skipped!")


@bot.hybrid_command(name="stop", description="Stop playing and clear the queue")
async def stop(ctx: commands.Context):
    """Stop playing and clear the queue."""
    if not ctx.voice_client:
        return await ctx.send("I'm not in a voice channel!")

    ctx.voice_client.queue.clear()
    await ctx.voice_client.stop()
    await ctx.send("Stopped and cleared the queue!")


@bot.hybrid_command(name="queue", aliases=["q"], description="Show the current queue")
async def queue(ctx: commands.Context):
    """Show the current queue."""
    if not ctx.voice_client:
        return await ctx.send("I'm not in a voice channel!")

    player = ctx.voice_client

    if not player.current and player.queue.is_empty:
        return await ctx.send("The queue is empty!")

    embed = discord.Embed(title="Music Queue", color=discord.Color.purple())

    # Current track
    if player.current:
        embed.add_field(
            name="Now Playing",
            value=f"[{player.current.title}]({player.current.uri}) - {format_duration(player.current.length)}",
            inline=False
        )

    # Queue
    if not player.queue.is_empty:
        queue_list = []
        for i, track in enumerate(player.queue[:10], 1):
            queue_list.append(f"`{i}.` [{track.title}]({track.uri}) - {format_duration(track.length)}")

        if player.queue.count > 10:
            queue_list.append(f"\n*...and {player.queue.count - 10} more tracks*")

        embed.add_field(
            name=f"Up Next ({player.queue.count} tracks)",
            value="\n".join(queue_list),
            inline=False
        )

    # Show current settings
    settings = []
    if hasattr(player, 'autoplay_enabled') and player.autoplay_enabled:
        settings.append("Autoplay: ON")
    if hasattr(player, 'twentyfourseven') and player.twentyfourseven:
        settings.append("24/7: ON")
    if player.queue.mode != wavelink.QueueMode.normal:
        mode = "Track" if player.queue.mode == wavelink.QueueMode.loop else "Queue"
        settings.append(f"Loop: {mode}")

    if settings:
        embed.set_footer(text=" | ".join(settings))

    await ctx.send(embed=embed)


@bot.hybrid_command(name="nowplaying", aliases=["np"], description="Show the current song")
async def nowplaying(ctx: commands.Context):
    """Show the currently playing song."""
    if not ctx.voice_client or not ctx.voice_client.current:
        return await ctx.send("Nothing is playing!")

    player = ctx.voice_client
    track = player.current

    # Calculate progress
    position = player.position
    duration = track.length
    progress = int((position / duration) * 20) if duration > 0 else 0
    progress_bar = "▓" * progress + "░" * (20 - progress)

    embed = discord.Embed(
        title="Now Playing",
        description=f"[{track.title}]({track.uri})",
        color=discord.Color.green()
    )
    embed.add_field(name="Author", value=track.author, inline=True)
    embed.add_field(name="Duration", value=f"{format_duration(position)}/{format_duration(duration)}", inline=True)
    embed.add_field(name="Volume", value=f"{player.volume}%", inline=True)
    embed.add_field(name="Progress", value=f"`{progress_bar}`", inline=False)

    if track.artwork:
        embed.set_thumbnail(url=track.artwork)

    await ctx.send(embed=embed)


@bot.hybrid_command(name="volume", aliases=["vol"], description="Set the volume (0-100)")
@app_commands.describe(volume="Volume level (0-100)")
async def volume(ctx: commands.Context, volume: int):
    """Set the volume."""
    if not ctx.voice_client:
        return await ctx.send("I'm not in a voice channel!")

    if volume < 0 or volume > 100:
        return await ctx.send("Volume must be between 0 and 100!")

    await ctx.voice_client.set_volume(volume)
    await ctx.send(f"Volume set to **{volume}%**")


@bot.hybrid_command(name="shuffle", description="Shuffle the queue")
async def shuffle(ctx: commands.Context):
    """Shuffle the queue."""
    if not ctx.voice_client:
        return await ctx.send("I'm not in a voice channel!")

    if ctx.voice_client.queue.is_empty:
        return await ctx.send("The queue is empty!")

    ctx.voice_client.queue.shuffle()
    await ctx.send("Queue shuffled!")


@bot.hybrid_command(name="loop", description="Toggle loop mode")
@app_commands.describe(mode="Loop mode: off, track, or queue")
async def loop(ctx: commands.Context, mode: Optional[str] = None):
    """Toggle loop mode."""
    if not ctx.voice_client:
        return await ctx.send("I'm not in a voice channel!")

    player = ctx.voice_client

    if mode is None:
        # Cycle through modes
        if player.queue.mode == wavelink.QueueMode.normal:
            player.queue.mode = wavelink.QueueMode.loop
            await ctx.send("Looping: **Current Track**")
        elif player.queue.mode == wavelink.QueueMode.loop:
            player.queue.mode = wavelink.QueueMode.loop_all
            await ctx.send("Looping: **Queue**")
        else:
            player.queue.mode = wavelink.QueueMode.normal
            await ctx.send("Looping: **Off**")
    else:
        mode = mode.lower()
        if mode in ["off", "none", "disable"]:
            player.queue.mode = wavelink.QueueMode.normal
            await ctx.send("Looping: **Off**")
        elif mode in ["track", "song", "one"]:
            player.queue.mode = wavelink.QueueMode.loop
            await ctx.send("Looping: **Current Track**")
        elif mode in ["queue", "all"]:
            player.queue.mode = wavelink.QueueMode.loop_all
            await ctx.send("Looping: **Queue**")
        else:
            await ctx.send("Invalid mode! Use: `off`, `track`, or `queue`")


@bot.hybrid_command(name="seek", description="Seek to a position in the song")
@app_commands.describe(position="Position in seconds")
async def seek(ctx: commands.Context, position: int):
    """Seek to a position in the current song."""
    if not ctx.voice_client or not ctx.voice_client.current:
        return await ctx.send("Nothing is playing!")

    duration = ctx.voice_client.current.length // 1000

    if position < 0 or position > duration:
        return await ctx.send(f"Position must be between 0 and {duration} seconds!")

    await ctx.voice_client.seek(position * 1000)
    await ctx.send(f"Seeked to **{format_duration(position * 1000)}**")


@bot.hybrid_command(name="remove", description="Remove a track from the queue")
@app_commands.describe(position="Position in queue (1-based)")
async def remove(ctx: commands.Context, position: int):
    """Remove a track from the queue."""
    if not ctx.voice_client:
        return await ctx.send("I'm not in a voice channel!")

    if ctx.voice_client.queue.is_empty:
        return await ctx.send("The queue is empty!")

    if position < 1 or position > ctx.voice_client.queue.count:
        return await ctx.send(f"Position must be between 1 and {ctx.voice_client.queue.count}!")

    removed = ctx.voice_client.queue.delete(position - 1)
    await ctx.send(f"Removed **{removed.title}** from the queue!")


@bot.hybrid_command(name="clear", description="Clear the queue")
async def clear(ctx: commands.Context):
    """Clear the queue."""
    if not ctx.voice_client:
        return await ctx.send("I'm not in a voice channel!")

    ctx.voice_client.queue.clear()
    await ctx.send("Queue cleared!")


# ============== Audio Filters (Like PrimeMusic) ==============

@bot.hybrid_command(name="filter", aliases=["filters", "f"], description="Apply an audio filter")
@app_commands.describe(preset="Filter preset to apply")
async def filter_cmd(ctx: commands.Context, preset: Optional[str] = None):
    """Apply an audio filter preset."""
    if not ctx.voice_client:
        return await ctx.send("I'm not in a voice channel!")

    if not ctx.voice_client.playing:
        return await ctx.send("Nothing is playing!")

    player = ctx.voice_client

    if preset is None:
        # Show available filters
        embed = discord.Embed(
            title="Audio Filters",
            description="Use `/filter <name>` to apply a filter",
            color=discord.Color.blue()
        )

        filter_list = [
            ("bassboost", "Boosts bass frequencies"),
            ("nightcore", "Speeds up and raises pitch"),
            ("vaporwave", "Slows down and lowers pitch"),
            ("8d", "Rotating audio effect"),
            ("karaoke", "Reduces vocals"),
            ("tremolo", "Wavering volume effect"),
            ("vibrato", "Wavering pitch effect"),
            ("lowpass", "Muffles high frequencies"),
            ("soft", "Softer, calmer sound"),
            ("loud", "Louder, more intense sound"),
            ("off", "Remove all filters"),
        ]

        value = "\n".join([f"`{name}` - {desc}" for name, desc in filter_list])
        embed.add_field(name="Available Filters", value=value, inline=False)

        return await ctx.send(embed=embed)

    preset = preset.lower()

    if preset in ["off", "none", "reset", "clear"]:
        await player.set_filters(None)
        return await ctx.send("Filters cleared!")

    if preset not in FILTER_CREATORS:
        return await ctx.send(f"Unknown filter! Use `/filter` to see available filters.")

    await player.set_filters(FILTER_CREATORS[preset]())
    await ctx.send(f"Applied **{preset}** filter!")


@bot.hybrid_command(name="bassboost", aliases=["bass", "bb"], description="Apply bassboost filter")
async def bassboost(ctx: commands.Context):
    """Quick command to apply bassboost."""
    if not ctx.voice_client or not ctx.voice_client.playing:
        return await ctx.send("Nothing is playing!")

    await ctx.voice_client.set_filters(FILTER_CREATORS["bassboost"]())
    await ctx.send("Applied **bassboost** filter!")


@bot.hybrid_command(name="nightcore", aliases=["nc"], description="Apply nightcore filter")
async def nightcore(ctx: commands.Context):
    """Quick command to apply nightcore."""
    if not ctx.voice_client or not ctx.voice_client.playing:
        return await ctx.send("Nothing is playing!")

    await ctx.voice_client.set_filters(FILTER_CREATORS["nightcore"]())
    await ctx.send("Applied **nightcore** filter!")


@bot.hybrid_command(name="vaporwave", aliases=["vw"], description="Apply vaporwave filter")
async def vaporwave(ctx: commands.Context):
    """Quick command to apply vaporwave."""
    if not ctx.voice_client or not ctx.voice_client.playing:
        return await ctx.send("Nothing is playing!")

    await ctx.voice_client.set_filters(FILTER_CREATORS["vaporwave"]())
    await ctx.send("Applied **vaporwave** filter!")


@bot.hybrid_command(name="clearfilter", aliases=["cf", "nofilter"], description="Remove all audio filters")
async def clearfilter(ctx: commands.Context):
    """Remove all audio filters."""
    if not ctx.voice_client:
        return await ctx.send("I'm not in a voice channel!")

    await ctx.voice_client.set_filters(None)
    await ctx.send("Filters cleared!")


# ============== Autoplay & 24/7 Mode ==============

@bot.hybrid_command(name="autoplay", aliases=["ap"], description="Toggle autoplay mode")
async def autoplay(ctx: commands.Context):
    """Toggle autoplay mode - automatically plays similar songs when queue is empty."""
    if not ctx.voice_client:
        return await ctx.send("I'm not in a voice channel!")

    player = ctx.voice_client

    if not hasattr(player, 'autoplay_enabled'):
        player.autoplay_enabled = False

    player.autoplay_enabled = not player.autoplay_enabled

    # Save to database
    await db.set_autoplay(str(ctx.guild.id), player.autoplay_enabled)

    status = "enabled" if player.autoplay_enabled else "disabled"
    await ctx.send(f"Autoplay **{status}**!")


@bot.hybrid_command(name="247", aliases=["twentyfourseven", "stay"], description="Toggle 24/7 mode")
async def twentyfourseven(ctx: commands.Context):
    """Toggle 24/7 mode - bot stays in channel even when no one is listening."""
    if not ctx.voice_client:
        return await ctx.send("I'm not in a voice channel!")

    player = ctx.voice_client

    if not hasattr(player, 'twentyfourseven'):
        player.twentyfourseven = False

    player.twentyfourseven = not player.twentyfourseven

    status = "enabled" if player.twentyfourseven else "disabled"
    await ctx.send(f"24/7 mode **{status}**!")


# ============== Playlist Commands ==============

@bot.hybrid_group(name="playlist", aliases=["pl"], description="Manage playlists")
async def playlist(ctx: commands.Context):
    """Playlist management commands."""
    if ctx.invoked_subcommand is None:
        embed = discord.Embed(
            title="Playlist Commands",
            description="Manage your personal playlists",
            color=discord.Color.blue()
        )

        commands_list = [
            ("`/playlist create <name>`", "Create a new playlist"),
            ("`/playlist delete <name>`", "Delete a playlist"),
            ("`/playlist save <name>`", "Save current queue to playlist"),
            ("`/playlist load <name>`", "Load a playlist to queue"),
            ("`/playlist list`", "Show your playlists"),
            ("`/playlist show <name>`", "Show tracks in a playlist"),
        ]

        value = "\n".join([f"{cmd} - {desc}" for cmd, desc in commands_list])
        embed.add_field(name="Commands", value=value, inline=False)

        await ctx.send(embed=embed)


@playlist.command(name="create", description="Create a new playlist")
@app_commands.describe(name="Name for the playlist")
async def playlist_create(ctx: commands.Context, *, name: str):
    """Create a new playlist."""
    name = name.strip()[:50]  # Limit name length

    playlist_id = await db.create_playlist(str(ctx.guild.id), str(ctx.author.id), name)

    if playlist_id:
        await ctx.send(f"Created playlist **{name}**!")
    else:
        await ctx.send(f"A playlist with that name already exists!")


@playlist.command(name="delete", description="Delete a playlist")
@app_commands.describe(name="Name of the playlist to delete")
async def playlist_delete(ctx: commands.Context, *, name: str):
    """Delete a playlist."""
    deleted = await db.delete_playlist(str(ctx.guild.id), str(ctx.author.id), name.strip())

    if deleted:
        await ctx.send(f"Deleted playlist **{name}**!")
    else:
        await ctx.send(f"Playlist not found!")


@playlist.command(name="save", description="Save current queue to a playlist")
@app_commands.describe(name="Name for the playlist")
async def playlist_save(ctx: commands.Context, *, name: str):
    """Save the current queue to a playlist."""
    if not ctx.voice_client:
        return await ctx.send("I'm not in a voice channel!")

    player = ctx.voice_client

    if not player.current and player.queue.is_empty:
        return await ctx.send("The queue is empty!")

    name = name.strip()[:50]

    # Create or get playlist
    playlist_id = await db.get_playlist_id(str(ctx.guild.id), str(ctx.author.id), name)

    if not playlist_id:
        playlist_id = await db.create_playlist(str(ctx.guild.id), str(ctx.author.id), name)
        if not playlist_id:
            return await ctx.send("Failed to create playlist!")
    else:
        # Clear existing tracks
        await db.clear_playlist_tracks(playlist_id)

    # Add current track and queue
    position = 0

    if player.current:
        await db.add_track_to_playlist(
            playlist_id,
            player.current.uri,
            player.current.title,
            player.current.author,
            position
        )
        position += 1

    for track in player.queue:
        await db.add_track_to_playlist(
            playlist_id,
            track.uri,
            track.title,
            track.author,
            position
        )
        position += 1

    await ctx.send(f"Saved **{position}** tracks to playlist **{name}**!")


@playlist.command(name="load", description="Load a playlist to the queue")
@app_commands.describe(name="Name of the playlist to load")
async def playlist_load(ctx: commands.Context, *, name: str):
    """Load a playlist into the queue."""
    if not ctx.author.voice:
        return await ctx.send("You need to be in a voice channel!")

    playlist_id = await db.get_playlist_id(str(ctx.guild.id), str(ctx.author.id), name.strip())

    if not playlist_id:
        return await ctx.send("Playlist not found!")

    tracks_data = await db.get_playlist_tracks(playlist_id)

    if not tracks_data:
        return await ctx.send("Playlist is empty!")

    # Connect to voice if not connected
    if not ctx.voice_client:
        player = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        default_vol = await db.get_default_volume(str(ctx.guild.id))
        await player.set_volume(default_vol)
    else:
        player = ctx.voice_client

    player.text_channel = ctx.channel

    await ctx.defer()

    added = 0
    for track_data in tracks_data:
        try:
            tracks = await wavelink.Playable.search(track_data['uri'])
            if tracks:
                track = tracks[0] if not isinstance(tracks, wavelink.Playlist) else tracks.tracks[0]
                await player.queue.put_wait(track)
                added += 1
        except Exception as e:
            logger.warning(f"Failed to load track {track_data['title']}: {e}")

    embed = discord.Embed(
        title="Playlist Loaded",
        description=f"Added **{added}** tracks from **{name}**",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

    # Start playing if not already
    if not player.playing and not player.queue.is_empty:
        await player.play(player.queue.get())


@playlist.command(name="list", description="Show your playlists")
async def playlist_list(ctx: commands.Context):
    """List all your playlists."""
    playlists = await db.list_playlists(str(ctx.guild.id), str(ctx.author.id))

    if not playlists:
        return await ctx.send("You don't have any playlists!")

    embed = discord.Embed(
        title="Your Playlists",
        color=discord.Color.purple()
    )

    playlist_text = []
    for pl in playlists[:15]:  # Limit to 15
        playlist_text.append(f"**{pl['name']}** - {pl['track_count']} tracks")

    embed.description = "\n".join(playlist_text)

    if len(playlists) > 15:
        embed.set_footer(text=f"...and {len(playlists) - 15} more")

    await ctx.send(embed=embed)


@playlist.command(name="show", description="Show tracks in a playlist")
@app_commands.describe(name="Name of the playlist")
async def playlist_show(ctx: commands.Context, *, name: str):
    """Show tracks in a playlist."""
    playlist_id = await db.get_playlist_id(str(ctx.guild.id), str(ctx.author.id), name.strip())

    if not playlist_id:
        return await ctx.send("Playlist not found!")

    tracks = await db.get_playlist_tracks(playlist_id)

    if not tracks:
        return await ctx.send("Playlist is empty!")

    embed = discord.Embed(
        title=f"Playlist: {name}",
        color=discord.Color.purple()
    )

    track_list = []
    for i, track in enumerate(tracks[:15], 1):
        track_list.append(f"`{i}.` {track['title']}")

    embed.description = "\n".join(track_list)

    if len(tracks) > 15:
        embed.set_footer(text=f"...and {len(tracks) - 15} more tracks")
    else:
        embed.set_footer(text=f"{len(tracks)} tracks total")

    await ctx.send(embed=embed)


# ============== Settings Commands ==============

@bot.hybrid_command(name="setvolume", aliases=["defaultvolume", "setvol"], description="Set default volume for this server")
@app_commands.describe(volume="Default volume level (0-100)")
async def setvolume(ctx: commands.Context, volume: int):
    """Set the default volume for this server."""
    if not ctx.author.guild_permissions.manage_guild:
        return await ctx.send("You need **Manage Server** permission to change this!")

    if volume < 0 or volume > 100:
        return await ctx.send("Volume must be between 0 and 100!")

    await db.set_default_volume(str(ctx.guild.id), volume)
    await ctx.send(f"Default volume set to **{volume}%**")


# ============== Help Command ==============

@bot.hybrid_command(name="help", description="Show all commands")
async def help_command(ctx: commands.Context):
    """Show all available commands."""
    embed = discord.Embed(
        title="Music Bot Commands",
        description=f"Prefix: `{config.PREFIX}` | Also supports slash commands!",
        color=discord.Color.blue()
    )

    commands_list = {
        "Playing": [
            ("`play <query>`", "Play a song (YouTube/Spotify URL or search)"),
            ("`pause`", "Pause the current song"),
            ("`resume`", "Resume the paused song"),
            ("`skip`", "Skip the current song"),
            ("`stop`", "Stop playing and clear queue"),
            ("`seek <seconds>`", "Seek to a position"),
        ],
        "Queue": [
            ("`queue`", "Show the current queue"),
            ("`nowplaying`", "Show current song info"),
            ("`shuffle`", "Shuffle the queue"),
            ("`loop [mode]`", "Toggle loop (off/track/queue)"),
            ("`remove <pos>`", "Remove track from queue"),
            ("`clear`", "Clear the queue"),
        ],
        "Filters": [
            ("`filter [name]`", "Apply audio filter (bassboost, nightcore, etc.)"),
            ("`bassboost`", "Apply bassboost filter"),
            ("`nightcore`", "Apply nightcore filter"),
            ("`clearfilter`", "Remove all filters"),
        ],
        "Features": [
            ("`autoplay`", "Toggle autoplay mode"),
            ("`247`", "Toggle 24/7 mode"),
            ("`playlist`", "Manage playlists"),
        ],
        "General": [
            ("`join`", "Join your voice channel"),
            ("`leave`", "Leave the voice channel"),
            ("`volume <0-100>`", "Set the volume"),
            ("`setvolume <0-100>`", "Set default volume"),
            ("`help`", "Show this message"),
        ]
    }

    for category, cmds in commands_list.items():
        value = "\n".join([f"{cmd} - {desc}" for cmd, desc in cmds])
        embed.add_field(name=category, value=value, inline=False)

    embed.set_footer(text="Supports YouTube URLs, Spotify URLs (tracks/albums/playlists), and search queries!")

    await ctx.send(embed=embed)


# Run the bot
if __name__ == "__main__":
    bot.run(config.BOT_TOKEN)
