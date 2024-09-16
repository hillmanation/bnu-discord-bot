import discord
from io import BytesIO


class EmbedBuilder:
    def __init__(self, server_address, kavita_queries):
        self.server_address = server_address
        self.kavita_queries = kavita_queries

    def build_series_url(self, series_id, series_library):
        return f"{self.server_address}/library/{series_library}/series/{series_id}"

    def build_description(self, metadata, series_url):
        return (f"\n\n**Author**:\n- {metadata['writers'][0]['name']}"
                f"\n**Summary**:\n{metadata['summary']}\n[**Read here**]({series_url})")

    def build_embed(self, series, metadata):
        if 'value' in series:
            series_id = series['value']['id']
            series_name = series['value']['name']
            series_library = series['value']['libraryId']
        else:
            series_id = series['id']
            series_name = series['name']
            series_library = series['libraryId']
        series_url = self.build_series_url(series_id, series_library)

        description = self.build_description(metadata, series_url)

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

            return embed, discord.File(cover_image_file, filename=cover_image_file.name)
        else:
            return embed,

    def create_server_address_embed(self):
        # Define server details
        server_name = "BNU Manga Server"
        header_img_path = 'assets/images/server_icon.png'

        # Create the embed
        embed = discord.Embed(
            title=server_name,
            description=f"Login to the Manga server here:\n\n[**{server_name}**]({self.server_address})",
            color=0x4ac694  # Set a color for the embed
        )

        # Open the image file to use
        with open(header_img_path, 'rb') as img:
            file = discord.File(img, filename='header.jpg')
            # Set the header image in the embed
            embed.set_image(url="attachment://header.jpg")

        # Add a footer
        embed.set_footer(text="--Read responsibly!!--")

        return embed, file