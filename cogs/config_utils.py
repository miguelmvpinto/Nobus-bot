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
    """Return the config dict for a guild."""
    return load_configs().get(str(guild_id), {})


def is_correct_channel(channel_id: int, config: dict, key: str) -> bool:
    """
    Check whether the current channel is the one configured for a feature.

    Returns True (allow) if:
      - The key doesn't exist yet (not configured → no restriction)
      - The key is None (disabled → no restriction, feature just won't post)
      - The channel matches the configured one

    Returns False (block) only when a channel IS configured and it's a different one.
    """
    if key not in config:
        return True
    val = config[key]
    if val is None:
        return True
    return channel_id == val


def is_feature_enabled(config: dict, key: str) -> bool:
    """
    Returns True if a feature has an active channel configured.
    Returns False if it's missing or explicitly disabled (None).
    """
    val = config.get(key)
    return val is not None


def get_channel_mention(guild: discord.Guild, config: dict, key: str) -> str:
    """Return a channel mention string, or a friendly fallback."""
    val = config.get(key)
    if val is None:
        return "*(feature disabled)*"
    ch = guild.get_channel(val)
    return ch.mention if ch else "*(channel deleted)*"