# scheduler_setup.py
import json
import asyncio
import discord
import utilities.logging_config as logging_config
from api.kavita_query.kavita_config import kavita_base_url
from utilities.series_embed import EmbedBuilder
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Setup logging
logger = logging_config.setup_logging()


class ScheduledJobs:
    def __init__(self, bot):
        self.scheduler = BackgroundScheduler()
        self.bot = bot
        self.jobs = []
        self.load_jobs_from_json()
        logger.info(f"Job scheduler started.")
        # Source the series embed function
        self.embed_builder = EmbedBuilder(server_address=kavita_base_url, kavita_queries=self.bot.kavita_queries)

    def load_jobs_from_json(self):
        # Load job config from file
        with open('assets/subscriptions/scheduled_jobs.json', 'r') as file:
            jobs = json.load(file)['jobs']
            for job in jobs:
                self.add_job(job)

    def load_subscriptions(self, file_path='assets/subscriptions/subscriptions.json'):
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                # Ensure that all values are lists
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
            # Run the async function using asyncio
            asyncio.run_coroutine_threadsafe(self.send_message_action(job), self.bot.loop)
        elif job_type == 'command':
            # Run the async function using asyncio
            asyncio.run_coroutine_threadsafe(self.run_command_action(job), self.bot.loop)
        # elif job_type == 'custom_action':
            # self.custom_action(job)
        else:
            logger.warning(f"Unknown job type: {job_type}")

    async def send_message_action(self, job):
        channel = self.bot.get_channel(job['channel_id'])
        if channel:
            message = job['message']
            self.bot.loop.create_task(channel.send(message))
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

        # Find the command or function and execute it
        if command_name == "mangastats":
            # Use the bot instance to call the extracted method directly
            # Create a mock interaction for this context
            class MockInteraction:
                def __init__(self, channel):
                    self.channel = channel
                    self.user = self.channel.guild.me  # Use the bot itself for the user

                async def response(self):
                    # Mock the followup response to the interaction
                    class Response:
                        async def send(self, message):
                            await self.channel.send(message)

                        async def defer(self):
                            pass  # No action needed for defer in this mock

                    return Response()

                async def followup(self):
                    return await self.response()

            interaction = MockInteraction(channel)
            await self.bot.tree.mangastats(interaction)
        elif command_name == "user_notifications":
            logger.info(f"Sending notifications to users")
            await self.check_user_subscriptions()
        else:
            logger.error(f"Command '{command_name}' not found in bot.")

    def add_job(self, job):
        # Define a job using CronTrigger
        self.scheduler.add_job(
            self.job_function,
            CronTrigger(hour=job['hour'], minute=job['minute'], second=job['second']),
            args=[job],
            id=job['id']
        )
        logger.info(f"Job '{job['id']}' added with schedule: {job['hour']}:{job['minute']}:{job['second']}")

    async def check_user_subscriptions(self):
        subs = self.load_subscriptions()
        if not subs:
            logger.info("No subscriptions found.")
            return

        for user_id, series_list in subs.items():
            try:
                user = await self.bot.fetch_user(user_id)
                for series_id in series_list:
                    series_metadata = self.bot.kavita_queries.get_series_metadata(series_id)
                    series_embed, file = self.embed_builder.build_embed(series=series_id, metadata=series_metadata,
                                                                        thumbnail=False)
                    await user.send(embed=series_embed, file=file if file else None)
                    logger.info(f"Sent notification to user {user_id} for series {series_id}.")
            except discord.HTTPException as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")
            except Exception as e:
                logger.error(f"An error occurred while checking subscriptions: {e}")

    def list_jobs(self):
        # List all scheduled jobs
        return self.jobs

    def start_scheduler(self):
        self.scheduler.start()
        logger.info("Scheduler started.")
        #log.info(self.list_jobs())

    def stop_scheduler(self):
        self.scheduler.shutdown()
        logger.info("Scheduler stopped.")
