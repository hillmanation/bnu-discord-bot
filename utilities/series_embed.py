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

    def build_embed(self, series, metadata, thumbnail: bool = False):
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

        series_cover_data = self.kavita_queries.get_series_cover(series_id)
        if series_cover_data:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as self.cover_image_file:
                self.cover_image_file.write(series_cover_data)
                self.cover_image_file.flush()  # Ensure the file is written
                self.cover_image_file.seek(0)  # Move to the start of the file

                # Set the appropriate image URL
                image_url = f"attachment://{os.path.basename(self.cover_image_file.name)}"

                if thumbnail:
                    embed.set_thumbnail(url=image_url)
                else:
                    embed.set_image(url=image_url)

                # Return the embed and the discord.File from the temporary file
                file_to_send = discord.File(self.cover_image_file.name,
                                            filename=os.path.basename(self.cover_image_file.name))

            # Return the embed and the file to send
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
                # Limit the decimal places in the seconds
                if '.' in created_date_str:
                    created_date_str = created_date_str[:created_date_str.index('.') + 7]  # Keep 6 decimal places
                added = datetime.fromisoformat(created_date_str.replace('Z', '+00:00'))
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

            # Customize the chapter name in case there is a legetimate chapter title
            if chapter_info.get('titleName') and chapter_info['titleName'].replace('.', '') != chapter_title:
                chapter_title_full = f"{chapter_title} - {chapter_info['titleName']}"
            else:
                chapter_title_full = chapter_title
            # Customize the chapter info for the embed
            embed.add_field(name="Chapter", value=f"{chapter_title_full}", inline=False)
            embed.add_field(name="Summary:", value=description, inline=False) if description else None
            embed.add_field(name="Chapter Info", value=chapter_info_text or "No additional information available.",
                            inline=False)

            chapter_cover_data = self.kavita_queries.get_chapter_cover(chapter_id)
            if chapter_cover_data:
                # Create a temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as self.cover_image_file:
                    self.cover_image_file.write(chapter_cover_data)
                    self.cover_image_file.flush()  # Ensure the file is written
                    self.cover_image_file.seek(0)  # Move to the start of the file

                    # Set the appropriate image URL
                    image_url = f"attachment://{os.path.basename(self.cover_image_file.name)}"

                    if thumbnail:
                        embed.set_thumbnail(url=image_url)
                    else:
                        embed.set_image(url=image_url)

                    # Return the embed and the discord.File from the temporary file
                    file_to_send = discord.File(self.cover_image_file.name,
                                                filename=os.path.basename(self.cover_image_file.name))

                # Return the embed and the file to send
                return embed, file_to_send
            else:
                return embed, None
        else:
            return None

    def cleanup_temp_cover(self):
        # Check to see if there is a temp file and remove it if there is
        if hasattr(self, 'cover_image_file') and self.cover_image_file:
            try:
                os.remove(self.cover_image_file.name)
            except Exception as e:
                logger.error(f"Error deleting temporary cover file: {e}")
            finally:
                self.cover_image_file.close()  # Ensure the file is closed

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
