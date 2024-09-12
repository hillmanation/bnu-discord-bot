from api.kavita_api import KavitaAPI
from discord_bot.bnu_command_listener import BNUCommandListener
from discord_bot.bot_config import guild_id, default_message_channel, bot_token
import asyncio
import discord
from discord.ext import commands
from discord import app_commands


async def setup_bot():
    # Login to the Kavita API
    kAPI = KavitaAPI('http://hillnet.jaykillmanstudios.com:23566/api/opds/0d49f655-ddee-40d0-9412-eb7433362352')

    if kAPI.authenticate():
        server_stats = kAPI.get_server_stats()
        if server_stats:
            print(server_stats)
            test = "Passed"

        else:
            print("Failed to retrieve server stats.")
            return
    else:
        print("Authentication failed.")
        return

    intents = discord.Intents.default()
    intents.message_content = True  # Ensure message content intent is enabled

    bot = commands.Bot(command_prefix='/', intents=intents)

    # Add cog asynch
    await bot.add_cog(BNUCommandListener(bot, guild_id=guild_id, log_channel_id=default_message_channel,
                                         message=server_stats))
    # Run the bot
    await bot.start(bot_token)


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_bot())


if __name__ == "__main__":
    main()
