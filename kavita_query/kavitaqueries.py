import requests
import random
import logging_config as log
from api.kavita_api import KavitaAPI
from api.kavita_config import *

log = log.setup_logging()

class KavitaQueries:
    def __init__(self):
        self.kAPI = KavitaAPI(f"{opds_url}")

    def authenticate(self):
        # Login to the Kavita API
        return self.kAPI.authenticate()

    def get_series_info(self, series_id):
        # Ensure the API is authenticated
        if not self.kAPI.jwt_token:
            raise Exception("Authentication is required before accessing the API.")

        # Define request headers
        headers = {
            "Authorization": f"Bearer {self.kAPI.jwt_token}",
            "Content-Type": "application/json"
        }

        # Retrieve series info from the server
        scan_endpoint = f"/api/Series/{series_id}"
        try:
            response = requests.get(f"{self.kAPI.host_address}{scan_endpoint}", headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            log.error(f"Error fetching series info: {e}")
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
            log.error(f"Error fetching series cover: {e}")
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
            log.error(f"Error fetching series info: {e}")
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
            log.error(f"Error fetching server stats: {e}")
            return None

    def search_server(self, search_query: str):
        # Ensure the API is authenticated
        if not self.kAPI.jwt_token:
            raise Exception("Authentication is required before accessing the API.")

        headers = {
            "Authorization": f"Bearer {self.kAPI.jwt_token}",
            "Content-Type": "application/json"
        }

        # Send the search query to the API
        scan_endpoint = f"/api/Search/search?queryString={search_query}&includeChapterAndFiles=false"
        try:
            response = requests.get(f"{self.kAPI.host_address}{scan_endpoint}", headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            log.info(f"Error fetching server stats: {e}")
            return None

    def search_series_by_library_name(self, library_name):
        library_query = self.search_server(library_name)

        log.info(f"{library_query}")

    def get_random_series_id(self, library_id):
        series_ids = self.search_series_by_library_name(library_id)
        return random.choice(series_ids) if series_ids else None