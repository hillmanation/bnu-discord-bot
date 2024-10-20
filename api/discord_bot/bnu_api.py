import asyncio
import os
import requests
from datetime import datetime
import discord
from urllib.parse import urlparse
import utilities.logging_config as logging_config
from utilities.emoji_map import generate_emoji_manga_map as map_emojis
from io import BytesIO
from discord import app_commands
from api.kavita_query.kavita_config import *
from api.discord_bot.bot_config import *
from api.kavita_query.kavitaqueries import KavitaQueries
from api.kavita_query.kavitaactions import KavitaActions
from utilities.series_embed import EmbedBuilder
from utilities.job_scheduler import ScheduledJobs
from utilities.notification_subscriptions import *

# Setup logging
logger = logging_config.setup_logging()


class bnuAPI(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.kavita_queries = KavitaQueries()
        self.kavita_actions = KavitaActions()
        self.kavita_queries.authenticate()
        self.kavita_actions.authenticate()
        self.scheduled_jobs = ScheduledJobs(self)

    async def setup_hook(self):
        # Create a discord.Object for the guild using the guild ID
        guild = discord.Object(id=int(guild_id))

        try:
            # Sync the command tree
            await self.tree.sync()
            self.tree.copy_global_to(guild=guild)
            logger.info(f"Successfully synced commands to {guild_id}...")
        except discord.HTTPException as e:
            logger.info(f"Failed to sync commands: {e}")

    async def on_ready(self):
        # Set the bots' status to "Listening to '/'"
        activity = discord.Activity(type=discord.ActivityType.listening, name="/")
        await bot.change_presence(activity=activity)

        current_commands = await self.tree.fetch_commands()
        command_names = sorted([command.name for command in current_commands])
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")

        # Format the command list with line breaks
        formatted_command_list = format_command_list(first_line_text="Synced Commands: ",
                                                     commands=command_names, max_width=100)

        # Log each line of the formatted command list in its own logger block
        for line in formatted_command_list.splitlines():
            logger.info(f"{line}")

        # Start the scheduler when the bot is ready
        self.scheduled_jobs.start_scheduler()

    async def on_error(self, event, *args, **kwargs):
        logger.exception(f"An error occurred: {event}")

    async def on_disconnect(self):
        logger.warning(f"bnuAPI ({self.user}) disconnected from server.")

    async def on_resumed(self):
        logger.info(f"bnuAPI ({self.user}) resumed session.")

    async def close(self):
        logger.info("Shutting down...")
        self.scheduled_jobs.stop_scheduler()  # Stop the scheduler when closing
        await super().close()


intents = discord.Intents.default()
bot = bnuAPI()
# Source the series embed function
embed_builder = EmbedBuilder(server_address=kavita_base_url, kavita_queries=bot.kavita_queries)
# Create a dictionary for holding reaction message IDs
bot.reaction_messages = {}


# Listen for reaction additions (on the entire bot)
@bot.event
async def on_reaction_add(reaction, user):
    # Ensure the bot doesn't respond to its own reactions
    if user == bot.user:
        return

    # Check if the message that received the reaction is one we are tracking
    if reaction.message.id in bot.reaction_messages:
        emoji_manga_list = bot.reaction_messages[reaction.message.id]

        # Find the corresponding manga for the reacted emoji
        for emoji_symbol, manga_title in emoji_manga_list.items():
            if reaction.emoji == emoji_symbol:
                series_id = bot.kavita_queries.get_id_from_name(manga_title)

                logger.info(
                    f"User {user} requests series info for {manga_title}, series ID {series_id}, "
                    f"querying Kavita server and responding...")
                if series_id:
                    # Gather metadata
                    metadata = bot.kavita_queries.get_series_metadata(series_id)
                    series = bot.kavita_queries.get_series_info(series_id)
                    series_name = bot.kavita_queries.get_name_from_id(series_id)
                    series_embed, file = embed_builder.build_series_embed(series=series, metadata=metadata,
                                                                          thumbnail=False)

                    await reaction.message.channel.send(embed=series_embed, file=file if file else None)
                    embed_builder.cleanup_temp_cover(file.fp.name) if file else None

                    recent_chapters = bot.kavita_queries.get_recent_chapters(series_id)
                    chapter_embeds = bot.kavita_queries.send_recent_chapters_embed(manga_title=series_name,
                                                                                   recent_chapters=recent_chapters)

                    for chapter_embed, file in chapter_embeds:
                        await reaction.message.channel.send(embed=chapter_embed, file=file if file else None)
                        embed_builder.cleanup_temp_cover(file.fp.name) if file else None
                else:
                    await reaction.message.channel.send(f"Invalid series ID {series_id}.")
                break


@bot.tree.command(name='bot-info', description="List all bot commands and their descriptions")
async def bot_info(interaction: discord.Interaction):
    # Create an embed for the command information
    embed = discord.Embed(
        title="Bot Commands",
        description="Here are the available commands you can use with this bot:",
        color=0x4ac694  # Customize the color as needed
    )

    # Dynamically fetch commands and their descriptions
    for command in bot.tree.get_commands():
        command_info = f"`/{command.name}`\n{command.description or ''}"

        # Check for command parameters
        if command.parameters:  # Check if parameters exist
            params_info = []
            for param in command.parameters:
                param_description = param.description or ""
                params_info.append(f"`{param.name}`: {param_description}")

            command_info += "\n**Arguments:**\n" + "\n".join(params_info)

        embed.add_field(name=command_info, value="\u200b", inline=False)

    # Send the embed message to the channel
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name='server-stats', description="List server stats and popular series")
async def server_stats(interaction: discord.Interaction):
    # Acknowledge the interaction to prevent it from timing out, so we can gather data to respond with
    await interaction.response.defer()
    logger.info(f"User {interaction.user} requests server-stats, querying Kavita server and responding...")

    # Get the server stats from function
    stats_message, embeds = bot.kavita_queries.generate_server_stats(interaction=interaction)

    if stats_message and embeds:
        # Send the message to the channel
        await interaction.followup.send(stats_message)

        # Send all the embeds in one message
        for embed, file in embeds:
            await interaction.followup.send(embed=embed, file=file if file else None)
            embed_builder.cleanup_temp_cover(file.fp.name) if file else None
    else:
        await interaction.followup.send("No server stats available.", ephemeral=True)


@bot.tree.command(name='server-health', description="Is the server up?")
async def server_health(interaction: discord.Interaction):
    # Acknowledge the interaction to prevent it from timing out
    await interaction.response.defer()
    logger.info(f"User {interaction.user} requests server-health, querying Kavita API and responding...")

    # Query server health status
    server_health_status = bot.kavita_queries.get_server_health()

    if server_health_status and server_health_status.status_code == 200:
        # Send the message to the channel
        await interaction.followup.send(f"Kavita API and Server are up and healthy!")
        logger.info(f"Server is healthy!")
    else:
        # No response means the server is down
        server_admin = await bot.fetch_user(server_admin_id)

        await interaction.followup.send(f"Kavita API is unresponsive, alerting server owner!")
        await interaction.followup.send(f"{server_admin.mention} the Kavita Instance is unresponsive, please "
                                        f"investigate.")
        logger.info(f"Server is unresponsive. Alerted {server_admin}.")


# Return series info when given a series ID
@bot.tree.command(name='series-info', description="Return information on a series")
@app_commands.describe(series_name="Enter the series to search for [This will only return the top result]",
                       series_id="Enter the series ID (optional")
async def series_info(interaction: discord.Interaction, series_name: str = None, series_id: int = None,
                      verbose: bool = False):
    await interaction.response.defer()
    logger.info(f"User {interaction.user} requests series info for {series_name if series_name else series_id}, "
                f"querying Kavita server and responding...")

    # Find the series ID if only the series_name was given
    if series_name and not series_id:
        # Send the safe query to the Kavita API
        search_results = bot.kavita_queries.search_server(series_name)

        series_id = search_results['series'][0]['seriesId']
    if series_id:
        # Gather metadata
        metadata = bot.kavita_queries.get_series_metadata(series_id)
        series = bot.kavita_queries.get_series_info(series_id=series_id, verbose=verbose)
        series_embed, file = embed_builder.build_series_embed(series=series, metadata=metadata, thumbnail=False)

        await interaction.followup.send(embed=series_embed, file=file if file else None)
        embed_builder.cleanup_temp_cover(file.fp.name) if file else None
    else:
        await interaction.followup.send_message(f"Invalid series ID {series_id}.", ephemeral=True)


@bot.tree.command(name='series-cover', description="Find the series cover and display it")
async def series_cover(interaction: discord.Interaction, series_name: str, series_id: int = None):
    await interaction.response.defer()
    logger.info(f"User {interaction.user} requests series cover for series {series_id}, "
                f"querying Kavita server and responding...")

    cover_image_stream = None  # Initialize to None to check later
    cover_image_path = None  # To track the file path for cleanup

    # Find the series ID if only the series_name was given
    if series_name and not series_id:
        # Send the safe query to the Kavita API
        search_results = bot.kavita_queries.search_server(series_name)

        series_id = search_results['series'][0]['seriesId']
    if series_id:
        try:
            # Fetch series cover data from Kavita server
            series_cover_data = bot.kavita_queries.get_series_cover(series_id)

            if series_cover_data:
                # Create a file-like object from the image data
                cover_image_stream = BytesIO(series_cover_data)
                cover_image_stream.name = f"series_cover_{series_id}.jpg"

                # Save the image to a temporary file so we don't spam the script root directory with pngs
                cover_image_path = cover_image_stream.name
                with open(cover_image_path, 'wb') as f:
                    f.write(series_cover_data)

                # Send the image as a file in response
                await interaction.followup.send(file=discord.File(cover_image_stream, filename=cover_image_stream.name))
            else:
                # If no cover data found, inform the user
                await interaction.followup.send(f"No cover image found for series ID {series_id}.")
        except Exception as e:
            # Log and handle any errors
            logger.error(f"Error fetching cover for series {series_id}: {e}")
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)
        finally:
            # Cleanup: Remove the temporary file if it was created
            if cover_image_path and os.path.exists(cover_image_path):
                os.remove(cover_image_path)
                logger.info(f"Removed temporary file: {cover_image_path}")

            # Ensure the BytesIO stream is properly closed to prevent memory leaks
            if cover_image_stream:
                cover_image_stream.close()
    else:
        # Handle case where no valid series_id was provided
        await interaction.followup.send(f"Unable to locate series, perhaps it's an invalid series ID?: {series_id}.",
                                        ephemeral=True)


# Get the next expected chapter update for the given series
@bot.tree.command(name='next-update', description="Get the next expected chapter update for the given series. "
                                                  "Not all series will have this...")
@app_commands.describe(series_name="Query the search function for a series to find info for.")
async def next_update(interaction: discord.Interaction, series_name: str):
    logger.info(f"User {interaction.user} requests next chapter update for series {series_name}, "
                f"querying Kavita server and responding....")

    # Find the series ID if only the series_name was given
    if series_name:
        # Send the safe query to the Kavita API
        search_results = bot.kavita_queries.search_server(series_name)

        series_id = search_results['series'][0]['seriesId']
        series_name = search_results['series'][0]['name']
    if series_id:
        # Query the server for the next series update
        update = bot.kavita_queries.get_series_next_update(series_id)

        if update and update['expectedDate'] is not None:
            # Truncate the fractional seconds to 6 digits
            iso_date = update['expectedDate'].split('.')
            if len(iso_date) == 2:
                iso_date[1] = iso_date[1][:6]  # Limit to 6 digits for microseconds
                fixed_date = '.'.join(iso_date)
            else:
                fixed_date = update['expectedDate']

            # Parse the date string after adjusting the fraction
            format_date = datetime.fromisoformat(fixed_date.replace("Z", "+00:00"))
            now = datetime.now()
            timespan = now - format_date
            days = timespan.days
            hours, remainder = divmod(timespan.seconds, 3600)
            minutes, _ = divmod(remainder, 60)

            # Format the output
            parts = []
            if days > 0:
                parts.append(f"{days} day{'s' if days != 1 else ''}")
            if hours > 0:
                parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
            if minutes > 0:
                parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

            # Combine parts for the final output
            difference = ", ".join(parts) if parts else "now"
            update_date = format_date.strftime("%B %d, %Y")

            await interaction.response.send_message(f"Next chapter of `{series_name}` expected "
                                                    f"{'in ' if difference != 'now' else ''}{difference} on "
                                                    f"{update_date}.", ephemeral=True)
        else:
            await interaction.response.send_message(f"No current chapter update info is known for `{series_name}`, "
                                                    f"this may indicate that not enough chapter updates have "
                                                    f"been gathered to predict the next one.", ephemeral=True)


@bot.tree.command(name='manga-search')
@app_commands.describe(search_query="Search for a manga by search term")
async def manga_search(interaction: discord.Interaction, *, search_query: str):
    await interaction.response.defer()
    logger.info(f"User {interaction.user} searched for {search_query}, querying Kavita server and responding...")

    # Send the safe query to the Kavita API
    search_results = bot.kavita_queries.search_server(search_query)

    # We may have multiple results, so we need an embed list object
    embeds = []

    if search_results['series']:
        # Limit the results to the first 3 and build the embeds
        for series in search_results['series'][:3]:
            series_id = series['seriesId']
            # Build variables and a clickable url to the server page for the series
            metadata = bot.kavita_queries.get_series_metadata(series_id)
            # Gather series metadata
            embed_result = embed_builder.build_series_embed(series, metadata, thumbnail=True)
            embeds.append(embed_result)

        # Send all the embeds in one message
        for embed, file in embeds:
            await interaction.followup.send(embed=embed, file=file if file else None)
    else:
        await interaction.followup.send(f"No search results found for `{search_query}`", ephemeral=True)


@bot.tree.command(name='recently-updated', description="See recently updated series info")
async def recently_updated(interaction: discord.Interaction):
    # Defer the interaction so we can do background logic
    await interaction.response.defer()
    logger.info(f"User {interaction.user} requests recently updated series list, querying server...")
    updated_series = bot.kavita_queries.get_recently_updated()
    if updated_series:
        logger.info(f"Generating emoji map...")
        # Build a list of the manga titles
        series_names = [series['seriesName'] for series in updated_series if 'seriesName' in series]

        # Generate the emoji mapping using the correct list
        emoji_manga_list = map_emojis(manga_titles=series_names)  # Use the list of series names

        # Create an embed for the response
        embed = discord.Embed(
            title="Recently Updated Series",
            description="React to see series update info:\n\n" + "\n".join(
                f"{emoji_symbol}: {manga}" for emoji_symbol, manga in emoji_manga_list.items()
            ),
            color=0x4ac694  # You can change the color to match your theme
        )
        # Path to thumbnail
        thumb_img_path = 'assets/images/server_icon.png'
        # Use discord.File with the file path directly
        file = discord.File(thumb_img_path, filename='thumbnail.jpg')
        embed.set_thumbnail(url="attachment://thumbnail.jpg")
        embed.set_footer(text=f"\nUse the emoji reacts below to get more info for the selected series:")

        # Send the embed message to the channel
        message = await interaction.followup.send(embed=embed, file=file if file else None)

        # Preload the interactions on the message
        for emoji_symbol in emoji_manga_list.keys():  # Use keys() to get the emoji symbols
            await asyncio.sleep(0.15)
            await message.add_reaction(emoji_symbol)

        # Store the message ID and emoji-manga mapping for this interaction
        bot.reaction_messages[message.id] = emoji_manga_list
    else:
        logger.error(f"Unable to pull recently updated series from Kavita server.")
        await interaction.followup.send("Unable to pull recently updated series from Kavita server.", ephemeral=True)


@bot.tree.command(name='invite-me', description="Get an invite to the server!")
@app_commands.describe(email="address@mail.com")
async def invite_me(interaction: discord.Interaction, email: str):
    # Prep actions before we respond
    await interaction.response.defer()
    logger.info(f"User {interaction.user} requests invite to BNU Kavita server with email address {email}, verifying "
                f"email address, inviting user via email, and responding...")
    # Generate the email invite
    user_invite = bot.kavita_actions.new_user_invite(email)
    if user_invite:
        await interaction.followup.send(f"User {interaction.user.mention} invited to the BNU Manga server!")
        # Respond so only the user can see (To keep the email used private)
        await interaction.followup.send(f"User invite send to `{email}`, you may need to check your junk mail "
                                        f"if it's not in your inbox, happy reading!", ephemeral=True)
    else:
        await interaction.followup.send(f"Unable to generate invite with provided email "
                                        f"`{email}`, please try again...", ephemeral=True)


@bot.tree.command(name='server-address', description="Get a link to the BNU Kavita server!")
async def server_address(interaction: discord.Interaction):
    logger.info(f"User {interaction.user} requests server URL, building fancy embed and responding with server address "
                f"({kavita_base_url})...")
    # Respond to the user with the Server address
    embed, file = embed_builder.create_server_address_embed()
    await interaction.response.send_message(embed=embed, file=file)


@bot.tree.command(name='random-manga')
@app_commands.describe(library="Enter Library name to query from [Manga, IT Books, default is 'Manga']")
async def random_manga(interaction: discord.Interaction, library: str = "Manga"):
    await interaction.response.defer()

    # Try to fetch a random series ID
    try:
        random_manga_id = bot.kavita_queries.get_random_series_id(library)
        logger.info(f"Random Manga ID: {random_manga_id}")  # Debug print

        if random_manga_id:
            # Gather metadata
            metadata = bot.kavita_queries.get_series_metadata(random_manga_id)
            series = bot.kavita_queries.get_series_info(random_manga_id)

            # Check if metadata and series are valid
            if metadata and series:
                series_embed, file = embed_builder.build_series_embed(series, metadata)
                await interaction.followup.send(embed=series_embed, file=file if file else None)
                embed_builder.cleanup_temp_cover(file.fp.name) if file else None
            else:
                await interaction.followup.send(f"No information found for series ID {random_manga_id}.")
        else:
            await interaction.followup.send(f"No series IDs found for library {library}.")

    except Exception as e:
        logger.error(f"An error occurred: {e}")  # Debug print
        await interaction.followup.send(f"An error occurred while fetching random manga: {e}")


@bot.tree.command(name='notify-me', description="Subscribe for notifications of series updates.")
@app_commands.describe(series_name="The series name you wish to subscribe to.")
async def notify_me(interaction: discord.Interaction, series_name: str, series_id: int = None):
    user_id = str(interaction.user.id)
    # Source User subscriptions
    user_notify = load_subscriptions()
    if user_id not in user_notify:
        user_notify[user_id] = []

    # Find the series ID if only the series_name was given
    if series_name and not series_id:
        # Set the proper series name and ID from a series name query
        search_results = bot.kavita_queries.search_server(series_name)

        series_info = search_results['series'][0]

        # Set the proper series name for user confirmation
        series_name = series_info['name']
        series_id = series_info['seriesId']
    elif series_id and not series_name:
        # Set the proper series name from the ID
        series_name = bot.kavita_queries.get_name_from_id(series_id)

    if series_id not in user_notify[user_id]:
        user_notify[user_id].append(series_id)
        save_subscriptions(user_notify)
        await interaction.response.send_message(f"You have been subscribed to updates for `{series_name}`.\n"
                                                f"To list active notifications, use `/list-notifications`",
                                                ephemeral=True)
    else:
        await interaction.response.send_message(f"You are already subscribed to {series_name}.\nTo list "
                                                f"active notifications, use `/list-notifications`", ephemeral=True)


@bot.tree.command(name='remove-notification',
                  description="Remove notifications for updates from a series or all series")
@app_commands.describe(series_name="The series name to unsubscribe from, or 'all' to remove all subscriptions.")
async def remove_notification(interaction: discord.Interaction, series_name: str = None, series_id: int = None):
    user_id = str(interaction.user.id)
    # Source User subscriptions
    user_notify = load_subscriptions()

    # Find the series ID if only the series_name was given
    if series_name and series_name != 'all' and not series_id:
        # Set the proper series name and ID from a series name query
        search_results = bot.kavita_queries.search_server(series_name)

        series_info = search_results['series'][0]

        # Set the proper series name for user confirmation
        series_name = series_info['name']
        series_id = series_info['seriesId']
    # Check the user's subscriptions
    if user_id in user_notify:
        if series_name == "all":
            # Remove all subscriptions for the user
            del user_notify[user_id]
            save_subscriptions(user_notify)
            await interaction.response.send_message(
                "You have been unsubscribed from all updates.",
                ephemeral=True
            )
        elif series_id:
            # Remove specific series if it exists
            if series_id in user_notify[user_id]:
                user_notify[user_id].remove(series_id)
                if not user_notify[user_id]:
                    del user_notify[user_id]  # Remove the user if no subscriptions are left
                save_subscriptions(user_notify)
                await interaction.response.send_message(
                    f"You have been unsubscribed from updates for `{series_name}`.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"You are not subscribed to {series_name}.",
                    ephemeral=True
                )
        else:
            await interaction.response.send_message(
                "Please specify a series name to unsubscribe from, or use 'all' to remove all subscriptions.",
                ephemeral=True
            )
    else:
        await interaction.response.send_message(
            "You have no subscriptions to remove.",
            ephemeral=True
        )


@bot.tree.command(name='list-notifications', description="Display your current notification subscriptions.")
async def list_notifications(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    # Source User subscriptions
    user_notify = load_subscriptions()
    if user_id in user_notify and user_notify[user_id]:
        series_names = []
        for series_id in user_notify[user_id]:
            series_name = bot.kavita_queries.get_name_from_id(series_id)
            if series_name:
                series_names.append(f"{series_name}")
            else:
                series_names.append(f"- Series ID {series_id}, (Name not found)")

        # Format the message
        series_list = "\n".join(series_names)
        # Create the embed
        embed = discord.Embed(
            title="Your BNU Kavita Notification Subscriptions",
            description="Here are the series you're subscribed to:",
            color=0x4ac694  # Kavita favicon color
        )

        # Add the list of series to the embed
        embed.add_field(name="Subscribed Series", value=f"```{series_list}```", inline=False)

        # Use discord.File with the file path directly
        header_img_path = 'assets/images/server_icon.png'
        file = discord.File(header_img_path, filename='header.jpg')
        embed.set_thumbnail(url="attachment://header.jpg")

        embed.add_field(name="*Tip:*", value="Use `/remove-notification` `series_name:` "
                                             "**[series name]** to remove a series from your "
                                             "notifications.")

        # Send the embed as an ephemeral message
        await interaction.response.send_message(embed=embed, file=file, ephemeral=True)

    else:
        # If the user has no subscriptions, send a different embed
        embed = discord.Embed(
            title="No Subscriptions",
            description="You are not subscribed to any series.",
            color=0x4ac694  # Kavita favicon color
        )

        # Use discord.File with the file path directly
        header_img_path = 'assets/images/server_icon.png'
        file = discord.File(header_img_path, filename='header.jpg')
        embed.set_thumbnail(url="attachment://header.jpg")

        await interaction.response.send_message(embed=embed, file=file, ephemeral=True)


@bot.tree.command(name='add-manga', description="Add a manga URL from mangadex to the server to be downloaded nightly"
                                                " @ 2am.")
@app_commands.describe(manga_url="Enter a valid mangadex.org url to the series you wish to add.")
async def add_manga(interaction: discord.Interaction, manga_url: str):
    # Defer the response so the bot can respond to the request
    await interaction.response.defer()
    logger.info(f"User {interaction.user} attempting to add URL {manga_url} to nightly download jobs..")

    # Check the url to ensure it's a valid mangadex url
    parsed_url = urlparse(manga_url)
    url_title = parsed_url.path.strip('/').split('/')[-1]

    if not (parsed_url.scheme in ["http", "https"] and
            parsed_url.netloc == "mangadex.org" and parsed_url.path.startswith("/title/")):
        await interaction.followup.send(f"<@{interaction.user.id}> Invalid Mangadex URL. Please provide a valid URL "
                                        f"and try again.", ephemeral=True)
        logger.warning(f"{manga_url} is an invalid mangadex title URL, advised user to try again...")
        return  # Exit the command if the URL is invalid

    try:
        # Let's check the URL to verify it is reachable
        response = requests.get(manga_url, timeout=10)

        # If the site returns the '200' [success] code, the URL is valid
        if response.status_code == 200:
            logger.info(f"URL title page for {url_title} validated and reachable, "
                        f"adding title to manga downloads staging file...")

            # Attempt to add the manga to the list
            add_attempt = add_manga_to_staging_list(manga_url)
            # Verify the 'manga_staging_list' output directory is valid
            if add_attempt == "Added":
                logger.info(f"Title {url_title} requested by {interaction.user} "
                            f"successfully added!")
                await interaction.followup.send(f"<@{interaction.user.id}> The requested title `{url_title}` has been "
                                                f"added to the nightly downloads queue. The title should be available "
                                                f"within `24` hours!")
                # TODO:^^^Let's plan to update the 'hours' to however long it is until ~8 am local time the next day
                #  (When the download and library updates are completed)
            elif add_attempt == "Exists":
                logger.info(f"Title {url_title} already in staging list.")
                await interaction.followup.send(f"<@{interaction.user.id}> The requested title `{url_title}` is "
                                                f"already staged to be added to the server!")
            else:
                await interaction.followup.send(f"<@{interaction.user.id}> Error: Failed to write to the manga staging "
                                                f"list file.", ephemeral=True)
        else:
            # If the URL verification failed
            logger.warning(f"Unreachable URL requested by {interaction.user}, advising user to try again...")
            await interaction.followup.send(
                f"<@{interaction.user.id}> The provided URL is not accessible. Status code: {response.status_code}\n"
                f"Please verify the URL is valid and that the bot has access to the "
                f"internet.", ephemeral=True)
    except requests.RequestException as e:
        logger.error(f"An error occurred while trying to access the URL: {str(e)}")
        await interaction.followup.send(f"<@{interaction.user.id}> An error occurred while trying to access the URL, "
                                        f"please verify and try again", ephemeral=True)


# Function to check file, ensure the URL is unique, and append it if necessary
def add_manga_to_staging_list(manga_url: str):
    # Check if the directory for the file exists
    file_dir = os.path.dirname(manga_staging_list)
    if not os.path.exists(file_dir):
        logger.info(f"Staging file {file_dir} does not exist. Creating it...")
        os.makedirs(file_dir)  # Create the directory if it doesn't exist

    try:
        # Read the file if it exists to check for duplicates
        if os.path.exists(manga_staging_list):
            with open(manga_staging_list, 'r') as file:
                existing_urls = file.readlines()
                existing_urls = [url.strip() for url in existing_urls]  # Strip newline characters

            if manga_url in existing_urls:
                logger.info(f"The URL {manga_url} is already in the list.")
                return "Exists"  # Return False if the URL is already in the list

        # Open the file in append mode, which will create the file if it doesn't exist
        with open(manga_staging_list, 'a') as file:
            file.write(f"{manga_url}\n")  # Append the manga URL to the file

        return "Added"  # Return True if writing was successful
    except IOError as e:
        logger.error(f"Failed to write to the file: {e}")
        return False


async def send_message_to_channel(message: str):
    try:
        channel = await bot.fetch_channel(default_message_channel)
        if channel:
            await channel.send(message)
        else:
            logger.info(f"Channel with ID {default_message_channel} not found.")
    except discord.NotFound:
        logger.exception(f"Channel with ID {default_message_channel} does not exist.")
    except discord.Forbidden:
        logger.exception(f"Bot does not have permission to access channel with ID {default_message_channel}.")
    except discord.HTTPException as e:
        logger.exception(f"An HTTP error occurred: {e}")


def format_command_list(commands, first_line_text=None, max_width=100):
    """
    Formats the list of commands to ensure the output does not exceed the max_width per line.

    :param commands: List of command names.
    :param first_line_text: The text that will appear at the start of the first line
    :param max_width: Maximum number of characters allowed per line.
    :return: A string where commands are split into lines respecting max_width.
    """
    formatted_commands = ""
    current_line = first_line_text.strip() + " " if first_line_text else ""  # Start with the first line text

    for command in commands:
        # Check if adding the command exceeds the max width
        if len(current_line) + len(command) + (2 if current_line else 0) > max_width:
            # Add the current line to the formatted string
            formatted_commands += current_line.strip() + ",\n"
            current_line = ""  # Reset for the next line

        # Add command to the current line
        if current_line and current_line.strip() != first_line_text.strip():
            current_line += ", "
        current_line += command

    # Add any remaining commands in the last line without trailing comma
    if current_line:
        formatted_commands += current_line.strip()

    # Generate line break based on the length of the longest line in formatted_commands
    longest_line_length = max(len(line) for line in formatted_commands.splitlines())
    line_break = '-' * longest_line_length  # Use the length of the longest line
    formatted_commands += f"\n{line_break}"

    return formatted_commands
