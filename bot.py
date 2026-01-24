"""
Discord Music Bot - Plays music from YouTube and Spotify
Uses discord.py and wavelink with Lavalink backend
"""

import discord
from discord.ext import commands
from discord import app_commands
import wavelink
import asyncio
import re
import time
import yt_dlp
from typing import Optional
import config
import socket
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

YTDLP_CACHE = {}


async def yt_dlp_extract(query: str) -> str | None:
    cache_key = query.lower().strip()
    now = time.time()
    cached = YTDLP_CACHE.get(cache_key)
    if cached and cached[1] > now:
        return cached[0]

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
        """Setup wavelink nodes when bot starts."""
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

    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Auto-play next track in queue when current track ends."""
        player = payload.player
        if player and not player.queue.is_empty:
            try:
                next_track = player.queue.get()
                await player.play(next_track)
            except Exception:
                pass


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
        await channel.connect(cls=wavelink.Player)

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
                tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.YouTube)
                if not tracks:
                    tracks = await wavelink.Playable.search(query, source=wavelink.TrackSource.SoundCloud)

        if not tracks:
            return await ctx.send("No tracks found!")

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

    except Exception as e:
        await ctx.send(f"Error: {str(e)}")


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
    progress = int((position / duration) * 20)
    progress_bar = "▓" * progress + "░" * (20 - progress)

    embed = discord.Embed(
        title="Now Playing",
        description=f"[{track.title}]({track.uri})",
        color=discord.Color.green()
    )
    embed.add_field(name="Author", value=track.author, inline=True)
    embed.add_field(name="Duration", value=f"{format_duration(position)}/{format_duration(duration)}", inline=True)
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
        "General": [
            ("`join`", "Join your voice channel"),
            ("`leave`", "Leave the voice channel"),
            ("`volume <0-100>`", "Set the volume"),
            ("`help`", "Show this message"),
        ]
    }

    for category, cmds in commands_list.items():
        value = "\n".join([f"{cmd} - {desc}" for cmd, desc in cmds])
        embed.add_field(name=category, value=value, inline=False)

    embed.set_footer(text="Supports YouTube URLs, Spotify URLs (tracks/albums/playlists), and search queries!")

    await ctx.send(embed=embed)


# Handle track end - auto play next
@bot.event
async def on_wavelink_track_end(payload: wavelink.TrackEndEventPayload):
    player = payload.player

    if player and not player.queue.is_empty:
        next_track = player.queue.get()
        await player.play(next_track)


# Run the bot
if __name__ == "__main__":
    bot.run(config.BOT_TOKEN)
