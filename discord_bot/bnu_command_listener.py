import discord
from discord.ext import commands
from discord import app_commands
from bot_config import bot_token, default_message_channel, guild_id
from assets.message_templates.server_status_template import server_status_template


class BNUCommandListener(commands.Cog):
    def __init__(self, bot: commands.Bot, guild_id: int, log_channel_id: int, message=None):
        self.bot = bot
        self.guild_id = guild_id
        self.log_channel_id = log_channel_id
        self.message = message

    async def setup_hook(self):
        # Set bot activity/presence
        activity = discord.Activity(name=" '/mangastats'...", type=discord.ActivityType.watching)
        await self.bot.change_presence(activity=activity)

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'Logged in as {self.bot.user}')

    @commands.command(name='mangastats')
    async def serverstats(self, ctx):
        if self.message:
            # Format the stats message
            stats_message = server_status_template(self.message)
            # Send the message to the channel
            await ctx.send(stats_message)
        else:
            await ctx.send("No server stats available.")

    async def send_message_to_channel(self, message: str):
        try:
            channel = await self.bot.fetch_channel(self.log_channel_id)
            if channel:
                await channel.send(message)
            else:
                print(f"Channel with ID {self.log_channel_id} not found.")
        except discord.NotFound:
            print(f"Channel with ID {self.log_channel_id} does not exist.")
        except discord.Forbidden:
            print(f"Bot does not have permission to access channel with ID {self.log_channel_id}.")
        except discord.HTTPException as e:
            print(f"An HTTP error occurred: {e}")
