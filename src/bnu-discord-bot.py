import sys
#sys.path.append('/app')  # Ensure /app is added to the Python path
from api.discord_bot.bnu_api import bot  # Import the bot instance from bnu_api
from api.discord_bot.bot_config import bot_token
import utilities.logging_config as logging_config

logger = logging_config.setup_logging()

if __name__ == "__main__":
    bot.run(bot_token)
