import discord
from discord.ext import commands
from discord import app_commands
from config_utils import get_server_config, is_correct_channel, get_channel_mention


class Help(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="help", description="Show all available bot commands")
    async def help(self, interaction: discord.Interaction):
        config = get_server_config(interaction.guild.id)
        if not is_correct_channel(interaction.channel.id, config, "bot_channel"):
            mention = get_channel_mention(interaction.guild, config, "bot_channel")
            await interaction.response.send_message(
                f"❌ Use bot commands in {mention}.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="📖 Nobus Bot — Command List",
            description="Here are all available commands:",
            color=discord.Color.blurple()
        )

        embed.add_field(
            name="🎵 Music",
            value=(
                "`/play <query>` — Play a song or playlist (YouTube URL, Spotify URL, or song name)\n"
                "`/skip` — Skip the current song\n"
                "`/pause` — Pause / resume playback\n"
                "`/stop` — Stop and disconnect\n"
                "`/queue` — Show the current queue\n"
                "`/nowplaying` — Info about the current song\n"
                "`/volume <0-100>` — Set playback volume\n"
                "`/loop <off/song/queue>` — Set loop mode\n"
                "`/shuffle` — Shuffle the queue\n"
                "`/remove <position>` — Remove a song from the queue\n"
                "`/clearqueue` — Clear the entire queue"
            ),
            inline=False
        )

        embed.add_field(
            name="🛡️ Administration",
            value=(
                "`/kick <member>` — Kick a member\n"
                "`/ban <member>` — Ban a member\n"
                "`/unban <user_id>` — Unban a user by ID\n"
                "`/mute <member> <minutes>` — Timeout a member\n"
                "`/unmute <member>` — Remove a timeout\n"
                "`/clear <amount>` — Delete messages (max 100)\n"
                "`/slowmode <seconds>` — Set channel slowmode"
            ),
            inline=False
        )

        embed.add_field(
            name="🎮 Free Games",
            value=(
                "`/freegames` — Show current free games on Epic & Steam\n"
                "🔔 Automatic alerts every 6 hours in the configured channel"
            ),
            inline=False
        )

        embed.add_field(
            name="⚙️ Setup & Config",
            value=(
                "`/setup` — Configure bot channels (Admin only)\n"
                "`/config` — View current configuration (Admin only)\n"
                "`/resetconfig` — Clear all settings (Admin only)"
            ),
            inline=False
        )

        embed.add_field(
            name="👋 Welcome",
            value="Automatic welcome & goodbye messages in the configured channel.",
            inline=False
        )

        embed.set_footer(text="Nobus Bot • Use / to see commands directly in Discord")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Help(bot))