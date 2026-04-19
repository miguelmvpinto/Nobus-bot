import discord
from discord.ext import commands
from discord import app_commands
import datetime
from config_utils import get_server_config, is_correct_channel, get_channel_mention


class Admin(commands.Cog):
    """Server administration commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _check_bot_channel(self, interaction: discord.Interaction) -> bool:
        config = get_server_config(interaction.guild.id)
        if not is_correct_channel(interaction.channel.id, config, "bot_channel"):
            mention = get_channel_mention(interaction.guild, config, "bot_channel")
            await interaction.response.send_message(
                f"❌ Use bot commands in {mention}.", ephemeral=True
            )
            return False
        return True

    # ── Kick ──────────────────────────────────
    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="The member to kick", reason="Reason for the kick")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction,
                   member: discord.Member, reason: str = "No reason provided"):
        if not await self._check_bot_channel(interaction):
            return
        try:
            await member.kick(reason=reason)
            embed = discord.Embed(
                title="👢 Member Kicked",
                description=f"**{member.name}** has been kicked.\n**Reason:** {reason}",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to kick this member.", ephemeral=True)

    # ── Ban ───────────────────────────────────
    @app_commands.command(name="ban", description="Ban a member from the server")
    @app_commands.describe(member="The member to ban", reason="Reason for the ban",
                           delete_days="Delete messages from the last X days (0-7)")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction,
                  member: discord.Member, reason: str = "No reason provided",
                  delete_days: int = 0):
        if not await self._check_bot_channel(interaction):
            return
        try:
            await member.ban(reason=reason, delete_message_days=delete_days)
            embed = discord.Embed(
                title="🔨 Member Banned",
                description=f"**{member.name}** has been banned.\n**Reason:** {reason}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to ban this member.", ephemeral=True)

    # ── Unban ─────────────────────────────────
    @app_commands.command(name="unban", description="Unban a user by their ID")
    @app_commands.describe(user_id="The user ID to unban")
    @app_commands.default_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):
        if not await self._check_bot_channel(interaction):
            return
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user)
            embed = discord.Embed(
                title="✅ Member Unbanned",
                description=f"**{user.name}** has been unbanned.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        except discord.NotFound:
            await interaction.response.send_message("❌ User not found or not banned.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to unban members.", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID.", ephemeral=True)

    # ── Mute (timeout) ────────────────────────
    @app_commands.command(name="mute", description="Timeout a member for a set duration")
    @app_commands.describe(member="The member to mute", minutes="Duration in minutes (max 40320 = 28 days)")
    @app_commands.default_permissions(moderate_members=True)
    async def mute(self, interaction: discord.Interaction,
                   member: discord.Member, minutes: int = 10):
        if not await self._check_bot_channel(interaction):
            return
        try:
            duration = datetime.timedelta(minutes=minutes)
            await member.timeout(duration, reason=f"Timed out by {interaction.user}")
            embed = discord.Embed(
                title="🔇 Member Muted",
                description=f"**{member.name}** has been timed out for **{minutes} minute(s)**.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to timeout this member.", ephemeral=True)

    # ── Unmute ────────────────────────────────
    @app_commands.command(name="unmute", description="Remove a timeout from a member")
    @app_commands.describe(member="The member to unmute")
    @app_commands.default_permissions(moderate_members=True)
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        if not await self._check_bot_channel(interaction):
            return
        try:
            await member.timeout(None)
            embed = discord.Embed(
                title="🔊 Member Unmuted",
                description=f"**{member.name}** can speak again.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to unmute this member.", ephemeral=True)

    # ── Clear ─────────────────────────────────
    @app_commands.command(name="clear", description="Delete messages from this channel")
    @app_commands.describe(amount="Number of messages to delete (1–100)")
    @app_commands.default_permissions(manage_messages=True)
    async def clear(self, interaction: discord.Interaction, amount: int = 10):
        if not 1 <= amount <= 100:
            await interaction.response.send_message("❌ Amount must be between 1 and 100.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"🗑️ Deleted **{len(deleted)}** message(s).", ephemeral=True)

    # ── Slowmode ──────────────────────────────
    @app_commands.command(name="slowmode", description="Set slowmode delay for this channel")
    @app_commands.describe(seconds="Delay in seconds (0 to disable, max 21600)")
    @app_commands.default_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int = 0):
        if not await self._check_bot_channel(interaction):
            return
        if not 0 <= seconds <= 21600:
            await interaction.response.send_message("❌ Slowmode must be between 0 and 21600 seconds.", ephemeral=True)
            return
        await interaction.channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await interaction.response.send_message("✅ Slowmode **disabled**.")
        else:
            await interaction.response.send_message(f"🐢 Slowmode set to **{seconds}s**.")


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))