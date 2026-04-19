import discord
from discord.ext import commands
from discord import app_commands
from discord.ext import tasks
import aiohttp
from config_utils import get_server_config


class FreeGames(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot        = bot
        self.sent_games: set[str] = set()
        self.check_free_games.start()

    def cog_unload(self):
        self.check_free_games.cancel()

    # ── Epic Games API ─────────────────────────
    async def get_epic_games(self) -> list[dict]:
        url = (
            "https://store-site-backend-static.ak.epicgames.com"
            "/freeGamesPromotions?locale=en&country=US&allowCountries=US"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json(content_type=None)

        games   = []
        elements = data["data"]["Catalog"]["searchStore"]["elements"]
        for game in elements:
            promos = game.get("promotions") or {}
            for offer_group in promos.get("promotionalOffers", []):
                for offer in offer_group.get("promotionalOffers", []):
                    if offer["discountSetting"]["discountPercentage"] == 0:
                        end_date = offer["endDate"][:10]
                        img = next(
                            (ki["url"] for ki in game.get("keyImages", []) if ki["type"] == "Thumbnail"),
                            None
                        )
                        slug = game.get("productSlug") or game.get("urlSlug") or ""
                        games.append({
                            "title":       game["title"],
                            "description": game.get("description", "")[:120],
                            "source":      "Epic Games",
                            "url":         f"https://store.epicgames.com/en-US/p/{slug}",
                            "image":       img,
                            "end_date":    end_date,
                        })
        return games

    # ── Steam API ──────────────────────────────
    async def get_steam_games(self) -> list[dict]:
        url = "https://store.steampowered.com/api/featuredcategories?cc=us"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json(content_type=None)

        games = []
        for game in data.get("specials", {}).get("items", []):
            if game.get("discount_percent") == 100:
                games.append({
                    "title":       game["name"],
                    "description": "Free on Steam right now!",
                    "source":      "Steam",
                    "url":         f"https://store.steampowered.com/app/{game['id']}",
                    "image":       game.get("large_capsule_image"),
                    "end_date":    None,
                })
        return games

    # ── Build embed ────────────────────────────
    def _game_embed(self, game: dict) -> discord.Embed:
        color = discord.Color.from_rgb(0, 0, 0) if game["source"] == "Epic Games" else discord.Color.from_rgb(23, 26, 33)
        embed = discord.Embed(
            title=f"🆓 Free Game — {game['source']}",
            description=f"**{game['title']}**\n{game.get('description', '')}",
            color=color,
            url=game.get("url", "")
        )
        if game.get("image"):
            embed.set_image(url=game["image"])
        if game.get("end_date"):
            embed.add_field(name="Available until", value=game["end_date"], inline=True)
        embed.set_footer(text=f"Source: {game['source']}")
        return embed

    # ── Automatic task ─────────────────────────
    @tasks.loop(hours=6)
    async def check_free_games(self):
        await self.bot.wait_until_ready()

        games = []
        try:
            games.extend(await self.get_epic_games())
        except Exception as e:
            print(f"[FreeGames] Epic error: {e}")
        try:
            games.extend(await self.get_steam_games())
        except Exception as e:
            print(f"[FreeGames] Steam error: {e}")

        for guild in self.bot.guilds:
            config     = get_server_config(guild.id)
            channel_id = config.get("freegames_channel")

            # Not configured or explicitly disabled
            if not channel_id:
                continue

            channel = guild.get_channel(channel_id)
            if not channel:
                continue

            for game in games:
                game_id = f"{game['source']}_{game['title']}"
                if game_id in self.sent_games:
                    continue
                try:
                    await channel.send(embed=self._game_embed(game))
                    self.sent_games.add(game_id)
                except discord.Forbidden:
                    pass

    # ── Manual command ─────────────────────────
    @app_commands.command(name="freegames", description="Show current free games on Epic Games and Steam")
    async def freegames_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()

        games = []
        try:
            games.extend(await self.get_epic_games())
        except Exception:
            pass
        try:
            games.extend(await self.get_steam_games())
        except Exception:
            pass

        if not games:
            await interaction.followup.send(
                embed=discord.Embed(
                    description="😔 No free games found at the moment. Check back later!",
                    color=discord.Color.orange()
                )
            )
            return

        await interaction.followup.send(
            embed=discord.Embed(
                title=f"🎮 {len(games)} Free Game(s) Right Now!",
                color=discord.Color.green()
            )
        )
        for game in games:
            await interaction.followup.send(embed=self._game_embed(game))


async def setup(bot: commands.Bot):
    await bot.add_cog(FreeGames(bot))