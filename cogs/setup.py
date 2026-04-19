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

class ChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, config_key: str, label: str):
        super().__init__(
            placeholder=f"Escolhe o canal para {label}...",
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
            custom_id=f"select_{config_key}"
        )
        self.config_key = config_key
        self.label_name = label

    async def callback(self, interaction: discord.Interaction):
        channel = self.values[0]
        set_server_config(interaction.guild.id, self.config_key, channel.id)

        embed = discord.Embed(
            title="✅ Canal configurado!",
            description=f"**{self.label_name}** → {channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # Atualiza o embed principal com o progresso
        await self.view.update_main_embed(interaction)


class ChannelSelectView(discord.ui.View):
    def __init__(self, guild: discord.Guild, original_interaction: discord.Interaction):
        super().__init__(timeout=300)
        self.guild = guild
        self.original_interaction = original_interaction

        self.music_select = ChannelSelect("music_channel", "🎵 Música")
        self.bot_select = ChannelSelect("bot_channel", "🤖 Comandos / Bot")
        self.welcome_select = ChannelSelect("welcome_channel", "👋 Boas-vindas")

        self.add_item(self.music_select)
        self.add_item(self.bot_select)
        self.add_item(self.welcome_select)

    def build_embed(self) -> discord.Embed:
        config = get_server_config(self.guild.id)

        def channel_mention(key):
            cid = config.get(key)
            if cid:
                ch = self.guild.get_channel(cid)
                return ch.mention if ch else "⚠️ Canal removido"
            return "❌ Não configurado"

        embed = discord.Embed(
            title="⚙️ Setup do Nobus Bot",
            description=(
                "Usa os menus abaixo para configurar os canais do servidor.\n"
                "Só administradores podem fazer isto.\n\u200b"
            ),
            color=discord.Color.blurple()
        )
        embed.add_field(name="🎵 Canal de Música", value=channel_mention("music_channel"), inline=True)
        embed.add_field(name="🤖 Canal de Comandos", value=channel_mention("bot_channel"), inline=True)
        embed.add_field(name="👋 Canal de Boas-vindas", value=channel_mention("welcome_channel"), inline=True)
        embed.set_footer(text="Nobus Bot Setup • Configurações guardadas automaticamente")
        return embed

    async def update_main_embed(self, interaction: discord.Interaction):
        try:
            await self.original_interaction.edit_original_response(embed=self.build_embed(), view=self)
        except Exception:
            pass

    @discord.ui.button(label="✅ Concluir Setup", style=discord.ButtonStyle.success, row=3)
    async def finish_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = get_server_config(self.guild.id)
        missing = []
        if not config.get("music_channel"):
            missing.append("🎵 Música")
        if not config.get("bot_channel"):
            missing.append("🤖 Comandos / Bot")
        if not config.get("welcome_channel"):
            missing.append("👋 Boas-vindas")

        if missing:
            embed = discord.Embed(
                title="⚠️ Setup incompleto",
                description="Ainda faltam configurar:\n" + "\n".join(f"• {m}" for m in missing),
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Desativa todos os selects
        for item in self.children:
            item.disabled = True
        button.label = "✅ Setup Concluído"

        final_embed = self.build_embed()
        final_embed.color = discord.Color.green()
        final_embed.title = "✅ Setup Concluído!"
        final_embed.description = "Todas as configurações foram guardadas com sucesso!"

        await interaction.response.edit_message(embed=final_embed, view=self)

    @discord.ui.button(label="🔄 Reset Config", style=discord.ButtonStyle.danger, row=3)
    async def reset_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        configs = load_configs()
        guild_key = str(self.guild.id)
        if guild_key in configs:
            del configs[guild_key]
            save_configs(configs)

        embed = discord.Embed(
            title="🔄 Configurações resetadas",
            description="Todas as configurações deste servidor foram apagadas.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await self.update_main_embed(interaction)

class Setup(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup", description="Configura os canais do bot para este servidor.")
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        """Comando de setup interativo - só admins"""
        view = ChannelSelectView(interaction.guild, interaction)
        embed = view.build_embed()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="config", description="Mostra a configuração atual do bot neste servidor.")
    @app_commands.default_permissions(administrator=True)
    async def config_show(self, interaction: discord.Interaction):
        """Mostra a config atual do servidor"""
        config = get_server_config(interaction.guild.id)

        def channel_mention(key):
            cid = config.get(key)
            if cid:
                ch = interaction.guild.get_channel(cid)
                return ch.mention if ch else "⚠️ Canal removido"
            return "❌ Não configurado"

        embed = discord.Embed(
            title="📋 Configuração atual",
            color=discord.Color.blurple()
        )
        embed.add_field(name="🎵 Música", value=channel_mention("music_channel"), inline=True)
        embed.add_field(name="🤖 Comandos / Bot", value=channel_mention("bot_channel"), inline=True)
        embed.add_field(name="👋 Boas-vindas", value=channel_mention("welcome_channel"), inline=True)
        embed.set_footer(text="Usa /setup para alterar as configurações")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Quando o bot entra num novo servidor, envia setup automático"""
        target_channel = guild.system_channel
        if target_channel is None:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).send_messages:
                    target_channel = channel
                    break

        if target_channel is None:
            return

        embed = discord.Embed(
            title="👋 Olá! Sou o Nobus Bot!",
            description=(
                "Obrigado por me adicionar ao servidor!\n\n"
                "Para começar, um **administrador** deve correr o comando:\n"
                "```/setup```\n"
                "Isto vai configurar os canais para música, comandos e boas-vindas."
            ),
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Nobus Bot • Usa /setup para configurar")

        try:
            await target_channel.send(embed=embed)
        except discord.Forbidden:
            pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Setup(bot))