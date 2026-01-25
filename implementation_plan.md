# Implementation Plan: Discord Music Bot Critical Fixes

This plan addresses the critical issues identified in the investigation report comparing your bot with PrimeMusic-Lavalink.

---

## User Review Required

> [!IMPORTANT]
> **Breaking Changes:** None. All fixes are backwards compatible.

> [!WARNING]
> **YouTube OAuth Token:** Your current `application.yml` requires a `YOUTUBE_REFRESH_TOKEN` environment variable that isn't documented. This may cause YouTube playback failures. The plan includes documenting this requirement and making it optional.

---

## Proposed Changes

### Critical Bug Fixes

#### [MODIFY] [bot.py](file:///f:/work/Ai/workflow/discord-music-bot/bot.py)

**Issue 1: Duplicate Event Handler (Lines 547-553)**
- Remove the duplicate `on_wavelink_track_end` event handler outside the class
- The class method (lines 113-121) already handles this functionality
- Having both causes unpredictable behavior

**Issue 2: Queue Auto-play Logic (Line 278-279)**
- Fix potential issue where first track might be skipped
- Ensure proper queue handling when starting playback

**Enhancement: Add Node Reconnection Handler**
- Add `on_wavelink_node_closed` event handler
- Automatically reconnect when Lavalink node disconnects
- Improves reliability and reduces manual restarts

**Enhancement: Improve Error Handling**
- Replace generic `Exception` catches with specific wavelink exceptions
- Provide user-friendly error messages
- Add proper logging for debugging

---

#### [MODIFY] [.env.example](file:///f:/work/Ai/workflow/discord-music-bot/.env.example)

**Missing Environment Variables:**
- Add `YOUTUBE_REFRESH_TOKEN` (optional, for YouTube OAuth)
- Add `YTDLP_ENABLED` (optional, defaults to false)
- Add `YTDLP_COOKIES_PATH` (optional, for yt-dlp cookie file)
- Add `YTDLP_CACHE_TTL` (optional, cache time-to-live)

These variables are referenced in `config.py` but not documented.

---

#### [MODIFY] [config.py](file:///f:/work/Ai/workflow/discord-music-bot/config.py)

**Improve yt-dlp Configuration:**
- Make yt-dlp cookies optional (don't fail if file doesn't exist)
- Add better logging for configuration issues
- Ensure graceful degradation when yt-dlp is disabled

---

#### [MODIFY] [application.yml](file:///f:/work/Ai/workflow/discord-music-bot/application.yml)

**YouTube OAuth Configuration:**
- Make `refreshToken` optional by providing a default empty value
- Add comments explaining when YouTube OAuth is needed
- Document how to obtain a refresh token

---

#### [MODIFY] [README.md](file:///f:/work/Ai/workflow/discord-music-bot/README.md)

**Documentation Improvements:**
- Add section on YouTube OAuth setup (optional)
- Document yt-dlp cookie setup for age-restricted videos
- Add troubleshooting section for YouTube playback issues
- Link to guide for obtaining YouTube refresh token

---

## Verification Plan

### Automated Tests

Since there are no existing unit tests in the project, verification will be done through manual testing and runtime checks.

### Manual Verification

#### Test 1: Verify Duplicate Handler Removal
1. Start the bot: `python bot.py`
2. Check logs for any duplicate event handler warnings
3. Play a song and let it finish naturally
4. Verify the next song in queue plays automatically (if queue has songs)
5. **Expected:** No errors, smooth transition to next track

#### Test 2: YouTube Playback
1. Join a voice channel
2. Test YouTube search: `!play never gonna give you up`
3. Test YouTube URL: `!play https://www.youtube.com/watch?v=dQw4w9WgXcQ`
4. Test YouTube playlist: `!play https://www.youtube.com/playlist?list=PLx0sYbCqOb8TBPRdmBHs5Iftvv9TPboYG`
5. **Expected:** All should play without errors

#### Test 3: Spotify Playback (if configured)
1. Test Spotify track: `!play https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8`
2. Test Spotify playlist: `!play https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M`
3. **Expected:** Tracks load and play correctly

#### Test 4: SoundCloud Fallback
1. Test SoundCloud search: `!play scsearch:lofi hip hop`
2. **Expected:** Should find and play SoundCloud tracks

#### Test 5: Error Handling
1. Try playing an invalid URL: `!play https://invalid-url.com`
2. Try playing with no results: `!play asdfjkl;qwertyuiop`
3. **Expected:** User-friendly error messages, no crashes

#### Test 6: Node Reconnection (if applicable)
1. Start the bot with Lavalink running
2. Stop Lavalink server
3. Wait 5-10 seconds
4. Restart Lavalink server
5. **Expected:** Bot should reconnect automatically and log reconnection

#### Test 7: Queue Management
1. Add multiple songs to queue: `!play song1`, `!play song2`, `!play song3`
2. Check queue: `!queue`
3. Let first song finish
4. **Expected:** Second song should auto-play

#### Test 8: Environment Variables
1. Check that bot starts without `YOUTUBE_REFRESH_TOKEN` set
2. Check that bot starts without yt-dlp cookies
3. **Expected:** Bot should start successfully with warnings in logs

---

## Testing Checklist

- [ ] Bot starts without errors
- [ ] YouTube search works
- [ ] YouTube URL playback works
- [ ] Spotify playback works (if configured)
- [ ] SoundCloud fallback works
- [ ] Queue auto-play works correctly
- [ ] Error messages are user-friendly
- [ ] No duplicate event handler warnings
- [ ] Environment variables are documented
- [ ] README includes troubleshooting guide

---

## Notes

- All changes maintain backwards compatibility
- No database migrations needed (no database in current implementation)
- Docker deployment should work without changes
- Lavalink configuration may need YouTube refresh token for best reliability
