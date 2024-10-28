import requests
import random
import os
import tempfile
from datetime import datetime
import utilities.logging_config as logging_config
from kavita_api import KavitaAPI
from kavita_config import *
import urllib.parse
from assets.message_templates.server_status_template import server_status_template
from utilities.series_embed import EmbedBuilder

# Create the logger object
logger = logging_config.setup_logging()


class KavitaQueries:
    def __init__(self):
        self.kAPI = KavitaAPI(f"{opds_url}")
        # Source the series embed function
        self.embed_builder = EmbedBuilder(server_address=kavita_base_url, kavita_queries=self)

    def authenticate(self):
        # Login to the Kavita API
        return self.kAPI.authenticate()

    def generate_server_stats(self, daily_update=False, interaction=None):
        message = self.get_server_stats()
        if message:
            # Format the stats message
            stats_message, most_read = server_status_template(data=message, daily_update=daily_update,
                                                              interaction=interaction)

            # Create a list to hold the embeds
            embeds = []

            for series in most_read:
                series_id = series['value']['id']
                # Build variables and a clickable url to the server page for the series
                metadata = self.get_series_metadata(series_id)
                # Gather series metadata
                embed_result = self.embed_builder.build_series_embed(series, metadata, thumbnail=True)
                embeds.append(embed_result)

            return stats_message, embeds

    def get_series_info(self, series_id: int, verbose: bool = False):
        # Ensure the API is authenticated
        if not self.kAPI.jwt_token:
            raise Exception("Authentication is required before accessing the API.")

        # Define request headers
        headers = {
            "Authorization": f"Bearer {self.kAPI.jwt_token}",
            "Content-Type": "application/json"
        }

        if verbose:
            # Retrieve series info from the server
            scan_endpoint = f"/api/Series/series-detail?seriesId={series_id}"
            try:
                response = requests.get(f"{self.kAPI.host_address}{scan_endpoint}", headers=headers)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching series info: {e}")
                return None
        else:
            # Retrieve series info from the server
            scan_endpoint = f"/api/Series/{series_id}"
            try:
                response = requests.get(f"{self.kAPI.host_address}{scan_endpoint}", headers=headers)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching series info: {e}")
                return None

    def get_recent_chapters(self, series_id: int, since_date: str = None, limit: int = 3):
        # Get series detailed info
        detailed_info = self.get_series_info(series_id=series_id, verbose=True)

        if not detailed_info:
            logger.error(f"No detailed info found for series: {series_id}")
            return None

        # Parse since_date if provided
        if since_date:
            try:
                filter_date = datetime.strptime(since_date, "%Y-%m-%d")
            except ValueError:
                logger.error("Invalid date format! Please use YYYY-MM-DD.")
                return None
        else:
            filter_date = None

        # Sort chapters by title in descending order and limit the results to the 3 most recent chapters
        recent_chapters = sorted(
            detailed_info['chapters'],
            key=lambda x: x['created'],  # Assuming 'created' exists in each chapter
            reverse=True
        )
        chapters = []
        # Apply date filter if specified
        if filter_date:
            for chapter in recent_chapters:
                created_str = chapter['created']

                if '.' in created_str:
                    date_part, microsecond_part = created_str.split('.')
                    # Trim or pad the microsecond part to ensure it's 6 digits
                    microsecond_part = (microsecond_part + '000000')[:6]  # Ensure 6 digits
                    created_str = f"{date_part}.{microsecond_part}"  # Reconstruct the string

                # Attempt to parse the date
                try:
                    chapter_date = datetime.fromisoformat(created_str)
                    # Compare the parsed date with the filter date
                    if chapter_date > datetime.strptime(since_date, "%Y-%m-%d"):
                        chapters.append(chapter)
                except ValueError as e:
                    logger.error(f"Failed to parse date: {created_str} with error: {e}")
        else:
            chapters = recent_chapters

        # Ensure at least 1 chapter is returned
        if not chapters:
            # If no chapters after the filter date, return the most recent chapters regardless of the date
            chapters = sorted(
                detailed_info['chapters'],
                key=lambda x: x['created'],
                reverse=True
            )
            # Set the limit so that we show the last two chapters so you have something to go off of
            limit = 2

        return chapters[:limit]

    def send_recent_chapters_embed(self, manga_title, recent_chapters):
        if recent_chapters:
            chapter_embeds = []
            for recent_chapter in recent_chapters:
                if 'id' in recent_chapter:
                    embed_results = self.embed_builder.build_chapter_embed(
                        series_name=manga_title,
                        chapter_info=recent_chapter,
                        thumbnail=True
                    )
                    chapter_embeds.append(embed_results)
                else:
                    logger.warning("Unable to find chapter ID in provided info.")
            return chapter_embeds
        else:
            logger.error("Unable to find recent Chapters")
            return None

    def get_id_from_name(self, series_name):
        series = self.search_server(series_name)

        # Check if 'series' exists in the response and has items
        if 'series' in series and series['series']:
            for item in series['series']:
                if item['name'] == series_name:
                    return item['seriesId']
        else:
            logger.error(f"No series found for name: {series_name}. Response: {series}")
            return None

    def get_name_from_id(self, series_id):
        series_info = self.get_series_info(series_id)

        # Check if 'name' exists in the response
        if series_info and 'name' in series_info:
            return series_info['name']
        else:
            logger.error(f"No series info found for ID: {series_id}. Response: {series_info}")
            return None

    def get_library_id(self, series_id):
        series_info = self.get_series_info(series_id)

        # Check if 'name' exists in the response
        if series_info and 'libraryId' in series_info:
            return series_info['libraryId']
        else:
            logger.error(f"No series info found for ID: {series_id}. Response: {series_info}")
            return None

    def get_series_cover(self, series_id):
        # Ensure the API is authenticated
        if not self.kAPI.jwt_token:
            raise Exception("Authentication is required before accessing the API.")

        # Construct the full URL with the seriesId and apiKey
        url = f"{self.kAPI.host_address}/api/image/series-cover"
        params = {
            "seriesId": series_id,
            "apiKey": kavi_api_key  # Assuming you have the API key available in your instance
        }

        headers = {
            "Authorization": f"Bearer {self.kAPI.jwt_token}",
            "Accept": "*/*"
        }
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            # Create a temporary file for the series cover image
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_file.write(response.content)
            temp_file.flush()
            temp_file.seek(0)  # Go back to the start of the file

            return temp_file.name  # Return the temporary file path
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching series cover: {e}")
            return None

    def get_chapter_cover(self, chapter_id):
        # Ensure the API is authenticated
        if not self.kAPI.jwt_token:
            raise Exception("Authentication is required before accessing the API.")

        # Construct the full URL with the seriesId and apiKey
        url = f"{self.kAPI.host_address}/api/Image/chapter-cover"
        params = {
            "chapterId": chapter_id,
            "apiKey": kavi_api_key  # Assuming you have the API key available in your instance
        }

        headers = {
            "Authorization": f"Bearer {self.kAPI.jwt_token}",
            "Accept": "*/*"
        }
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            # Create a temporary file for the chapter cover image
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_file.write(response.content)
            temp_file.flush()
            temp_file.seek(0)  # Go back to the start of the file

            return temp_file.name  # Return the temporary file path
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching chapter cover: {e}")
            return None

    def get_series_metadata(self, series_id: int):
        # API Auth
        if not self.kAPI.jwt_token:
            raise Exception("Authentication is required before accessing the API.")

        # Define request headers
        headers = {
            "Authorization": f"Bearer {self.kAPI.jwt_token}",
            "Accept": "application/json"
        }

        # Retrieve series metadata from the server
        scan_endpoint = f"/api/Series/metadata?seriesId={series_id}"
        try:
            response = requests.get(f"{self.kAPI.host_address}{scan_endpoint}", headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching series info: {e}")
            return None

    def get_chapter_metadata(self, chapter_id: int):
        # API Auth
        if not self.kAPI.jwt_token:
            raise Exception("Authentication is required before accessing the API.")

        # Define request headers
        headers = {
            "Authorization": f"Bearer {self.kAPI.jwt_token}",
            "Accept": "application/json"
        }

        # Retrieve series metadata from the server
        scan_endpoint = f"/api/Metadata/chapter-summary?chapterId={chapter_id}"
        try:
            response = requests.get(f"{self.kAPI.host_address}{scan_endpoint}", headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching series info: {e}")
            return None

    def get_series_next_update(self, series_id: int):
        # API Auth
        if not self.kAPI.jwt_token:
            raise Exception("Authentication is required before accessing the API.")

        # Define request headers
        headers = {
            "Authorization": f"Bearer {self.kAPI.jwt_token}",
            "Accept": "application/json"
        }

        # Retrieve series metadata from the server
        scan_endpoint = f"/api/Series/next-expected?seriesId={series_id}"
        try:
            response = requests.get(f"{self.kAPI.host_address}{scan_endpoint}", headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching series next expected: {e}")
            return None

    def get_server_stats(self):
        # Ensure the API is authenticated
        if not self.kAPI.jwt_token:
            raise Exception("Authentication is required before accessing the API.")

        headers = {
            "Authorization": f"Bearer {self.kAPI.jwt_token}",
            "Content-Type": "application/json"
        }

        # Retrieve server stats
        scan_endpoint = "/api/Stats/server/stats"
        try:
            response = requests.get(f"{self.kAPI.host_address}{scan_endpoint}", headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching server stats: {e}")
            return None

    def get_server_health(self):
        # Ensure the API is authenticated
        if not self.kAPI.jwt_token:
            raise Exception("Authentication is required before accessing the API.")

        headers = {
            "Authorization": f"Bearer {self.kAPI.jwt_token}",
            "Content-Type": "application/json"
        }

        # Retrieve server health
        scan_endpoint = "/api/Health"
        try:
            response = requests.post(f"{self.kAPI.host_address}{scan_endpoint}", headers=headers)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.exception(f"Error Querying Server Health: {e}")
            return None

    def get_recently_updated(self):
        # Ensure API is authenticated
        if not self.kAPI.jwt_token:
            raise Exception("Authentication is required before accessing the API.")

        headers = {
            "Authorization": f"Bearer {self.kAPI.jwt_token}",
            "Content-Type": "application/json"
        }

        # Retrieve the updated series list
        scan_endpoint = "/api/Series/recently-updated-series"
        try:
            response = requests.post(f"{self.kAPI.host_address}{scan_endpoint}", headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.exception(f"Error fetching recently updated series: {e}")
            return None
        
    def search_server(self, search_query: str):
        # Verify the query is URL safe
        url_safe_query = urllib.parse.quote(search_query)

        # Ensure the API is authenticated
        if not self.kAPI.jwt_token:
            raise Exception("Authentication is required before accessing the API.")

        headers = {
            "Authorization": f"Bearer {self.kAPI.jwt_token}",
            "Content-Type": "application/json"
        }

        # Send the search query to the API
        scan_endpoint = f"/api/Search/search?queryString={url_safe_query}&includeChapterAndFiles=false"
        try:
            response = requests.get(f"{self.kAPI.host_address}{scan_endpoint}", headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.info(f"Error fetching server stats: {e}")
            return None

    def search_series_by_library_name(self, library_name):
        library_query = self.search_server(library_name)

        logger.info(f"{library_query}")

    def get_random_series_id(self, library_id):
        series_ids = self.search_series_by_library_name(library_id)
        return random.choice(series_ids) if series_ids else None