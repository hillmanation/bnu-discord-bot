import requests
import random
import utilities.logging_config as logging_config
from kavita_api import KavitaAPI
from kavita_config import *
import urllib.parse

logger = logging_config.setup_logging()


class KavitaQueries:
    def __init__(self):
        self.kAPI = KavitaAPI(f"{opds_url}")

    def authenticate(self):
        # Login to the Kavita API
        return self.kAPI.authenticate()

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

    def get_recent_chapters(self, series_id: int):
        # Get series detailed info
        detailed_info = self.get_series_info(series_id=series_id, verbose=True)

        if detailed_info:
            # Sort chapters by title in descending order and limit the results to the 3 most recent chapters
            recent_chapters = sorted(
                detailed_info['chapters'],
                key=lambda x: x['created'],  # Assuming 'title' exists in each chapter
                reverse=True
            )[:3]
            return recent_chapters
        else:
            logger.error(f"No detailed info found for series: {series_id}")
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
            # Save the image to a file (optional)
            with open(f"series_cover_{series_id}.jpg", "wb") as file:
                file.write(response.content)

            return response.content  # Return the raw image data
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
            # Save the image to a file (optional)
            with open(f"chapter_cover_{chapter_id}.jpg", "wb") as file:
                file.write(response.content)

            return response.content  # Return the raw image data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching series cover: {e}")
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