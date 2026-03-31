import logging

import requests

from app.core.config import settings
from app.exceptionhandler import CantoAthenticationFailed

logger = logging.getLogger(__name__)

STARTER_KIT_GROUP = "edc64c67-dad4-4db0-b040-40b7226400f2"
SHORT_FORM = "e7cd7230-b288-4cb4-a7ae-4ba7e6771db2"
BUSINESS_PLAN_GROUP = "bf01b86c-dda8-474c-8160-324100c0da3b"
BASIC_PLAN_GROUP = settings.CANTO_BASIC_PLAN_GROUP_ID
CANTO_API_URL = "https://sdamedia.canto.com/api/v1"

class CantoUsers:

    def __init__(self) -> None:
        self.canto_auth_token = CantoAuth().get_token()

    @staticmethod
    def _normalize_user_email(user_email: str) -> str:
        return user_email.strip().lower()

    def _create_canto_user(self, user_email, first_name, last_name, groups):
        normalized_email = self._normalize_user_email(user_email)
        payload = {
            "userId": normalized_email,
            "firstName": first_name,
            "lastName": last_name,
            "roles": ["consumer"],
            "groups": groups,
        }

        response = requests.post(
            f"{CANTO_API_URL}/user",
            json=payload,
            headers={"Authorization": f"Bearer {self.canto_auth_token}"},
            timeout=10,
        )
        response.raise_for_status()
        logger.info(
            "Canto user created: user_id=%s groups=%s status=%s",
            normalized_email,
            groups,
            response.status_code,
        )

    def create_new_user_starter_kit(self, user_email, first_name, last_name):
        self._create_canto_user(user_email, first_name, last_name, [STARTER_KIT_GROUP])

    def create_new_user_short_form(self, user_email, first_name, last_name):
        self._create_canto_user(user_email, first_name, last_name, [SHORT_FORM])

    def create_new_user_business_plan(self, user_email, first_name, last_name):
        self._create_canto_user(user_email, first_name, last_name, [BUSINESS_PLAN_GROUP])

    def create_new_user_basic_plan(self, user_email, first_name, last_name):
        self._create_canto_user(user_email, first_name, last_name, [BASIC_PLAN_GROUP])

    def add_user_to_group(self, group_id: str, user_email: str) -> None:
        normalized_email = self._normalize_user_email(user_email)
        response = requests.post(
            f"{CANTO_API_URL}/groups/{group_id}/users",
            json=[normalized_email],
            headers={"Authorization": f"Bearer {self.canto_auth_token}"},
            timeout=10,
        )
        response.raise_for_status()
        logger.info(
            "Canto add user to group succeeded: group_id=%s user_id=%s status=%s body=%s",
            group_id,
            normalized_email,
            response.status_code,
            response.text[:500],
        )

    def remove_user_from_group(self, group_id: str, user_email: str) -> None:
        normalized_email = self._normalize_user_email(user_email)
        response = requests.delete(
            f"{CANTO_API_URL}/groups/{group_id}/users",
            json=[normalized_email],
            headers={"Authorization": f"Bearer {self.canto_auth_token}"},
            timeout=10,
        )
        response.raise_for_status()
        logger.info(
            "Canto remove user from group succeeded: group_id=%s user_id=%s status=%s body=%s",
            group_id,
            normalized_email,
            response.status_code,
            response.text[:500],
        )

class CantoAuth:
    AUTH_URL = settings.CANTO_AUTH_URL
    APP_ID = settings.CANTO_APP_ID
    APP_SECRET = settings.CANTO_APP_SECRET

    def get_token(self):
        params = {
            "app_id": self.APP_ID,
            "app_secret": self.APP_SECRET,
            "grant_type": "client_credentials",
            "user_id": "wissem@sda.media",
        }
        resp = requests.post(self.AUTH_URL, params=params, timeout=10)

        if resp.status_code == 200:
            return resp.json()["accessToken"]
        else:
            raise CantoAthenticationFailed("response from canto: %s " % str(resp.text))
