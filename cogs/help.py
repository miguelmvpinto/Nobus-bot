import discord
from discord.ext import commands
from discord import app_commands

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="Mostra todos os comandos disponíveis")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Comandos do NOBUS-BOT",
            description="Aqui estão todos os comandos disponíveis:",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🎵 Música",
            value=(
                "`/play` — Pesquisa e toca uma música do YouTube\n"
                "`/skip` — Salta para a próxima música da fila\n"
                "`/pause` — Pausa ou retoma a música atual\n"
                "`/stop` — Para a música e sai do canal de voz\n"
                "`/queue` — Mostra as músicas na fila"
            ),
            inline=False
        )

        embed.add_field(
            name="🛡️ Administração",
            value=(
                "`/kick` — Expulsa um membro do servidor\n"
                "`/ban` — Bane um membro do servidor\n"
                "`/mute` — Silencia um membro por X minutos\n"
                "`/unmute` — Remove o silêncio de um membro\n"
                "`/clear` — Apaga mensagens do canal (máx. 100)"
            ),
            inline=False
        )

        embed.add_field(
            name="🎮 Free Games",
            value=(
                "`/freegames` — Mostra os jogos grátis agora na Epic e Steam\n"
                "🔔 Alertas automáticos a cada 6 horas no canal `#free-games`"
            ),
            inline=False
        )

        embed.add_field(
            name="👋 Boas-vindas",
            value="Mensagem automática no canal `#boas-vindas` quando alguém entra",
            inline=False
        )

        embed.set_footer(text="NOBUS-BOT • Usa / para ver os comandos diretamente")
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Help(bot))