import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio
import os
import re
import tempfile
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from config_utils import get_server_config, is_correct_channel, get_channel_mention

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

cookies_content = os.getenv('YOUTUBE_COOKIES')
cookies_file = None
if cookies_content:
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
    tmp.write(cookies_content)
    tmp.close()
    cookies_file = tmp.name

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
}
if cookies_file:
    YDL_OPTIONS['cookiefile'] = cookies_file

YDL_PLAYLIST_OPTIONS = {
    **YDL_OPTIONS,
    'noplaylist': False,
    'extract_flat': True,
}

SPOTIFY_CLIENT_ID     = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

sp = None
if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
    sp = spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        )
    )

class Track:
    def __init__(self, url: str, title: str, duration: int = 0,
                 thumbnail: str = None, requester: discord.Member = None,
                 webpage_url: str = None):
        self.url        = url           # stream URL
        self.title      = title
        self.duration   = duration      # seconds
        self.thumbnail  = thumbnail
        self.requester  = requester
        self.webpage_url = webpage_url  # YouTube page URL

    @property
    def duration_str(self) -> str:
        if not self.duration:
            return "?"
        m, s = divmod(self.duration, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"

    def embed(self, status: str = "🎵 Now Playing") -> discord.Embed:
        e = discord.Embed(
            title=status,
            description=f"**[{self.title}]({self.webpage_url or self.url})**",
            color=discord.Color.blurple()
        )
        e.add_field(name="Duration", value=self.duration_str, inline=True)
        if self.requester:
            e.add_field(name="Requested by", value=self.requester.mention, inline=True)
        if self.thumbnail:
            e.set_thumbnail(url=self.thumbnail)
        return e


# ─────────────────────────────────────────────
#  Regex helpers
# ─────────────────────────────────────────────
YOUTUBE_PLAYLIST_RE = re.compile(r'(?:youtube\.com|youtu\.be).*[?&]list=([^&]+)')
SPOTIFY_TRACK_RE    = re.compile(r'open\.spotify\.com/track/([A-Za-z0-9]+)')
SPOTIFY_PLAYLIST_RE = re.compile(r'open\.spotify\.com/playlist/([A-Za-z0-9]+)')
SPOTIFY_ALBUM_RE    = re.compile(r'open\.spotify\.com/album/([A-Za-z0-9]+)')

class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot    = bot
        self.queues: dict[int, list[Track]] = {}
        self.current: dict[int, Track]       = {}
        self.loop_mode: dict[int, str]       = {}
        self._ydl = yt_dlp.YoutubeDL(YDL_OPTIONS)

    # ── queue helpers ──────────────────────────
    def get_queue(self, guild_id: int) -> list[Track]:
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    def clear_guild(self, guild_id: int):
        self.queues.pop(guild_id, None)
        self.current.pop(guild_id, None)
        self.loop_mode.pop(guild_id, None)

    # ── audio extraction ───────────────────────
    async def _fetch_track(self, query: str, requester: discord.Member) -> Track:
        """Resolve a single query/URL into a Track (with stream URL)."""
        loop = asyncio.get_event_loop()

        if not query.startswith('http'):
            query = f'ytsearch:{query}'

        def _extract():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(query, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                return info

        info = await loop.run_in_executor(None, _extract)
        return Track(
            url         = info['url'],
            title       = info.get('title', 'Unknown'),
            duration    = info.get('duration', 0),
            thumbnail   = info.get('thumbnail'),
            requester   = requester,
            webpage_url = info.get('webpage_url'),
        )

    async def _fetch_youtube_playlist(self, url: str, requester: discord.Member) -> list[Track]:
        """Extract all tracks from a YouTube playlist (metadata only, stream URL resolved later)."""
        loop = asyncio.get_event_loop()

        def _extract():
            with yt_dlp.YoutubeDL(YDL_PLAYLIST_OPTIONS) as ydl:
                return ydl.extract_info(url, download=False)

        info = await loop.run_in_executor(None, _extract)
        tracks = []
        for entry in info.get('entries', []):
            if not entry:
                continue
            tracks.append(Track(
                url         = f"https://www.youtube.com/watch?v={entry.get('id', '')}",
                title       = entry.get('title', 'Unknown'),
                duration    = entry.get('duration', 0),
                thumbnail   = entry.get('thumbnail'),
                requester   = requester,
                webpage_url = f"https://www.youtube.com/watch?v={entry.get('id', '')}",
            ))
        return tracks

    async def _resolve_track_url(self, track: Track) -> Track:
        """Resolve a playlist entry (no stream URL yet) into a playable stream URL."""
        loop = asyncio.get_event_loop()
        def _extract():
            with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(track.url, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                return info
        info = await loop.run_in_executor(None, _extract)
        track.url       = info['url']
        track.thumbnail = info.get('thumbnail') or track.thumbnail
        track.duration  = info.get('duration') or track.duration
        return track

    async def _fetch_spotify_tracks(self, url: str, requester: discord.Member) -> list[Track]:
        """Convert Spotify track/playlist/album into YouTube search queries."""
        if sp is None:
            raise RuntimeError("Spotify credentials not configured. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET.")

        loop  = asyncio.get_event_loop()
        names = []  # list of "artist - title" strings

        track_m    = SPOTIFY_TRACK_RE.search(url)
        playlist_m = SPOTIFY_PLAYLIST_RE.search(url)
        album_m    = SPOTIFY_ALBUM_RE.search(url)

        if track_m:
            def _get():
                t = sp.track(track_m.group(1))
                return [f"{t['artists'][0]['name']} - {t['name']}"]
            names = await loop.run_in_executor(None, _get)

        elif playlist_m:
            def _get():
                results = sp.playlist_tracks(playlist_m.group(1))
                out = []
                while results:
                    for item in results['items']:
                        t = item.get('track')
                        if t:
                            out.append(f"{t['artists'][0]['name']} - {t['name']}")
                    results = sp.next(results) if results['next'] else None
                return out
            names = await loop.run_in_executor(None, _get)

        elif album_m:
            def _get():
                results = sp.album_tracks(album_m.group(1))
                out = []
                for t in results['items']:
                    out.append(f"{t['artists'][0]['name']} - {t['name']}")
                return out
            names = await loop.run_in_executor(None, _get)

        else:
            raise ValueError("Invalid Spotify URL.")

        # Create lightweight Track objects — stream URLs resolved on play
        return [
            Track(url=name, title=name, requester=requester)
            for name in names
        ]

    # ── playback ───────────────────────────────
    def _play_next(self, guild_id: int, vc: discord.VoiceClient, channel: discord.TextChannel):
        queue = self.get_queue(guild_id)
        mode  = self.loop_mode.get(guild_id, 'off')

        if mode == 'song' and guild_id in self.current:
            queue.insert(0, self.current[guild_id])

        if not queue:
            if mode == 'queue' and guild_id in self.current:
                pass  # nothing to loop
            self.current.pop(guild_id, None)
            asyncio.run_coroutine_threadsafe(
                channel.send(embed=discord.Embed(
                    description="✅ Queue finished. Use `/play` to add more music!",
                    color=discord.Color.green()
                )),
                self.bot.loop
            )
            return

        track = queue.pop(0)
        self.current[guild_id] = track

        # If this is a playlist entry (url is a YT page link, not a stream),
        # we need to resolve before playing
        if 'googlevideo' not in track.url and 'manifest' not in track.url:
            future = asyncio.run_coroutine_threadsafe(
                self._play_resolved(guild_id, vc, track, channel),
                self.bot.loop
            )
            return

        source = discord.FFmpegPCMAudio(track.url, **FFMPEG_OPTIONS)
        source = discord.PCMVolumeTransformer(source, volume=0.5)
        vc.play(source, after=lambda e: self._play_next(guild_id, vc, channel))

        asyncio.run_coroutine_threadsafe(
            channel.send(embed=track.embed()),
            self.bot.loop
        )

        if mode == 'queue':
            self.get_queue(guild_id).append(track)

    async def _play_resolved(self, guild_id: int, vc: discord.VoiceClient, track: Track, channel: discord.TextChannel):
        """Resolve stream URL then play."""
        try:
            track = await self._resolve_track_url(track)
        except Exception as e:
            await channel.send(f"⚠️ Skipping **{track.title}** — could not fetch audio: `{e}`")
            self._play_next(guild_id, vc, channel)
            return

        source = discord.FFmpegPCMAudio(track.url, **FFMPEG_OPTIONS)
        source = discord.PCMVolumeTransformer(source, volume=0.5)
        vc.play(source, after=lambda e: self._play_next(guild_id, vc, channel))
        await channel.send(embed=track.embed())

        mode = self.loop_mode.get(guild_id, 'off')
        if mode == 'queue':
            self.get_queue(guild_id).append(track)

    async def _ensure_voice(self, interaction: discord.Interaction):
        """Connect or move to user's voice channel. Returns VoiceClient or None."""
        if not interaction.user.voice:
            await interaction.followup.send("❌ Join a voice channel first!", ephemeral=True)
            return None
        channel = interaction.user.voice.channel
        vc = interaction.guild.voice_client
        if not vc:
            vc = await channel.connect()
        elif vc.channel != channel:
            await vc.move_to(channel)
        return vc

    async def _check_music_channel(self, interaction: discord.Interaction) -> bool:
        config = get_server_config(interaction.guild.id)
        if not is_correct_channel(interaction.channel.id, config, "music_channel"):
            mention = get_channel_mention(interaction.guild, config, "music_channel")
            await interaction.response.send_message(
                f"❌ Use music commands in {mention}.", ephemeral=True
            )
            return False
        return True

    # ── slash commands ─────────────────────────
    @app_commands.command(name="play", description="Play a song or playlist from YouTube or Spotify")
    @app_commands.describe(query="Song name, YouTube URL/playlist, or Spotify URL")
    async def play(self, interaction: discord.Interaction, query: str):
        if not await self._check_music_channel(interaction):
            return

        await interaction.response.defer()

        vc = await self._ensure_voice(interaction)
        if not vc:
            return

        guild_id = interaction.guild.id
        queue    = self.get_queue(guild_id)
        added    = 0

        try:
            # ── Spotify ──
            if 'open.spotify.com' in query:
                tracks = await self._fetch_spotify_tracks(query, interaction.user)
                queue.extend(tracks)
                added = len(tracks)
                kind = "track" if SPOTIFY_TRACK_RE.search(query) else ("playlist" if SPOTIFY_PLAYLIST_RE.search(query) else "album")
                embed = discord.Embed(
                    title="🎵 Spotify added to queue",
                    description=f"Added **{added}** {kind} track(s) to the queue.",
                    color=discord.Color.green()
                )
                embed.set_footer(text="Tracks will be searched on YouTube when played")
                await interaction.followup.send(embed=embed)

            # ── YouTube Playlist ──
            elif YOUTUBE_PLAYLIST_RE.search(query):
                tracks = await self._fetch_youtube_playlist(query, interaction.user)
                queue.extend(tracks)
                added = len(tracks)
                embed = discord.Embed(
                    title="📋 YouTube Playlist added",
                    description=f"Added **{added}** tracks to the queue.",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=embed)

            # ── Single YouTube/search ──
            else:
                track = await self._fetch_track(query, interaction.user)
                if vc.is_playing() or vc.is_paused():
                    queue.append(track)
                    embed = discord.Embed(
                        description=f"➕ Added to queue: **[{track.title}]({track.webpage_url or track.url})**\nPosition: `#{len(queue)}`",
                        color=discord.Color.blurple()
                    )
                    embed.add_field(name="Duration", value=track.duration_str)
                    if track.thumbnail:
                        embed.set_thumbnail(url=track.thumbnail)
                    await interaction.followup.send(embed=embed)
                    return
                else:
                    self.current[guild_id] = track
                    source = discord.FFmpegPCMAudio(track.url, **FFMPEG_OPTIONS)
                    source = discord.PCMVolumeTransformer(source, volume=0.5)
                    vc.play(source, after=lambda e: self._play_next(guild_id, vc, interaction.channel))
                    await interaction.followup.send(embed=track.embed())
                    return

        except RuntimeError as e:
            await interaction.followup.send(f"❌ {e}", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"❌ Error fetching audio: `{e}`", ephemeral=True)
            return

        # Start playing if not already
        if not vc.is_playing() and not vc.is_paused() and queue:
            track = queue.pop(0)
            self.current[guild_id] = track
            await self._play_resolved(guild_id, vc, track, interaction.channel)

    @app_commands.command(name="skip", description="Skip the current song")
    async def skip(self, interaction: discord.Interaction):
        if not await self._check_music_channel(interaction):
            return
        vc = interaction.guild.voice_client
        if vc and (vc.is_playing() or vc.is_paused()):
            vc.stop()
            await interaction.response.send_message("⏭️ Skipped.")
        else:
            await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)

    @app_commands.command(name="pause", description="Pause or resume the current song")
    async def pause(self, interaction: discord.Interaction):
        if not await self._check_music_channel(interaction):
            return
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Paused.")
        elif vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Resumed.")
        else:
            await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)

    @app_commands.command(name="stop", description="Stop music and disconnect the bot")
    async def stop(self, interaction: discord.Interaction):
        if not await self._check_music_channel(interaction):
            return
        vc = interaction.guild.voice_client
        if vc:
            self.clear_guild(interaction.guild.id)
            await vc.disconnect()
            await interaction.response.send_message("⏹️ Stopped and disconnected.")
        else:
            await interaction.response.send_message("❌ Not in a voice channel.", ephemeral=True)

    @app_commands.command(name="queue", description="Show the current music queue")
    async def queue_cmd(self, interaction: discord.Interaction):
        if not await self._check_music_channel(interaction):
            return
        guild_id = interaction.guild.id
        queue    = self.get_queue(guild_id)
        current  = self.current.get(guild_id)
        mode     = self.loop_mode.get(guild_id, 'off')

        embed = discord.Embed(title="🎶 Music Queue", color=discord.Color.blurple())

        if current:
            embed.add_field(
                name="▶️ Now Playing",
                value=f"**{current.title}** ({current.duration_str}) — {current.requester.mention if current.requester else ''}",
                inline=False
            )

        if queue:
            lines = []
            for i, t in enumerate(queue[:15], 1):
                lines.append(f"`{i}.` **{t.title}** ({t.duration_str})")
            if len(queue) > 15:
                lines.append(f"*... and {len(queue) - 15} more*")
            embed.add_field(name=f"📋 Up Next ({len(queue)} tracks)", value="\n".join(lines), inline=False)
        else:
            embed.add_field(name="📋 Up Next", value="Queue is empty.", inline=False)

        embed.set_footer(text=f"Loop mode: {mode}")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nowplaying", description="Show info about the current song")
    async def nowplaying(self, interaction: discord.Interaction):
        if not await self._check_music_channel(interaction):
            return
        current = self.current.get(interaction.guild.id)
        if not current:
            await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)
            return
        await interaction.response.send_message(embed=current.embed("🎵 Now Playing"))

    @app_commands.command(name="volume", description="Set the playback volume (0–100)")
    @app_commands.describe(level="Volume level from 0 to 100")
    async def volume(self, interaction: discord.Interaction, level: app_commands.Range[int, 0, 100]):
        if not await self._check_music_channel(interaction):
            return
        vc = interaction.guild.voice_client
        if vc and isinstance(vc.source, discord.PCMVolumeTransformer):
            vc.source.volume = level / 100
            await interaction.response.send_message(f"🔊 Volume set to **{level}%**")
        else:
            await interaction.response.send_message("❌ Nothing is playing.", ephemeral=True)

    @app_commands.command(name="loop", description="Set loop mode: off, song, or queue")
    @app_commands.describe(mode="off = no loop | song = repeat current | queue = repeat all")
    @app_commands.choices(mode=[
        app_commands.Choice(name="Off",   value="off"),
        app_commands.Choice(name="Song",  value="song"),
        app_commands.Choice(name="Queue", value="queue"),
    ])
    async def loop(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        if not await self._check_music_channel(interaction):
            return
        self.loop_mode[interaction.guild.id] = mode.value
        icons = {'off': '➡️', 'song': '🔂', 'queue': '🔁'}
        await interaction.response.send_message(f"{icons[mode.value]} Loop mode set to **{mode.name}**.")

    @app_commands.command(name="shuffle", description="Shuffle the current queue")
    async def shuffle(self, interaction: discord.Interaction):
        if not await self._check_music_channel(interaction):
            return
        import random
        queue = self.get_queue(interaction.guild.id)
        if len(queue) < 2:
            await interaction.response.send_message("❌ Not enough songs in queue to shuffle.", ephemeral=True)
            return
        random.shuffle(queue)
        await interaction.response.send_message("🔀 Queue shuffled!")

    @app_commands.command(name="remove", description="Remove a song from the queue by position")
    @app_commands.describe(position="Position in the queue (use /queue to see positions)")
    async def remove(self, interaction: discord.Interaction, position: int):
        if not await self._check_music_channel(interaction):
            return
        queue = self.get_queue(interaction.guild.id)
        if position < 1 or position > len(queue):
            await interaction.response.send_message("❌ Invalid position.", ephemeral=True)
            return
        removed = queue.pop(position - 1)
        await interaction.response.send_message(f"🗑️ Removed **{removed.title}** from the queue.")

    @app_commands.command(name="clearqueue", description="Clear the entire queue")
    async def clearqueue(self, interaction: discord.Interaction):
        if not await self._check_music_channel(interaction):
            return
        self.queues[interaction.guild.id] = []
        await interaction.response.send_message("🗑️ Queue cleared.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Music(bot))