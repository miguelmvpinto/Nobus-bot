import discord
from discord.ext import commands
from discord import app_commands
import yt_dlp
import asyncio

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
}

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}

    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        return self.queues[guild_id]

    async def get_audio(self, query):
        loop = asyncio.get_event_loop()
        # Se não for URL, pesquisa no YouTube
        if not query.startswith('http'):
            query = f'ytsearch:{query}'
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
            if 'entries' in info:
                info = info['entries'][0]
            return info['url'], info.get('title', 'Desconhecido')

    def play_next(self, interaction, vc):
        queue = self.get_queue(interaction.guild.id)
        if queue:
            url, title = queue.pop(0)
            source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
            vc.play(source, after=lambda e: self.play_next(interaction, vc))

    @app_commands.command(name="play", description="Toca uma música do YouTube")
    @app_commands.describe(query="Nome da música ou URL")
    async def play(self, interaction: discord.Interaction, query: str):
        if not interaction.user.voice:
            await interaction.response.send_message("❌ Entra num canal de voz primeiro!", ephemeral=True)
            return

        await interaction.response.defer()

        try:
            url, title = await self.get_audio(query)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao pesquisar: {e}")
            return

        vc = interaction.guild.voice_client
        channel = interaction.user.voice.channel

        if not vc:
            vc = await channel.connect()
        elif vc.channel != channel:
            await vc.move_to(channel)

        if vc.is_playing() or vc.is_paused():
            self.get_queue(interaction.guild.id).append((url, title))
            await interaction.followup.send(f"➕ **{title}** adicionado à fila.")
        else:
            source = discord.FFmpegPCMAudio(url, **FFMPEG_OPTIONS)
            vc.play(source, after=lambda e: self.play_next(interaction, vc))
            await interaction.followup.send(f"🎵 A tocar: **{title}**")

    @app_commands.command(name="skip", description="Salta a música atual")
    async def skip(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.stop()
            await interaction.response.send_message("⏭️ Saltado.")
        else:
            await interaction.response.send_message("❌ Nada a tocar.", ephemeral=True)

    @app_commands.command(name="pause", description="Pausa ou retoma a música")
    async def pause(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc and vc.is_playing():
            vc.pause()
            await interaction.response.send_message("⏸️ Pausado.")
        elif vc and vc.is_paused():
            vc.resume()
            await interaction.response.send_message("▶️ Retomado.")
        else:
            await interaction.response.send_message("❌ Nada a tocar.", ephemeral=True)

    @app_commands.command(name="stop", description="Para a música e sai do canal")
    async def stop(self, interaction: discord.Interaction):
        vc = interaction.guild.voice_client
        if vc:
            self.queues.pop(interaction.guild.id, None)
            await vc.disconnect()
            await interaction.response.send_message("⏹️ Parado.")
        else:
            await interaction.response.send_message("❌ Não estou em nenhum canal.", ephemeral=True)

    @app_commands.command(name="queue", description="Mostra a fila de músicas")
    async def queue_cmd(self, interaction: discord.Interaction):
        queue = self.get_queue(interaction.guild.id)
        if not queue:
            await interaction.response.send_message("📭 A fila está vazia.")
            return
        lista = "\n".join([f"{i+1}. {t}" for i, (_, t) in enumerate(queue)])
        await interaction.response.send_message(f"🎶 **Fila:**\n{lista}")

async def setup(bot):
    await bot.add_cog(Music(bot))