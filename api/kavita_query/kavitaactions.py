import requests
from kavita_api import KavitaAPI
from kavita_config import *
from utilities.email_check import is_email_valid
import utilities.logging_config as logging_config

# Setup logging
logger = logging_config.setup_logging()


class KavitaActions:
    def __init__(self):
        self.kAPI = KavitaAPI(f"{opds_url}")

    def authenticate(self):
        # Login to the Kavita API
        return self.kAPI.authenticate()

    def new_user_invite(self, user_email: str):
        # When a user sends '/inviteme' to the bot, generate a user invite
        # API Auth
        if not self.kAPI.jwt_token:
            raise Exception("Authentication is required before accessing the API.")

        email_validate = is_email_valid(user_email)
        if email_validate:
            # If the email is good generate the invite
            headers = {
                "Authorization": f"Bearer {self.kAPI.jwt_token}",
                "Accept": "text/plain",
                "Content-Type": "application/json"
            }

            # Generate the invite API call and establish default permissions for the user
            data = {
                "email": user_email,
                "roles": [
                    "Download",
                    "Change Password",
                    "Bookmark",
                    "Login",
                    "Promote"
                ],
                "libraries": [
                    3, 4
                ],
                "ageRestriction": {
                    "ageRating": 0,
                    "includeUnknowns": True
                }
            }

            # Generate the email invite
            scan_endpoint = "/api/Account/invite"
            try:
                response = requests.post(f"{self.kAPI.host_address}{scan_endpoint}", headers=headers, json=data)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error sending email invite to API: {e}")
                return None
        else:
            return False