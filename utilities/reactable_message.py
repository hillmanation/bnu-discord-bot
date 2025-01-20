import asyncio
import json
import os.path
from datetime import datetime, timedelta
from types import SimpleNamespace

import discord
import utilities.logging_config as logging_config
from api.kavita_query.kavita_config import *
from utilities.series_embed import EmbedBuilder

# Setup logging
logger = logging_config.setup_logging()


class ReactableMessage:
    def __init__(self, bot):
        self.bot = bot
        self.embed_builder = EmbedBuilder(server_address=kavita_base_url, kavita_queries=self.bot.kavita_queries)

    @staticmethod
    def create_reactable_message(emoji_manga_list, embed_title=None, embed_description=None, message_id=None,
                                 reaction_messages=None):
        # Create an embed for the given emoji/manga mapping list
        embed = discord.Embed(
            title=embed_title if embed_title else None,
            description=f"{embed_description if embed_description else None}\n\n" + "\n".join(
                f"{emoji_symbol}: {manga}" for emoji_symbol, manga in emoji_manga_list.items()
            ),
            color=0x4ac694  # You can change the color to match your theme, this is the Kavita icon color
        )
        # Path to thumbnail
        thumb_img_path = 'assets/images/server_icon.png'
        # Use discord.File with the file path directly
        file = discord.File(thumb_img_path, filename='thumbnail.jpg')
        embed.set_thumbnail(url="attachment://thumbnail.jpg")
        embed.set_footer(text=f"\nUse the emoji reacts below to get more info for the selected series:")

        # Return the emoji mapped message
        return embed, file

    async def handle_raw_reaction(self, payload, user, reaction_messages):
        # Handle RawReactionActionEvent
        if isinstance(payload, discord.RawReactionActionEvent):
            logger.info(f"Raw reaction on {payload.message_id} triggered")
            # Fetch the message for RawReactionActionEvent
            channel = self.bot.get_channel(payload.channel_id)
            emoji = str(payload.emoji)

            # Now proceed with matching the reaction to the emoji/series in the list
            if str(payload.message_id) in reaction_messages.keys():
                emoji_manga_list = reaction_messages[str(payload.message_id)]["emoji_mapping"]
                logger.info(f"User {user} requests more info in {channel}")

                # Find the corresponding manga for the reacted emoji
                for emoji_symbol, manga_title in emoji_manga_list.items():
                    if emoji == str(emoji_symbol):
                        series_id = self.bot.kavita_queries.get_id_from_name(manga_title)

                        # Check the message type, if it's "DM" we only want the Chapter info
                        message_type = reaction_messages[str(payload.message_id)]["type"]
                        series_info = False if message_type == "DM" else True

                        if series_id:
                            await self.send_series_info(series_id=series_id, channel=channel, series_info=series_info,
                                                        type=message_type, user_id=payload.user_id)
                        break

    async def handle_cached_reaction(self, reaction, user, reaction_messages):
        # For regular Reaction event
        message = reaction.message
        logger.info(f"Cached reaction on {message.id} triggered")
        emoji = str(reaction.emoji)
        channel = self.bot.get_channel(message.channel.id)

        # Now proceed with matching the reaction to the emoji/series in the list
        if message.id in reaction_messages.keys():
            emoji_manga_list = reaction_messages[message.id]["emoji_mapping"]
            logger.info(f"User {user} requests more info in {channel}")

            # Find the corresponding manga for the reacted emoji
            for emoji_symbol, manga_title in emoji_manga_list.items():
                if emoji == str(emoji_symbol):
                    series_id = self.bot.kavita_queries.get_id_from_name(manga_title)

                    # Check the message type, if it's "DM" we only want the Chapter info
                    message_type = reaction_messages[message.id]["type"]
                    series_info = False if message_type == "DM" else True

                    if series_id:
                        await self.send_series_info(series_id=series_id, channel=channel, series_info=series_info,
                                                    type=message_type, user_id=user.id)
                    else:
                        await message.channel.send(f"Invalid series ID {series_id}.")
                    break

    async def send_series_info(self, series_id, channel, series_info=True, chapter_info=True, type="Normal",
                               user_id=None):
        # Gather metadata
        metadata = self.bot.kavita_queries.get_series_metadata(series_id)
        series = self.bot.kavita_queries.get_series_info(series_id)
        series_name = self.bot.kavita_queries.get_name_from_id(series_id)

        if series_info and type != "DM":
            series_embed, file = self.embed_builder.build_series_embed(series=series, metadata=metadata,
                                                                       thumbnail=False)

            await channel.send(embed=series_embed, file=file if file else None)
            if file:
                self.embed_builder.cleanup_temp_cover(file.fp.name)

        if chapter_info and type != "DM":
            recent_chapters = self.bot.kavita_queries.get_recent_chapters(series_id)
            chapter_embeds = self.bot.kavita_queries.send_recent_chapters_embed(
                manga_title=series_name, recent_chapters=recent_chapters)

            for chapter_embed, file in chapter_embeds:
                await channel.send(embed=chapter_embed, file=file if file else None)
                if file:
                    self.embed_builder.cleanup_temp_cover(file.fp.name)
        elif chapter_info and type == "DM":
            # Fetch user with user id
            user = await self.bot.fetch_user(user_id)
            # Set the date to 7 days ago to prefer data from the last week
            today = datetime.now()
            seven_days_ago = today - timedelta(days=7)
            # Format it as a string in YYYY-MM-DD format
            since_date = seven_days_ago.strftime("%Y-%m-%d")
            recent_chapters = self.bot.kavita_queries.get_recent_chapters(series_id=series_id, since_date=since_date,
                                                                          limit=5)
            if recent_chapters:
                chapter_embeds = self.bot.kavita_queries.send_recent_chapters_embed(manga_title=series_name,
                                                                                    recent_chapters=recent_chapters)

                for chapter_embed, file in chapter_embeds:
                    await user.send(embed=chapter_embed, file=file if file else None)
                    if file:
                        self.embed_builder.cleanup_temp_cover(file.fp.name)

    @staticmethod
    def save_reaction_messages(file_path, emoji_manga_list, message_id=None, reaction_messages=None,
                               reaction_type="Normal"):
        if reaction_messages is None:
            reaction_messages = {}  # Initialize a local dictionary

        # Save the mapping if the message_id is provided
        if message_id and emoji_manga_list is not None:
            # Store the emoji mapping
            reaction_messages[message_id] = {
                "emoji_mapping": emoji_manga_list,
                "type": reaction_type
            }

            # Limit to 20 entries
            if len(reaction_messages) > 20:
                oldest_key = min(reaction_messages.keys(), key=int)  # Find the oldest entry
                del reaction_messages[oldest_key]  # Remove it
        try:
            with open(file_path, 'w') as f:
                json.dump(reaction_messages, f, indent=4)
                logger.info(f"Reaction messages and emoji mappings saved to JSON {file_path}.")
        except Exception as e:
            logger.error(f"Error saving reaction messages: {e}")

    @staticmethod
    def load_reaction_messages(file_path):
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    reaction_messages = json.load(f)
                    logger.info(f"Reaction messages loaded from JSON file.")
                    return reaction_messages
            except Exception as e:
                logger.error(f"Error loading reaction messages from {file_path}: {e}")
        return {}
