import discord
from discord.ext import commands
from discord import app_commands
import datetime

class Admin(commands.Cog):
    """Comandos de administração do servidor"""

    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Expulsa um membro do servidor")
    @app_commands.describe(membro="O membro a expulsar", motivo="Motivo da expulsão")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction,
                   membro: discord.Member, motivo: str = "Sem motivo"):
        try:
            await membro.kick(reason=motivo)
            await interaction.response.send_message(
                f"👢 **{membro.name}** foi expulso. Motivo: {motivo}"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para expulsar este membro."
            )

    @app_commands.command(name="ban", description="Bane um membro do servidor")
    @app_commands.describe(membro="O membro a banir", motivo="Motivo do ban",
                           delete_dias="Apagar mensagens dos últimos X dias (0-7)")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction,
                  membro: discord.Member, motivo: str = "Sem motivo",
                  delete_dias: int = 0):
        try:
            await membro.ban(reason=motivo, delete_message_days=delete_dias)
            await interaction.response.send_message(
                f"🔨 **{membro.name}** foi banido. Motivo: {motivo}"
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para banir este membro."
            )

    @app_commands.command(name="mute", description="Coloca um membro em silêncio")
    @app_commands.describe(membro="O membro a silenciar",
                           minutos="Duração em minutos (máx. 40320 = 28 dias)")
    @app_commands.default_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction,
                   membro: discord.Member, minutos: int = 10):
        try:
            duration = datetime.timedelta(minutes=minutos)
            await membro.timeout(duration, reason="Timeout pelo admin")
            await interaction.response.send_message(
                f"🔇 **{membro.name}** silenciado por {minutos} minuto(s)."
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Não tenho permissão para silenciar este membro."
            )

    @app_commands.command(name="unmute", description="Remove o silêncio de um membro")
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, membro: discord.Member):
        try:
            await membro.timeout(None)
            await interaction.response.send_message(
                f"🔊 **{membro.name}** já pode falar novamente."
            )
        except discord.Forbidden:
            await interaction.response.send_message("❌ Sem permissão.")

    @app_commands.command(name="clear", description="Apaga mensagens do canal")
    @app_commands.describe(quantidade="Número de mensagens a apagar (1-100)")
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, quantidade: int = 10):
        if not 1 <= quantidade <= 100:
            await interaction.response.send_message(
                "❌ Quantidade deve ser entre 1 e 100."
            )
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=quantidade)
        await interaction.followup.send(
            f"🗑️ {len(deleted)} mensagem(ns) apagada(s).", ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(Admin(bot))