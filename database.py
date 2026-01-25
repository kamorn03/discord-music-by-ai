"""
Database module for Discord Music Bot
Handles SQLite database operations for playlists and user settings
"""

import aiosqlite
import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Use data directory if it exists (Docker), otherwise current directory
DATA_DIR = "./data" if os.path.exists("./data") else "."
DATABASE_PATH = os.path.join(DATA_DIR, "music_bot.db")


class Database:
    """Async SQLite database manager for music bot."""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        self.db = None
    
    async def connect(self):
        """Connect to the database and initialize schema."""
        self.db = await aiosqlite.connect(self.db_path)
        await self._initialize_schema()
        logger.info(f"Connected to database: {self.db_path}")
    
    async def close(self):
        """Close database connection."""
        if self.db:
            await self.db.close()
            logger.info("Database connection closed")
    
    async def _initialize_schema(self):
        """Create database tables if they don't exist."""
        async with self.db.cursor() as cursor:
            # User settings table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    guild_id TEXT PRIMARY KEY,
                    autoplay INTEGER DEFAULT 0,
                    default_volume INTEGER DEFAULT 50,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Playlists table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id TEXT NOT NULL,
                    owner_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(guild_id, owner_id, name)
                )
            """)
            
            # Playlist tracks table
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS playlist_tracks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    playlist_id INTEGER NOT NULL,
                    track_uri TEXT NOT NULL,
                    track_title TEXT NOT NULL,
                    track_author TEXT,
                    position INTEGER NOT NULL,
                    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
                )
            """)
            
            await self.db.commit()
            logger.info("Database schema initialized")
    
    # ============== User Settings ==============
    
    async def get_autoplay(self, guild_id: str) -> bool:
        """Get autoplay setting for a guild."""
        async with self.db.cursor() as cursor:
            await cursor.execute(
                "SELECT autoplay FROM user_settings WHERE guild_id = ?",
                (guild_id,)
            )
            result = await cursor.fetchone()
            return bool(result[0]) if result else False
    
    async def set_autoplay(self, guild_id: str, enabled: bool):
        """Set autoplay setting for a guild."""
        async with self.db.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO user_settings (guild_id, autoplay, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(guild_id) DO UPDATE SET
                    autoplay = excluded.autoplay,
                    updated_at = CURRENT_TIMESTAMP
            """, (guild_id, int(enabled)))
            await self.db.commit()
    
    async def get_default_volume(self, guild_id: str) -> int:
        """Get default volume for a guild."""
        async with self.db.cursor() as cursor:
            await cursor.execute(
                "SELECT default_volume FROM user_settings WHERE guild_id = ?",
                (guild_id,)
            )
            result = await cursor.fetchone()
            return result[0] if result else 50
    
    async def set_default_volume(self, guild_id: str, volume: int):
        """Set default volume for a guild."""
        async with self.db.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO user_settings (guild_id, default_volume, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(guild_id) DO UPDATE SET
                    default_volume = excluded.default_volume,
                    updated_at = CURRENT_TIMESTAMP
            """, (guild_id, volume))
            await self.db.commit()
    
    # ============== Playlists ==============
    
    async def create_playlist(self, guild_id: str, owner_id: str, name: str) -> Optional[int]:
        """Create a new playlist. Returns playlist ID or None if name exists."""
        try:
            async with self.db.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO playlists (guild_id, owner_id, name)
                    VALUES (?, ?, ?)
                """, (guild_id, owner_id, name))
                await self.db.commit()
                return cursor.lastrowid
        except aiosqlite.IntegrityError:
            logger.warning(f"Playlist '{name}' already exists for user {owner_id} in guild {guild_id}")
            return None
    
    async def delete_playlist(self, guild_id: str, owner_id: str, name: str) -> bool:
        """Delete a playlist. Returns True if deleted, False if not found."""
        async with self.db.cursor() as cursor:
            await cursor.execute("""
                DELETE FROM playlists
                WHERE guild_id = ? AND owner_id = ? AND name = ?
            """, (guild_id, owner_id, name))
            await self.db.commit()
            return cursor.rowcount > 0
    
    async def get_playlist_id(self, guild_id: str, owner_id: str, name: str) -> Optional[int]:
        """Get playlist ID by name."""
        async with self.db.cursor() as cursor:
            await cursor.execute("""
                SELECT id FROM playlists
                WHERE guild_id = ? AND owner_id = ? AND name = ?
            """, (guild_id, owner_id, name))
            result = await cursor.fetchone()
            return result[0] if result else None
    
    async def list_playlists(self, guild_id: str, owner_id: str) -> List[Dict[str, Any]]:
        """List all playlists for a user in a guild."""
        async with self.db.cursor() as cursor:
            await cursor.execute("""
                SELECT p.name, COUNT(pt.id) as track_count, p.created_at
                FROM playlists p
                LEFT JOIN playlist_tracks pt ON p.id = pt.playlist_id
                WHERE p.guild_id = ? AND p.owner_id = ?
                GROUP BY p.id
                ORDER BY p.created_at DESC
            """, (guild_id, owner_id))
            results = await cursor.fetchall()
            
            return [
                {
                    "name": row[0],
                    "track_count": row[1],
                    "created_at": row[2]
                }
                for row in results
            ]
    
    # ============== Playlist Tracks ==============
    
    async def add_track_to_playlist(
        self,
        playlist_id: int,
        track_uri: str,
        track_title: str,
        track_author: str,
        position: int
    ):
        """Add a track to a playlist."""
        async with self.db.cursor() as cursor:
            await cursor.execute("""
                INSERT INTO playlist_tracks (playlist_id, track_uri, track_title, track_author, position)
                VALUES (?, ?, ?, ?, ?)
            """, (playlist_id, track_uri, track_title, track_author, position))
            await self.db.commit()
    
    async def get_playlist_tracks(self, playlist_id: int) -> List[Dict[str, Any]]:
        """Get all tracks from a playlist."""
        async with self.db.cursor() as cursor:
            await cursor.execute("""
                SELECT track_uri, track_title, track_author, position
                FROM playlist_tracks
                WHERE playlist_id = ?
                ORDER BY position
            """, (playlist_id,))
            results = await cursor.fetchall()
            
            return [
                {
                    "uri": row[0],
                    "title": row[1],
                    "author": row[2],
                    "position": row[3]
                }
                for row in results
            ]
    
    async def clear_playlist_tracks(self, playlist_id: int):
        """Remove all tracks from a playlist."""
        async with self.db.cursor() as cursor:
            await cursor.execute(
                "DELETE FROM playlist_tracks WHERE playlist_id = ?",
                (playlist_id,)
            )
            await self.db.commit()


# Global database instance
db = Database()
