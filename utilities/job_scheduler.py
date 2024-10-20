import json
import asyncio
import discord
import utilities.logging_config as logging_config
from api.kavita_query.kavita_config import kavita_base_url
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_MISSED
from kavita_config import server_admin_id
from utilities.series_embed import EmbedBuilder
from utilities.emoji_map import generate_emoji_manga_map as map_emojis

# Setup logging
logger = logging_config.setup_logging()


class ScheduledJobs:
    def __init__(self, bot):
        self.scheduler = BackgroundScheduler({
            'job_defaults': {
                'misfire_grace_time': None,  # Set default misfire grace period for all jobs
                'coalesce': True,  # Combine missed runs
                'max_instances': 3  # Max instances of the same job running at the same time
            }
        })
        self.bot = bot
        self.embed_builder = EmbedBuilder(server_address=kavita_base_url, kavita_queries=self.bot.kavita_queries)
        self.load_jobs_from_json()
        logger.info("Job scheduler initialized.")

    def load_jobs_from_json(self):
        # Load job config from file
        try:
            with open('assets/subscriptions/scheduled_jobs.json', 'r') as file:
                jobs = json.load(file)['jobs']
                for job in jobs:
                    self.add_job(job)
        except Exception as e:
            logger.error(f"Failed to load jobs from JSON: {e}")

    def load_subscriptions(self, file_path='assets/subscriptions/subscriptions.json'):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                if not all(isinstance(v, list) for v in data.values()):
                    logger.error(f"Data in subscriptions file is not as expected. Data: {data}")
                    return {}
                return data
        except Exception as e:
            logger.error(f"Failed to load subscriptions file: {e}")
            return {}

    def job_function(self, job):
        job_type = job['type']
        if job_type == 'send_message':
            asyncio.run_coroutine_threadsafe(self.send_message_action(job), self.bot.loop)
        elif job_type == 'command':
            asyncio.run_coroutine_threadsafe(self.run_command_action(job), self.bot.loop)
        else:
            logger.warning(f"Unknown job type: {job_type}")

    async def send_message_action(self, job):
        channel = self.bot.get_channel(job['channel_id'])
        if channel:
            message = job['message']
            await channel.send(message)
            logger.info(f"Sent message to channel {job['channel_id']}: {message}")
        else:
            logger.error(f"Channel with ID {job['channel_id']} not found.")

    async def run_command_action(self, job):
        command_name = job['command_name']
        channel_id = job['channel_id']
        channel = self.bot.get_channel(channel_id)
        if not channel:
            logger.error(f"Channel with ID {channel_id} not found.")
            return

        if command_name == "server-stats":
            logger.info(f"[Scheduled Job] Sending daily server stats to {channel_id}.")
            try:
                # Get the server stats directly
                stats_message, embeds = self.bot.kavita_queries.generate_server_stats(daily_update=True)

                if stats_message and embeds:
                    # Send the message to the channel
                    await channel.send(stats_message)

                    # Fetch recently updated series
                    updated_series = self.bot.kavita_queries.get_recently_updated()
                    if updated_series:
                        logger.info(f"[Scheduled Job] Generating emoji map for recently updated series...")
                        series_names = [series['seriesName'] for series in updated_series if 'seriesName' in series]
                        emoji_manga_list = map_emojis(manga_titles=series_names, max_titles=10)

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

                        # Send the emoji message
                        emoji_message_obj = await channel.send(embed=embed, file=file if file else None)

                        for emoji_symbol in emoji_manga_list.keys():
                            await asyncio.sleep(0.15)
                            await emoji_message_obj.add_reaction(emoji_symbol)
                        # Store the mapping of emojis to the message ID for tracking
                        self.bot.reaction_messages[emoji_message_obj.id] = emoji_manga_list
                    else:
                        await channel.send("No recently updated series available.")
                else:
                    await channel.send("No server stats available.")
            except Exception as e:
                logger.error(f"Failed to execute command '{command_name}': {e}")
        elif command_name == "user_notifications":
            await self.check_user_subscriptions()
        elif command_name == "server_health_check":
            logger.info(f"[Scheduled Job] Checking Kavita API/Server health status...")
            server_status = await self.server_health_check()
            # If server_status is false we need to alert an admin
            if not server_status:
                # No response means the server is down
                server_admin = await self.bot.fetch_user(server_admin_id)
                logger.warning(
                    f"[Scheduled Job] Kavita server did not respond to Health request, informing server admin!")
                await channel.send(f"{server_admin.mention} the Kavita instance is unresponsive, please investigate.")
            else:
                # Confirm in the console that the server is up
                logger.info(f"[Scheduled Job] Kavita Server is healthy!")
        else:
            logger.error(f"[Scheduled Job] Command '{command_name}' not found in bot.")

    def add_job(self, job):
        # Build a flexible CronTrigger based on the provided job parameters
        cron_kwargs = {}

        if job['enabled'] == "True":
            # Check for specific time scheduling (hour, minute, second)
            if 'hour' in job:
                cron_kwargs['hour'] = job['hour']
            if 'minute' in job:
                cron_kwargs['minute'] = job['minute']
            if 'second' in job:
                cron_kwargs['second'] = job['second']

            # Check for day-specific scheduling
            if 'day_of_week' in job:
                cron_kwargs['day_of_week'] = job['day_of_week']  # E.g., 'mon', 'tue', '5' (for Friday)

            if 'day_of_month' in job:
                cron_kwargs['day'] = job['day_of_month']  # E.g., 1-31 (for the 1st to 31st day of the month)

            # Check for month-specific scheduling
            if 'month' in job:
                cron_kwargs['month'] = job['month']  # E.g., 1-12 (for January to December)

            # If cron_kwargs is empty, it means no valid scheduling was provided
            if not cron_kwargs:
                logger.error(f"No valid scheduling parameters for job '{job['id']}'. Job not added.")
                return

            # Define the job using the CronTrigger with the constructed cron_kwargs
            self.scheduler.add_job(
                self.job_function,
                CronTrigger(**cron_kwargs),
                args=[job],
                id=job['id']
            )

            logger.info(f"Job '{job['id']}' added with schedule: {cron_kwargs}")
        else:
            logger.info(f"Job '{job['id']} disabled, skipping...")

    async def check_user_subscriptions(self):
        subs = self.load_subscriptions()
        if not subs:
            logger.info("No subscriptions found.")
            return

        for user_id, series_ids in subs.items():  # Unpacking user_id and series_ids
            try:
                # Fetch user with user_id
                user = await self.bot.fetch_user(user_id)
                logger.info(f"Processing user_id: {user}, series_ids: {series_ids}")

                # Ensure series_ids is either a list or int and handle both cases
                if isinstance(series_ids, int):
                    logger.info(f"Single series_id {series_ids} found for user {user_id}.")
                    series_ids = [series_ids]  # Wrap single series_id in a list
                elif not isinstance(series_ids, list):
                    logger.error(f"Unexpected type for series_ids: {type(series_ids)}. Skipping user {user_id}.")
                    continue  # Skip this user if series_ids is neither an int nor a list

                # Now process each series_id in the list
                for series_id in series_ids:
                    if isinstance(series_id, int):  # Ensure series_id is an integer
                        logger.info(f"Processing series_id: {series_id} for user {user_id}.")
                        series_metadata = self.bot.kavita_queries.get_series_metadata(series_id)
                        series_name = self.bot.kavita_queries.get_name_from_id(series_id)
                        library_id = self.bot.kavita_queries.get_library_id(series_id)
                        series_embed, file = self.embed_builder.build_series_embed(
                            series={'id': series_id, 'name': series_name, 'libraryId': library_id},
                            metadata=series_metadata,
                            thumbnail=False)
                        await user.send(embed=series_embed, file=file if file else None)
                        logger.info(f"Sent notification to user {user_id} for series {series_id}.")
                    else:
                        logger.error(f"Unexpected non-integer series_id: {series_id}. Skipping this series.")
            except discord.HTTPException as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")
            except Exception as e:
                logger.error(f"An error occurred while checking subscriptions: {e}")

    async def server_health_check(self):
        try:
            # Check the status of the Kavita API
            server_health_status = self.bot.kavita_queries.get_server_health()

            if server_health_status and server_health_status.status_code == 200:
                return True
            else:
                return False
        except Exception as e:
            logger.error(f"Error during server health check: {e}")

    def missed_job_listener(self, event):
        logger.warning(f"Job {event.job_id} missed its scheduled run time.")

    def start_scheduler(self):
        # Add listener for missed jobs
        self.scheduler.add_listener(self.missed_job_listener, EVENT_JOB_MISSED)
        self.scheduler.start()
        logger.info("Scheduler started.")

    def stop_scheduler(self):
        self.scheduler.shutdown()
        logger.info("Scheduler stopped.")
