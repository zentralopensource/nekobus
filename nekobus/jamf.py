from datetime import datetime, timedelta
import logging
import requests
from .utils import CustomHTTPAdapter
from .version import __version__

logger = logging.getLogger(__name__)


class JamfClientError(Exception):
    pass


class JamfClient:
    default_timeout = 15  # 15 seconds
    max_retries = 3  # max 3 attempts
    access_token_min_validity_seconds = 300  # 5 min

    def __init__(self, base_url, client_id, client_secret, api_path="/JSSResource"):
        self.base_url = base_url
        self.api_base_url = f"{base_url}{api_path}"
        self.client_id = client_id
        self.client_secret = client_secret
        self.session = requests.Session()
        self.session.headers.update({'user-agent': f"nekobus/{__version__}",
                                     'accept': 'application/json'})
        self.session.mount(
            self.api_base_url,
            CustomHTTPAdapter(self.default_timeout, self.max_retries)
        )
        self.access_token = None

    def refresh_access_token_if_necessary(self, force=False):
        if (
            force or
            self.access_token is None
            or (
                self.access_token["expires"]
                + timedelta(seconds=self.access_token_min_validity_seconds) < datetime.now()
            )
        ):
            logger.debug("Fetch access token for %s", self.base_url)
            self.session.headers.pop("Authorization", None)
            resp = self.session.post(
                f"{self.base_url}/api/oauth/token",
                data={
                    "client_id": self.client_id,
                    "grant_type": "client_credentials",
                    "client_secret": self.client_secret
                }
            )
            if resp.status_code != 200:
                raise JamfClientError(f"Could not get access token. Status code: {resp.status_code}")
            self.access_token = resp.json()
            self.access_token["expires"] = datetime.now() + timedelta(seconds=self.access_token.pop("expires_in"))
            logger.debug("Got access token for %s. Expires: %s", self.base_url, self.access_token["expires"])
            self.session.headers["Authorization"] = f'Bearer {self.access_token["access_token"]}'
        else:
            logger.debug("Re-use access token for %s. Expires: %s", self.base_url, self.access_token["expires"])
        return self.access_token["access_token"]

    def make_query(self, verb, path, missing_ok=False):
        url = f"{self.api_base_url}{path}"
        meth = getattr(self.session, verb.lower())
        for i in range(2):
            self.refresh_access_token_if_necessary()
            try:
                r = meth(url)
            except requests.exceptions.RequestException as e:
                raise JamfClientError(f"{verb} {url} {e}")
            if missing_ok and r.status_code == 404:
                return None
            if r.status_code == 200:
                return r.json()
            elif r.status_code == 201:
                return None
            elif r.status_code == 401:
                pass
            else:
                raise JamfClientError(f"{verb} {url} status code {r.status_code}")
        raise JamfClientError(f"{verb} {url} Unauthorized")

    def get_computer_device_id(self, serial_number):
        logger.info("Get computer %s Jamf ID", serial_number)
        response = self.make_query("GET", f"/computers/serialnumber/{serial_number}", missing_ok=True)
        if response is None:
            logger.error("Unknown Jamf computer %s", serial_number)
            return
        jamf_id = response["computer"]["general"]["id"]
        logger.info("Computer %s has Jamf ID %s", serial_number, jamf_id)
        return jamf_id

    def unmanage_computer_device(self, serial_number):
        logger.info("Unmanage computer %s", serial_number)
        jamf_id = self.get_computer_device_id(serial_number)
        if not jamf_id:
            return False
        try:
            self.make_query("POST", f"/computercommands/command/UnmanageDevice/id/{jamf_id}")
        except JamfClientError as e:
            logger.error("Could not queue Unenroll command for computer %s %s: %s", serial_number, jamf_id, e)
            return False
        else:
            logger.info("Unenroll command queued for computer %s", serial_number)
            return True
