# 🤖 Nobus Bot

A Discord bot developed in Python with support for both slash commands and prefix commands, organized using a modular Cog system.

---

## ✨ Features

- ⚡ Slash Commands (/commands)
- 🧩 Modular Cogs System (plug & play commands)
- 🛡️ Global Error Handling
- 🔧 Easy configuration with .env
- ☁️ Ready for deployment (Railway + Nixpacks)

---

## 📁 Estrutura do Projeto

```
Nobus-bot/
├── cogs/               # Modules containing bot commands
├── main.py             # Bot entry point
├── requirements.txt    # Python dependencies
├── nixpacks.toml       # Build configuration (Railway)
├── procfile            # Start command
└── runtime.txt         # Python version
```

---

## ⚙️ Setup

### Prerequisites

- Python 3.10+
- A [Discord Developer Portal](https://discord.com/developers/applications)
- A Discord bot token

### Installation

1. Clone the repository:

```bash
git clone https://github.com/miguelmvpinto/Nobus-bot.git
cd Nobus-bot
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a .env file in the project root:

```env
DISCORD_TOKEN=your_token_here
```

4. Run the bot:

```bash
python main.py
```

---

## 🚀 Deployment

The project is configured for direct deployment on Railway using nixpacks.toml and procfile. Simply connect the repository to Railway and set the DISCORD_TOKEN environment variable.

---

## 🛠️ Adding New Commands

Create a new .py file inside the cogs/ folder. The bot automatically loads all Cogs on startup.

Example Cog structure:

```python
from discord.ext import commands
import discord

class MeuCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.app_commands.command(name="ola", description="Diz olá!")
    async def ola(self, interaction: discord.Interaction):
        await interaction.response.send_message("Olá! 👋")

async def setup(bot):
    await bot.add_cog(MeuCog(bot))
```

---

## 📦 Dependencies

Check the [`requirements.txt`](requirements.txt) file for the full list. Main ones include:

- [`discord.py`](https://discordpy.readthedocs.io/) — main library
- [`python-dotenv`](https://pypi.org/project/python-dotenv/) — environment variable management

---

## 📌 Roadmap

- Add database support
- Add moderation commands
- Add economy system
- Web dashboard

---

## 🤝 Contributing

Pull requests are welcome!
If you have ideas, feel free to open an issue.

---

## 📄 License

This project does not have a defined license. Intended for personal and educational use.

---

> Developed by [miguelmvpinto](https://github.com/miguelmvpinto)
