import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

# Carrega variáveis do ficheiro .env
load_dotenv()

# Intents = permissões de "ouvir" eventos
intents = discord.Intents.default()
intents.message_content = True  # Para ler mensagens
intents.members = True          # Para acesso a membros

# Prefixo "!" para comandos de texto
# sync_commands=True sincroniza slash commands
bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None  # Vamos criar o nosso próprio
)

@bot.event
async def on_ready():
    """Executado quando o bot liga com sucesso"""
    print(f"✅ Bot ligado como: {bot.user}")
    print(f"📡 Em {len(bot.guilds)} servidor(es)")
    # Sincroniza slash commands com o Discord
    try:
        synced = await bot.tree.sync()
        print(f"🔄 {len(synced)} slash command(s) sincronizado(s)")
    except Exception as e:
        print(f"❌ Erro ao sincronizar: {e}")

async def load_cogs():
    """Carrega todos os Cogs da pasta cogs/"""
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and filename != "__init__.py":
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Cog carregado: {filename}")
            except Exception as e:
                print(f"❌ Erro ao carregar {filename}: {e}")

@bot.event
async def on_command_error(ctx, error):
    """Tratamento global de erros"""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Não tens permissão para usar este comando.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Membro não encontrado.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignora comandos desconhecidos silenciosamente
    else:
        await ctx.send(f"❌ Erro inesperado: {error}")
        raise error  # Re-lança para ver no terminal

# Ponto de entrada
import asyncio

async def main():
    async with bot:
        await load_cogs()
        await bot.start(os.getenv("DISCORD_TOKEN"))

asyncio.run(main())