import urllib.parse
import discord
import logging_config as log
from notification_subscriptions import *
from io import BytesIO
from discord import app_commands
from discord_bot.bot_config import *
from api.kavita_config import *
from kavita_query.kavitaqueries import KavitaQueries
from kavita_query.kavitaactions import KavitaActions
from assets.message_templates.server_status_template import server_status_template
from series_embed import EmbedBuilder
from job_scheduler import ScheduledJobs

# Setup logging
log = log.setup_logging()


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
            # self.tree.copy_global_to(guild=guild)
            await self.tree.sync()
            log.info(f"Successfully synced commands to {guild_id}...")
        except discord.HTTPException as e:
            log.info(f"Failed to sync commands: {e}")

    async def on_ready(self):
        current_commands = await self.tree.fetch_commands()
        log.info(f"Logged in as {self.user} (ID: {self.user.id})")
        log.info(f"Synced commands: {[command.name for command in current_commands]}")
        log.info(
            "---------------------------------------------------------------------------------------------------------")

        # Start the scheduler when the bot is ready
        #self.scheduled_jobs.start_scheduler()

        # List registered scheduled jobs
        # log.info(self.scheduled_jobs.list_jobs())

    async def on_error(self, event, *args, **kwargs):
        log.exception(f"An error occurred: {event}")

    async def on_disconnect(self):
        log.warning(f"bnuAPI ({self.user}) disconnected from server.")
        # await self.reconnect()

    async def on_resumed(self):
        log.info(f"bnuAPI ({self.user}) resumed session.")


    async def close(self):
        log.info("Shutting down...")
        self.scheduled_jobs.stop_scheduler()  # Stop the scheduler when closing
        await super().close()


intents = discord.Intents.default()
bot = bnuAPI()
# Source the series embed function
embed_builder = EmbedBuilder(server_address=kavita_base_url, kavita_queries=bot.kavita_queries)


@bot.tree.command()
# @app_commands.describe(description="List server stats and popular series")
async def mangastats(interaction: discord.Interaction):
    # Acknowledge the interaction to prevent it from timing out, so we can gather data to respond with
    await interaction.response.defer()
    log.info(f"User {interaction.user} requests mangastats, querying Kavita server and responding...")

    message = bot.kavita_queries.get_server_stats()
    if message:
        # Format the stats message
        stats_message, most_read = server_status_template(message, interaction)

        # Send the message to the channel
        await interaction.followup.send(stats_message)

        # Create a list to hold the embeds
        embeds = []

        for series in most_read:
            series_id = series['value']['id']
            # Build variables and a clickable url to the server page for the series
            metadata = bot.kavita_queries.get_series_metadata(series_id)
            # Gather series metadata
            embed_result = embed_builder.build_embed(series, metadata, thumbnail=True)
            embeds.append(embed_result)

        # Send all the embeds in one message
        for embed, file in embeds:
            await interaction.followup.send(embed=embed, file=file if file else None)
    else:
        await interaction.followup.send("No server stats available.")


# Return series info when given a series ID
@bot.tree.command(name='seriesinfo')
# @app_commands.describe(description="Return information on a series")
async def get_series(interaction: discord.Interaction, series_id: int):
    await interaction.response.defer()
    log.info(f"User {interaction.user} requests seriesinfo for {series_id}, querying Kavita server and responding...")
    if series_id:
        # Gather metadata
        metadata = bot.kavita_queries.get_series_metadata(series_id)
        series = bot.kavita_queries.get_series_info(series_id)
        series_embed, file = embed_builder.build_embed(series=series, metadata=metadata, thumbnail=False)

        await interaction.followup.send(embed=series_embed, file=file if file else None)
    else:
        await interaction.followup.send_message(f"Invalid series ID {series_id}.")


@bot.tree.command(name='seriescover')
@app_commands.describe(series_id="Find the series cover and display it")
async def get_series_cover(interaction: discord.Interaction, series_id: int):
    await interaction.response.defer()
    log.info(f"User {interaction.user} requests seriescover for series {series_id}, "
             f"querying Kavita server and responding...")
    if series_id:
        series_cover_data = bot.kavita_queries.get_series_cover(series_id)
        if series_cover_data:
            # Create a file-like object from the image data
            cover_image_file = BytesIO(series_cover_data)
            cover_image_file.name = f"series_cover_{series_id}.jpg"

            # Send the image to discord
            await interaction.followup.send(file=discord.File(cover_image_file, filename=cover_image_file.name))
        else:
            await interaction.followup.send(f"No cover image found for {series_id}.")
    else:
        # Remove the calling message
        await interaction.followup.send(f"Unable to locate cover for {series_id}")


@bot.tree.command(name='mangasearch')
@app_commands.describe(search_query="Search for a manga by search term")
async def manga_search(interaction: discord.Interaction, *, search_query: str):
    await interaction.response.defer()
    log.info(f"User {interaction.user} searched for {search_query}, querying Kavita server and responding...")
    # Verify the query is URL safe
    url_safe_query = urllib.parse.quote(search_query)

    # Send the safe query to the Kavita API
    search_results = bot.kavita_queries.search_server(url_safe_query)

    # We may have multiple results, so we need an embed list object
    embeds = []

    if search_results['series']:
        # Limit the results to the first 3 and build the embeds
        for series in search_results['series'][:3]:
            series_id = series['seriesId']
            # Build variables and a clickable url to the server page for the series
            metadata = bot.kavita_queries.get_series_metadata(series_id)
            # Gather series metadata
            embed_result = embed_builder.build_embed(series, metadata, thumbnail=True)
            embeds.append(embed_result)

        # Send all the embeds in one message
        for embed, file in embeds:
            await interaction.followup.send(embed=embed, file=file if file else None)
    else:
        await interaction.followup.send(f"No search results found for `{search_query}`")


@bot.tree.command(name='inviteme')
@app_commands.describe(email="Get an invite to the server! [USAGE: /inviteme address@mail.com]")
async def invite_me(interaction: discord.Interaction, email: str):
    # Prep actions before we respond
    await interaction.response.defer()
    log.info(f"User {interaction.user} requests invite to BNU Kavita server with email address {email}, verifying email"
             f" address, inviting user via email, and responding...")
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


@bot.tree.command(name='server-address')
async def server_address(interaction: discord.Interaction):
    log.info(f"User {interaction.user} requests server URL, building fancy embed and responding with server address "
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
        log.info(f"Random Manga ID: {random_manga_id}")  # Debug print

        if random_manga_id:
            # Gather metadata
            metadata = bot.kavita_queries.get_series_metadata(random_manga_id)
            series = bot.kavita_queries.get_series_info(random_manga_id)

            # Check if metadata and series are valid
            if metadata and series:
                series_embed, file = embed_builder.build_embed(series, metadata)
                await interaction.followup.send(embed=series_embed, file=file if file else None)
            else:
                await interaction.followup.send(f"No information found for series ID {random_manga_id}.")
        else:
            await interaction.followup.send(f"No series IDs found for library {library}.")

    except Exception as e:
        log.error(f"An error occurred: {e}")  # Debug print
        await interaction.followup.send(f"An error occurred while fetching random manga: {e}")


@bot.tree.command(name='notify-me')
@app_commands.describe(series_name="The series name you wish to subscript to.")
async def notify_me(interaction: discord.Interaction, series_name: str):
    user_id = str(interaction.user.id)
    # Source User subscriptions
    user_notify = load_subscriptions()
    if user_id not in user_notify:
        user_notify[user_id] = []

    if series_name not in user_notify[user_id]:
        user_notify[user_id].append(series_name)
        save_subscriptions(user_notify)
        await interaction.response.send_message(f"You have been subscribed to updates for {series_name}.\nTo list "
                                                f"active notifications, use `/list-notifications`", ephemeral=True)
    else:
        await interaction.response.send_message(f"You are already subscribed to {series_name}.\nTo list "
                                                f"active notifications, use `/list-notifications`", ephemeral=True)


@bot.tree.command(name='remove-notification')
@app_commands.describe(series_name="The series name to unsubscribe from, or 'all' to remove all subscriptions.")
async def remove_notification(interaction: discord.Interaction, series_name: str = None):
    user_id = str(interaction.user.id)
    # Source User subscriptions
    user_notify = load_subscriptions()

    if user_id in user_notify:
        if series_name == "all":
            # Remove all subscriptions for the user
            del user_notify[user_id]
            save_subscriptions(user_notify)
            await interaction.response.send_message(
                "You have been unsubscribed from all updates.",
                ephemeral=True
            )
        elif series_name:
            # Remove specific series if it exists
            if series_name in user_notify[user_id]:
                user_notify[user_id].remove(series_name)
                if not user_notify[user_id]:
                    del user_notify[user_id]  # Remove the user if no subscriptions are left
                save_subscriptions(user_notify)
                await interaction.response.send_message(
                    f"You have been unsubscribed from updates for {series_name}.",
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


@bot.tree.command(name='list-notifications')
async def list_notifications(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    # Source User subscriptions
    user_notify = load_subscriptions()
    if user_id in user_notify and user_notify[user_id]:
        series_list = "\n".join(user_notify[user_id])
        await interaction.response.send_message(f"You are subscribed to the following series:\n`{series_list}`", ephemeral=True)
    else:
        await interaction.response.send_message("You are not subscribed to any series.", ephemeral=True)


async def send_message_to_channel(message: str):
    try:
        channel = await bot.fetch_channel(default_message_channel)
        if channel:
            await channel.send(message)
        else:
            log.info(f"Channel with ID {default_message_channel} not found.")
    except discord.NotFound:
        log.exception(f"Channel with ID {default_message_channel} does not exist.")
    except discord.Forbidden:
        log.exception(f"Bot does not have permission to access channel with ID {default_message_channel}.")
    except discord.HTTPException as e:
        log.exception(f"An HTTP error occurred: {e}")
