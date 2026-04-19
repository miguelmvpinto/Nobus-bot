import discord
from discord.ext import commands
from config_utils import get_server_config


class Welcome(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        config  = get_server_config(member.guild.id)
        channel_id = config.get("welcome_channel")

        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title=f"👋 Welcome to {member.guild.name}!",
            description=f"Hey {member.mention}, glad to have you here! Make yourself at home. 🎉",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Member #", value=str(member.guild.member_count), inline=True)
        embed.add_field(name="Account created", value=discord.utils.format_dt(member.created_at, style="R"), inline=True)
        embed.set_footer(text=f"Joined on {discord.utils.format_dt(member.joined_at, style='D')}")

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        config     = get_server_config(member.guild.id)
        channel_id = config.get("welcome_channel")

        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        embed = discord.Embed(
            title="👋 Someone left...",
            description=f"**{member.name}** has left the server. Goodbye!",
            color=discord.Color.red()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"{member.guild.member_count} members remaining")

        await channel.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Welcome(bot))