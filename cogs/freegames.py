import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import json
from datetime import datetime

ALERT_CHANNEL_NAME = "📰free-games"

class FreeGames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sent_games = set()
        self.check_free_games.start()

    def cog_unload(self):
        self.check_free_games.cancel()

    @tasks.loop(hours=6)
    async def check_free_games(self):
        await self.bot.wait_until_ready()
        games = []

        # Epic Games
        try:
            epic = await self.get_epic_games()
            games.extend(epic)
        except Exception as e:
            print(f"Erro Epic Games: {e}")

        # Steam
        try:
            steam = await self.get_steam_games()
            games.extend(steam)
        except Exception as e:
            print(f"Erro Steam: {e}")

        for guild in self.bot.guilds:
            channel = discord.utils.get(guild.text_channels, name=ALERT_CHANNEL_NAME)
            if not channel:
                continue

            for game in games:
                game_id = f"{game['source']}_{game['title']}"
                if game_id in self.sent_games:
                    continue

                embed = discord.Embed(
                    title=f"🎮 Jogo Grátis — {game['source']}",
                    description=f"**{game['title']}**\n{game.get('description', '')}",
                    color=discord.Color.green(),
                    url=game.get('url', '')
                )
                if game.get('image'):
                    embed.set_image(url=game['image'])
                if game.get('end_date'):
                    embed.add_field(name="Disponível até", value=game['end_date'], inline=True)
                embed.set_footer(text=f"Fonte: {game['source']}")

                await channel.send(embed=embed)
                self.sent_games.add(game_id)

    async def get_epic_games(self):
        url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=pt&country=PT&allowCountries=PT"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        games = []
        elements = data['data']['Catalog']['searchStore']['elements']
        for game in elements:
            promotions = game.get('promotions')
            if not promotions:
                continue
            offers = promotions.get('promotionalOffers', [])
            for offer_group in offers:
                for offer in offer_group.get('promotionalOffers', []):
                    if offer['discountSetting']['discountPercentage'] == 0:
                        end = offer['endDate'][:10]
                        img = None
                        for key_img in game.get('keyImages', []):
                            if key_img['type'] == 'Thumbnail':
                                img = key_img['url']
                                break
                        games.append({
                            'title': game['title'],
                            'description': game.get('description', '')[:100],
                            'source': 'Epic Games',
                            'url': f"https://store.epicgames.com/pt-BR/p/{game.get('productSlug', '')}",
                            'image': img,
                            'end_date': end
                        })
        return games

    async def get_steam_games(self):
        url = "https://store.steampowered.com/api/featuredcategories?cc=pt"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                data = await resp.json()

        games = []
        specials = data.get('specials', {}).get('items', [])
        for game in specials:
            if game.get('discount_percent') == 100:
                games.append({
                    'title': game['name'],
                    'description': 'Jogo grátis na Steam!',
                    'source': 'Steam',
                    'url': f"https://store.steampowered.com/app/{game['id']}",
                    'image': game.get('large_capsule_image'),
                    'end_date': None
                })
        return games

    @app_commands.command(name="freegames", description="Mostra os jogos grátis agora")
    async def freegames_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        games = []

        try:
            games.extend(await self.get_epic_games())
        except:
            pass
        try:
            games.extend(await self.get_steam_games())
        except:
            pass

        if not games:
            await interaction.followup.send("😔 Nenhum jogo grátis encontrado neste momento.")
            return

        for game in games:
            embed = discord.Embed(
                title=f"🎮 {game['title']}",
                description=game.get('description', ''),
                color=discord.Color.green(),
                url=game.get('url', '')
            )
            embed.set_footer(text=f"Fonte: {game['source']}")
            if game.get('image'):
                embed.set_image(url=game['image'])
            if game.get('end_date'):
                embed.add_field(name="Até", value=game['end_date'], inline=True)
            await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(FreeGames(bot))