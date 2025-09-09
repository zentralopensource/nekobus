import base64
from datetime import datetime
import logging
import requests
import urllib.parse
from .utils import CustomHTTPAdapter
from .version import __version__


logger = logging.getLogger(__name__)


def make_url_safe_serial_number(serial_number):
    if serial_number.startswith(".") or \
       urllib.parse.quote(serial_number, safe="") != serial_number:
        return ".{}".format(
            base64.urlsafe_b64encode(serial_number.encode("utf-8")).decode("utf-8").rstrip("=")
        )
    return serial_number


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

    def get_mdm_enrolled_device(self, serial_number):
        logger.info("Get MDM enrolled device %s", serial_number)
        try:
            r = self.session.get(f"{self.api_base_url}/mdm/devices/", params={"serial_number": serial_number})
            r.raise_for_status()
        except Exception:
            raise ZentralClientError(f"Could not search for MDM enrolled device {serial_number}")
        r_json = r.json()
        if "count" in r_json:
            device_count = r_json["count"]
            device_iter = r_json.get("results", [])
        else:
            # Older version of the API. TODO: remove.
            device_count = len(r_json)
            device_iter = r_json
        logger.info("Found %d MDM enrolled device(s) %s", device_count, serial_number)
        latest_enrolled_device = None
        for enrolled_device in device_iter:
            if latest_enrolled_device is None or enrolled_device["created_at"] > latest_enrolled_device["created_at"]:
                latest_enrolled_device = enrolled_device
        return latest_enrolled_device

    def get_tags(self, serial_number):
        logger.info("Get device %s tags", serial_number)
        url_safe_serial_number = make_url_safe_serial_number(serial_number)
        try:
            r = self.session.get(f"{self.api_base_url}/inventory/machines/{url_safe_serial_number}/meta/")
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r.json().get("tags", [])
        except Exception:
            raise ZentralClientError(f"Could not get device {serial_number} tags")

    def get_dep_status(self, serial_number, expected_profile_uuid):
        logger.info("Check DEP device %s enrollment status", serial_number)
        dep_device = self.get_dep_device(serial_number)
        if not dep_device:
            return "unknown"
        profile_uuid = dep_device.get("profile_uuid")
        if not profile_uuid:
            logger.warning("DEP device %s has no profile", serial_number)
            return "missing_profile"
        if profile_uuid != expected_profile_uuid:
            logger.warning("Wrong profile UUID %s for DEP device %s", profile_uuid or "-", serial_number)
            return "wrong_profile"
        profile_status = dep_device.get("profile_status")
        if profile_status not in ("assigned", "pushed"):
            logger.warning("Wrong profile status %s for DEP device %s", profile_status or "-", serial_number)
            return "wrong_profile_status"
        return "OK"

    def get_mdm_status(self, serial_number):
        logger.info("Check MDM enrolled device %s status", serial_number)
        enrolled_device = self.get_mdm_enrolled_device(serial_number)
        if not enrolled_device:
            logger.info("MDM enrolled device %s not found", serial_number)
            return "not_found"
        if enrolled_device.get("blocked_at"):
            logger.warning("MDM enrolled device %s blocked", serial_number)
            return "blocked"
        if enrolled_device.get("checkout_at"):
            logger.info("MDM enrolled device %s checked out", serial_number)
            return "checked_out"
        valid_cert = False
        try:
            valid_cert = datetime.fromisoformat(enrolled_device["cert_not_valid_after"]) > datetime.utcnow()
        except Exception:
            logger.exception("Could not verify MDM enrolled device %s cert validity. Default to False", serial_number)
        if not valid_cert:
            logger.info("MDM enrolled device %s has invalid cert", serial_number)
            return "invalid_cert"
        logger.info("MDM enrolled device %s has valid cert", serial_number)
        return "enrolled"

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
