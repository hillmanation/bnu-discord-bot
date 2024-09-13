import requests
from urllib.parse import urlparse


class KavitaAPI:
    def __init__(self, url):
        self.url = url
        self.jwt_token = None
        self.host_address = None
        self.api_key = None
        self.headers = None
        self._parse_url()

    def _parse_url(self):
        parsed_url = urlparse(self.url)
        self.host_address = f"{parsed_url.scheme}://{parsed_url.netloc}"
        self.api_key = parsed_url.path.split('/')[-1]

    def authenticate(self):
        login_endpoint = "/api/Plugin/authenticate"
        try:
            response = requests.post(
                f"{self.host_address}{login_endpoint}?apiKey={self.api_key}&pluginName=pythonScanScript"
            )
            response.raise_for_status()
            self.jwt_token = response.json().get('token')
            self.headers = {
                "Authorization": f"Bearer {self.jwt_token}",
                "Content-Type": "application/json"
            }
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error during authentication: {e}")
            return False
