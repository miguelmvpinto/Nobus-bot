import discord
from discord.ext import commands

WELCOME_CHANNEL_NAME = "👋welcome"

class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        channel = discord.utils.get(member.guild.text_channels, name=WELCOME_CHANNEL_NAME)
        if not channel:
            return

        embed = discord.Embed(
            title=f"👋 Bem-vindo ao {member.guild.name}!",
            description=f"Olá {member.mention}! Fica à vontade e diverte-te!",
            color=discord.Color.blurple()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Membro nº", value=str(member.guild.member_count), inline=True)
        embed.set_footer(text=f"Juntou-se em {member.joined_at.strftime('%d/%m/%Y')}")

        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Welcome(bot))