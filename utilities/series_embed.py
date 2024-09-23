import os
import re
import discord
from io import BytesIO
from datetime import datetime
import tempfile
import utilities.logging_config as logging_config

# Setup logging
logger = logging_config.setup_logging()


class EmbedBuilder:
    def __init__(self, server_address, kavita_queries):
        self.server_address = server_address
        self.kavita_queries = kavita_queries
        self.cover_image_file = None

    def build_series_url(self, series_id, series_library):
        return f"{self.server_address}/library/{series_library}/series/{series_id}"

    def build_description(self, metadata, series_url):
        return (f"\n\n**Author**:\n- {metadata['writers'][0]['name']}"
                f"\n**Summary**:\n{metadata['summary']}\n[**Read here**]({series_url})")

    def build_series_embed(self, series, metadata, thumbnail: bool = False):
        if 'value' in series:
            series_id = series['value']['id']
            series_name = series['value']['name']
            series_library = series['value']['libraryId']
        elif 'id' in series:
            series_id = series['id']
            series_name = series['name']
            series_library = series['libraryId']
        else:
            series_id = series['seriesId']
            series_name = series['name']
            series_library = series['libraryId']
        series_url = self.build_series_url(series_id, series_library)

        description = self.build_description(metadata, series_url)

        embed = discord.Embed(
            title=f"{series_name}",
            description=description if description else None,
            color=0x4ac694  # Kavita favicon color
        )

        series_cover_path = self.kavita_queries.get_series_cover(series_id)
        if series_cover_path:
            # Use the temporary file directly
            file_to_send = discord.File(series_cover_path, filename=f"series_cover_{series_id}.jpg")
            image_url = f"attachment://series_cover_{series_id}.jpg"
            # Set the image as a thumbnail if thumbnail version is requested, else use static image
            embed.set_thumbnail(url=image_url) if thumbnail else embed.set_image(url=image_url)

            # Return the embed and the file
            return embed, file_to_send
        else:
            return embed, None

    def build_chapter_embed(self, series_name, chapter_info, thumbnail: bool = False):
        series = self.kavita_queries.search_server(series_name)
        if series:
            series_id = series['series'][0]['seriesId']
            series_library = series['series'][0]['libraryId']

            chapter_id = chapter_info['id']
            chapter_title = chapter_info['title']

            series_url = self.build_series_url(series_id, series_library)
            chapter_url = f"{series_url}/chapter/{chapter_id}"
            chapter_summary = self.kavita_queries.get_chapter_metadata(chapter_id)

            # Build a list of pertinent info about the chapter
            chapter_info_lines = []

            # Check if releaseDate exists and is not the placeholder date
            if chapter_info.get('releaseDate'):
                release_date = datetime.fromisoformat(chapter_info['releaseDate'].replace('Z', '+00:00'))

                # Only append if the release date is valid
                if release_date.strftime('%B %d, %Y %H:%M:%S') != 'January 01, 0001 00:00:00':
                    chapter_info_lines.append(
                        f"**Original Release Date:** {release_date.strftime('%B %d, %Y %H:%M:%S')}")

            if chapter_info.get('pages'):
                chapter_info_lines.append(f"**Pages:** {chapter_info['pages']}")

            if chapter_info.get('volumeTitle'):
                chapter_info_lines.append(f"**Volume:** {chapter_info['volumeTitle']}")

            if chapter_info.get('created'):
                created_date_str = chapter_info['created']
                # Remove decimal places if present
                if '.' in created_date_str:
                    created_date_str = created_date_str[
                                       :created_date_str.index('.')]  # Keep only the part before the decimal

                # Add timezone info if it ends with 'Z'
                if created_date_str.endswith('Z'):
                    created_date_str = created_date_str[:-1] + '+00:00'  # Replace 'Z' with '+00:00'
                elif created_date_str[-6] == ':':
                    # Ensure there's a proper timezone if one is indicated
                    created_date_str = created_date_str[:-6] + '+00:00'

                added = datetime.fromisoformat(created_date_str)
                chapter_info_lines.append(f"**Added to Server:** {added.strftime('%B %d, %Y %H:%M:%S')}")

            chapter_info_lines.append(f"[**Read here**]({chapter_url})")

            # Join the chapter info lines into a single string
            chapter_info_text = "\n".join(chapter_info_lines)

            if chapter_summary and len(chapter_summary) > 140:
                chapter_summary = chapter_summary[:140] + '...' # Truncate and add ellipsis
            description = f"{chapter_summary}\n"

            embed = discord.Embed(
                title=f"{series_name}",
                color=0x4ac694  # Kavita favicon color
            )

            # Customize the chapter name in case there is a legitimate chapter title
            if chapter_info.get('titleName') and chapter_info['titleName'].replace('.', '') != chapter_title:
                chapter_title_full = f"{chapter_title} - {chapter_info['titleName']}"
            else:
                chapter_title_full = chapter_title
            # Customize the chapter info for the embed
            embed.add_field(name="Chapter", value=f"{chapter_title_full}", inline=False)
            embed.add_field(name="Summary:", value=description, inline=False) if description else None
            embed.add_field(name="Chapter Info", value=chapter_info_text or "No additional information available.",
                            inline=False)

            chapter_cover_path = self.kavita_queries.get_chapter_cover(chapter_id)
            if chapter_cover_path:
                # Use the temporary file directly
                file_to_send = discord.File(chapter_cover_path, filename=f"chapter_cover_{chapter_id}.jpg")
                image_url = f"attachment://chapter_cover_{chapter_id}.jpg"
                # Set the image as a thumbnail if thumbnail version is requested, else use static image
                embed.set_thumbnail(url=image_url) if thumbnail else embed.set_image(url=image_url)

                # Return the embed and the file
                return embed, file_to_send
            else:
                return embed, None
        else:
            return None

    def cleanup_temp_cover(self, temp_file_path):
        # Check to see if there is a temp file and remove it if there is
        if temp_file_path:
            try:
                os.remove(temp_file_path)
                logger.info(f"Temporary cover file {temp_file_path} deleted successfully.")
            except OSError as e:
                logger.error(f"Error deleting temporary cover file: {e}")

    def create_server_address_embed(self):
        server_name = "BNU Manga Server"
        header_img_path = 'assets/images/server_icon.png'

        embed = discord.Embed(
            title=server_name,
            description=f"Login to the Manga server here:\n\n[**{server_name}**]({self.server_address})",
            color=0x4ac694
        )

        # Use discord.File with the file path directly
        file = discord.File(header_img_path, filename='header.jpg')
        embed.set_thumbnail(url="attachment://header.jpg")

        embed.set_footer(text="--Read responsibly!!--")

        return embed, file
