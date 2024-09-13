import urllib.parse
import discord
from discord.ext import commands
from discord import app_commands
from discord_bot.bot_config import *
from api.kavita_config import *
from io import BytesIO
from kavita_query.kavitaqueries import KavitaQueries
from kavita_query.kavitaactions import KavitaActions
from assets.message_templates.server_status_template import server_status_template


class BNUCommandListener(commands.Cog):
    def __init__(self, bot: commands.Bot, guild_id: int, log_channel_id: int):
        self.bot = bot
        self.guild_id = guild_id
        self.log_channel_id = log_channel_id
        self.kavita_queries = KavitaQueries()  # Source the Kavita server queries
        self.kavita_actions = KavitaActions()  # Source the Kavita server actions
        self.kavita_queries.authenticate()  # Authenticate to the Kavita server
        self.kavita_actions.authenticate()  # Authenticate to the Kavita server

    # Respond with current server stats
    @app_commands.command(name='mangastats', description="List server stats and popular series")
    async def serverstats(self, interaction: discord.Interaction):
        message = self.kavita_queries.get_server_stats()
        if message:
            # Format the stats message
            stats_message, most_read = server_status_template(message, interaction)

            # Delete the user message this command is responding to
            await interaction.message.delete()

            # Send the message to the channel
            await interaction.response.send_message(stats_message)

            # Create a list to hold the embeds
            embeds = []

            for series in most_read:
                # Build variables and a clickable url to the server page for the series
                series_id = series['value']['id']
                series_name = series['value']['name']
                series_library = series['value']['libraryId']
                server_address = "http://hillnet.jaykillmanstudios.com:23566"  # Replace with actual server address
                series_url = f"{server_address}/library/{series_library}/series/{series_id}"

                # Gather series metadata
                metadata = self.kavita_queries.get_series_metadata(series_id)

                # Build the description field
                description = (f"\n\n**Author**:\n- {metadata['writers'][0]['name']}"
                               f"\n**Summary**:\n{metadata['summary']}\n[**Read here**]({series_url})")

                # Build an embed for the series
                embed = discord.Embed(
                    title=f"{series_name}",
                    description=description if description else None,
                    color=0x4ac694  # Kavita favicon color
                )
                # Attempt to pull cover data
                series_cover_data = self.kavita_queries.get_series_cover(series_id)
                if series_cover_data:
                    # Create a file-like object from the image data and add it to the embed
                    cover_image_file = BytesIO(series_cover_data)
                    cover_image_file.name = f"series_cover_{series_id}.jpg"
                    # Send the image as an attachment
                    image_url = f"attachment://{cover_image_file.name}"
                    embed.set_image(url=image_url)

                    # Add the embed to the list
                    embeds.append((embed, discord.File(cover_image_file, filename=cover_image_file.name)))
                else:
                    # Add the embed to the list without the image
                    embeds.append((embed,))

            # Send all the embeds in one message
            for embed, file in embeds:
                await interaction.response.send_message(embed=embed, file=file if file else None)
        else:
            # Delete the user message this command is responding to
            await interaction.message.delete()
            await interaction.response.send_message("No server stats available.")

    # Return series info when given a series ID
    @app_commands.command(name='seriesinfo', description="Return information on a series")
    async def get_series(self, interaction: discord.Interaction, series_id: int):
        if id:
            series_info = self.kavita_queries.get_series_info(series_id)

            await interaction.message.delete()

            print(f"{series_info}")

    @app_commands.command(name='seriescover', description="Find the series cover and display it")
    async def get_series_cover(self, interaction: discord.Interaction, series_id: int):
        if series_id:
            # Remove the calling message
            await interaction.message.delete()
            series_cover_data = self.kavita_queries.get_series_cover(series_id)
            if series_cover_data:
                # Create a file-like object from the image data
                cover_image_file = BytesIO(series_cover_data)
                cover_image_file.name = f"series_cover_{series_id}.jpg"

                # Send the image to discord
                await interaction.send_message(file=discord.File(cover_image_file, filename=cover_image_file.name))
            else:
                await interaction.response.send_message(f"No cover image found for {series_id}.")
        else:
            # Remove the calling message
            await interaction.message.delete()
            await interaction.response.send_message(f"Unable to locate cover for {series_id}")

    @app_commands.command(name='mangasearch', description="Search for a manga by search term")
    async def manga_search(self, interaction: discord.Interaction, *, search_query: str):
        # Verify the query is URL safe
        url_safe_query = urllib.parse.quote(search_query)

        # Send the safe query to the Kavita API
        search_results = self.kavita_queries.search_server(url_safe_query)

        if search_results['series']:
            print(search_results)
        else:
            await interaction.response.send_message(f"No search results found for [{search_query}]")

    @app_commands.command(name='inviteme', description="Get an invite to the server! "
                                                       "[USAGE: /inviteme address@mail.com]")
    async def invite_me(self, interaction: discord.Interaction, email_addr: str):
        # Clear the calling message
        await interaction.message.delete()
        # Generate the email invite
        user_invite = self.kavita_actions.new_user_invite(email_addr)
        if user_invite:
            await interaction.response.send_message(f"User invite send to `{email_addr}`")
        else:
            await interaction.response.send_message(f"Unable to generate invite with provided email "
                                                    f"`{email_addr}`, please try again...")

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
