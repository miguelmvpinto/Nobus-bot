import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

async def load_cogs():
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Cog loaded: {filename}")
            except Exception as e:
                print(f"❌ Error loading {filename}: {e}")

@bot.event
async def setup_hook():
    """Runs before the bot connects — loads cogs and syncs commands globally."""
    await load_cogs()
    try:
        synced = await bot.tree.sync()
        print(f"🔄 {len(synced)} slash command(s) synced globally")
    except Exception as e:
        print(f"❌ Sync error: {e}")

@bot.event
async def on_ready():
    print(f"✅ Bot online as: {bot.user}")
    print(f"📡 In {len(bot.guilds)} server(s)")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found.")
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        await ctx.send(f"❌ Unexpected error: {error}")
        raise error

async def main():
    async with bot:
        await bot.start(os.getenv("DISCORD_TOKEN"))

asyncio.run(main())