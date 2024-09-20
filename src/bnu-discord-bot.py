from api.discord_bot.bnu_api import bot  # Import the bot instance from bnu_api
from api.discord_bot.bot_config import bot_token

if __name__ == "__main__":
    bot.run(bot_token)
