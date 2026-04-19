import json
import os
import discord

CONFIG_FILE = "server_configs.json"

def load_configs() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def get_server_config(guild_id: int) -> dict:
    """Retorna o dicionário de config para um servidor."""
    configs = load_configs()
    return configs.get(str(guild_id), {})

def is_correct_channel(channel_id: int, config: dict, key: str) -> bool:
    """
    Verifica se o canal atual é o canal configurado para aquela função.
    Se não houver canal configurado, deixa passar (retorna True).
    """
    configured = config.get(key)
    if configured is None:
        return True
    return channel_id == configured

def get_channel_mention(guild: discord.Guild, config: dict, key: str) -> str:
    """Retorna o mention do canal configurado, ou uma mensagem de aviso."""
    cid = config.get(key)
    if cid is None:
        return "*(canal não configurado)*"
    ch = guild.get_channel(cid)
    return ch.mention if ch else "*(canal removido)*"