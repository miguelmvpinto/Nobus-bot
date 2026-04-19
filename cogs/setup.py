import discord
from discord.ext import commands
from discord import app_commands
import json
import os

CONFIG_FILE = "server_configs.json"

def load_configs() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_configs(data: dict):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_server_config(guild_id: int) -> dict:
    configs = load_configs()
    return configs.get(str(guild_id), {})

def set_server_config(guild_id: int, key: str, value):
    configs = load_configs()
    guild_key = str(guild_id)
    if guild_key not in configs:
        configs[guild_key] = {}
    configs[guild_key][key] = value
    save_configs(configs)

def skip_server_config(guild_id: int, key: str):
    """Explicitly mark a feature as disabled (None = skipped)."""
    configs = load_configs()
    guild_key = str(guild_id)
    if guild_key not in configs:
        configs[guild_key] = {}
    configs[guild_key][key] = None
    save_configs(configs)

CHANNELS = [
    ("music_channel",     "🎵", "Music",      "Channel where music commands (/play, /skip, etc.) will work."),
    ("bot_channel",       "🤖", "Commands",   "Channel where general bot commands (/help, /clear, etc.) will work."),
    ("welcome_channel",   "👋", "Welcome",    "Channel where join/leave messages are sent automatically."),
    ("freegames_channel", "🎮", "Free Games", "Channel where free game alerts (Epic & Steam) are posted every 6 hours."),
]

class StepView(discord.ui.View):
    def __init__(self, wizard: "SetupWizard", key: str, emoji: str, label: str):
        super().__init__(timeout=180)
        self.wizard = wizard
        self.key    = key

        select = discord.ui.ChannelSelect(
            placeholder=f"Select the {label} channel...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
        )
        select.callback = self._select_callback
        self.add_item(select)

    async def _select_callback(self, interaction: discord.Interaction):
        channel_id = int(interaction.data["values"][0])
        ch = interaction.guild.get_channel(channel_id)
        set_server_config(interaction.guild.id, self.key, channel_id)
        self.wizard.results[self.key] = ch.mention if ch else f"<#{channel_id}>"
        await interaction.response.defer()
        await self.wizard.advance()

    @discord.ui.button(label="⏭️ Skip — disable this feature", style=discord.ButtonStyle.secondary, row=1)
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        skip_server_config(interaction.guild.id, self.key)
        self.wizard.results[self.key] = "⏭️ Disabled"
        await interaction.response.defer()
        await self.wizard.advance()

class SetupWizard:
    def __init__(self, interaction: discord.Interaction):
        self.interaction = interaction
        self.guild       = interaction.guild
        self.step        = 0
        self.results: dict[str, str] = {}

    def _step_embed(self) -> discord.Embed:
        key, emoji, label, desc = CHANNELS[self.step]
        total = len(CHANNELS)

        filled = "█" * (self.step + 1)
        empty  = "░" * (total - self.step - 1)

        embed = discord.Embed(
            title=f"⚙️ Server Setup  —  Step {self.step + 1} of {total}",
            description=f"**{emoji} {label} Channel**\n{desc}\n\nPick a channel or click **Skip** to disable this feature.",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Progress", value=f"`{filled}{empty}` {self.step + 1}/{total}", inline=False)

        if self.results:
            lines = [f"{e} **{l}:** {self.results[k]}"
                     for k, e, l, _ in CHANNELS if k in self.results]
            embed.add_field(name="Configured so far", value="\n".join(lines), inline=False)

        embed.set_footer(text="Nobus Bot Setup • Admins only")
        return embed

    def _summary_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="✅ Setup Complete!",
            description="All settings have been saved. Here's a summary:",
            color=discord.Color.green()
        )
        for key, emoji, label, _ in CHANNELS:
            embed.add_field(name=f"{emoji} {label}", value=self.results.get(key, "⏭️ Disabled"), inline=True)
        embed.set_footer(text="Use /setup to reconfigure • /config to view • /resetconfig to clear")
        return embed

    async def start(self):
        key, emoji, label, _ = CHANNELS[0]
        view = StepView(self, key, emoji, label)
        await self.interaction.response.send_message(
            embed=self._step_embed(), view=view, ephemeral=True
        )

    async def advance(self):
        self.step += 1
        if self.step >= len(CHANNELS):
            await self.interaction.edit_original_response(embed=self._summary_embed(), view=None)
            return
        key, emoji, label, _ = CHANNELS[self.step]
        view = StepView(self, key, emoji, label)
        await self.interaction.edit_original_response(embed=self._step_embed(), view=view)

class ResetConfirmView(discord.ui.View):
    def __init__(self, guild_id: int):
        super().__init__(timeout=30)
        self.guild_id = guild_id

    @discord.ui.button(label="Yes, reset everything", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        configs = load_configs()
        configs.pop(str(self.guild_id), None)
        save_configs(configs)
        for item in self.children:
            item.disabled = True
        embed = discord.Embed(
            title="🔄 Config Reset",
            description="All settings have been cleared.\nRun `/setup` to configure again.",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        embed = discord.Embed(description="❌ Reset cancelled.", color=discord.Color.blurple())
        await interaction.response.edit_message(embed=embed, view=self)

class Setup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Configure the bot channels for this server (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def setup_cmd(self, interaction: discord.Interaction):
        wizard = SetupWizard(interaction)
        await wizard.start()

    @app_commands.command(name="config", description="Show the current bot configuration")
    @app_commands.default_permissions(administrator=True)
    async def config_show(self, interaction: discord.Interaction):
        config = get_server_config(interaction.guild.id)

        def fmt(key):
            if key not in config:
                return "❌ Not set"
            val = config[key]
            if val is None:
                return "⏭️ Disabled"
            ch = interaction.guild.get_channel(val)
            return ch.mention if ch else "⚠️ Channel deleted"

        embed = discord.Embed(title="📋 Current Configuration", color=discord.Color.blurple())
        for key, emoji, label, _ in CHANNELS:
            embed.add_field(name=f"{emoji} {label}", value=fmt(key), inline=True)
        embed.set_footer(text="Use /setup to change settings")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="resetconfig", description="Clear all bot configuration for this server (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def reset_config(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚠️ Reset Configuration",
            description="Are you sure you want to clear **all** bot settings for this server?\nThis cannot be undone.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, view=ResetConfirmView(interaction.guild.id), ephemeral=True)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        target = guild.system_channel
        if target is None:
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    target = ch
                    break
        if target is None:
            return

        embed = discord.Embed(
            title="👋 Hey! I'm Nobus Bot!",
            description=(
                "Thanks for adding me to your server!\n\n"
                "To get started, an **administrator** should run:\n"
                "```/setup```\n"
                "This will configure the channels for music, commands, welcome messages, and free game alerts."
            ),
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Nobus Bot • Run /setup to configure")
        try:
            await target.send(embed=embed)
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Setup(bot))