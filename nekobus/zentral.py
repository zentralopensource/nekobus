import logging
import requests
from .utils import CustomHTTPAdapter
from .version import __version__


logger = logging.getLogger(__name__)


class ZentralClientError(Exception):
    pass


class ZentralClient:
    default_timeout = 15  # 15 seconds
    max_retries = 3  # max 3 attempts

    def __init__(self, base_url, token):
        self.api_base_url = f"{base_url}/api"
        self.session = requests.Session()
        self.session.headers.update(
            {'user-agent': f"nekobus/{__version__}",
             'accept': 'application/json',
             'authorization': f'Token {token}'}
        )
        self.session.mount(
            self.api_base_url,
            CustomHTTPAdapter(self.default_timeout, self.max_retries)
        )

    def get_dep_device(self, serial_number):
        logger.info("Get DEP device %s", serial_number)
        try:
            r = self.session.get(f"{self.api_base_url}/mdm/dep/devices/", params={"serial_number": serial_number})
            r.raise_for_status()
        except Exception:
            raise ZentralClientError(f"Could not get DEP device {serial_number} info")
        r_json = r.json()
        if r_json.get("count") == 1:
            logger.info("DEP device %s found", serial_number)
            return r_json["results"][0]
        else:
            logger.info("Unknown DEP device %s", serial_number)
            return None

    def check_dep_device_enrollment(self, serial_number, expected_profile_uuid):
        logger.info("Check DEP device %s enrollment", serial_number)
        dep_device = self.get_dep_device(serial_number)
        if not dep_device:
            return False
        ok = True
        profile_uuid = dep_device.get("profile_uuid")
        if profile_uuid != expected_profile_uuid:
            logger.warning("Wrong profile UUID %s for DEP device %s", profile_uuid or "-", serial_number)
            ok = False
        profile_status = dep_device.get("profile_status")
        if profile_status != "pushed":
            logger.warning("Wrong profile status %s for DEP device %s", profile_status or "-", serial_number)
            ok = False
        if ok:
            logger.info("DEP device %s enrollment OK", serial_number)
        return ok

    def set_taxonomy_tags(self, serial_number, taxonomy, tags):
        logger.info("Set device %s taxonomy %s tag(s) %s", serial_number, taxonomy, ", ".join(tags))
        try:
            r = self.session.post(
                f"{self.api_base_url}/inventory/machines/tags/",
                json={
                    "serial_numbers": [serial_number],
                    "operations": [
                        {"kind": "SET", "taxonomy": taxonomy, "names": tags}
                    ]
                }
            )
            r.raise_for_status()
        except Exception:
            raise ZentralClientError(f"Could not set device {serial_number} tags")
