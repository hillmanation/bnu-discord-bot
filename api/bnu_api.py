import discord
from discord.ext import commands
from discord_bot.bot_config import *
from discord_bot.bnu_command_listener import BNUCommandListener


class bnuAPI:
    def __init__(self, server_stats=None):
        # Initialize intents for the bot
        self.intents = discord.Intents.all()
        self.intents.message_content = True  # Ensure message content intent is enabled
        # Initialize bot with command prefix and intents
        self.bot = commands.Bot(command_prefix='/', intents=self.intents)
        # Pass server_stats for the `BNUCommandListener` cog
        self.server_stats = server_stats

    async def authenticate(self):
        # Add the command listener cog with server stats passed
        await self.bot.add_cog(BNUCommandListener(self.bot, guild_id=guild_id, log_channel_id=default_message_channel))

        @self.bot.event
        async def setup_hook():
            print(f"Logged in as {self.bot.user}")
            activity = discord.Activity(name=" '/mangastats'...", type=discord.ActivityType.watching)
            await self.bot.change_presence(activity=activity)

            # Sync commands
            try:
                await self.bot.tree.sync()  # (guild=discord.Object(id=guild_id))  # Sync commands to a specific guild
                print(f"Synced slash commands with the guild {guild_id}")
            except Exception as e:
                print(f"Failed to sync commands: {e}")

        # Run the bot
        await self.bot.start(bot_token)
        return self.bot

    def get_bot(self):
        # Return bot object
        return self.bot
