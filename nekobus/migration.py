import logging
from .jamf import JamfClient
from .zentral import ZentralClient


logger = logging.getLogger(__name__)


class MigrationError(Exception):
    pass


class MigrationManager:
    def __init__(
        self,
        jamf_base_url,
        jamf_client_id,
        jamf_client_secret,
        zentral_base_url,
        zentral_token,
        profile_uuid,
        taxonomy,
        started_tag,
        finished_tag,
    ):
        self.jamf_client = JamfClient(jamf_base_url, jamf_client_id, jamf_client_secret)
        self.zentral_client = ZentralClient(zentral_base_url, zentral_token)
        self.profile_uuid = profile_uuid
        self.taxonomy = taxonomy
        self.started_tag = started_tag
        self.finished_tag = finished_tag

    def check(self, serial_number):
        logger.info("Check device %s", serial_number)
        if self.zentral_client.check_dep_device_enrollment(serial_number, self.profile_uuid):
            logger.info("Device %s OK", serial_number)
            return True
        else:
            logger.info("Device %s not OK", serial_number)
            return False

    def start(self, serial_number):
        logger.info("Start device %s migration", serial_number)
        # IMPORTANT, we need to check otherwise this could be used to unenroll the whole fleet
        # without making sure that they can enroll again
        if not self.check(serial_number):
            raise MigrationError("Device not ready for migration")
            return False
        self.jamf_client.unmanage_computer_device(serial_number)
        self.zentral_client.set_taxonomy_tags(serial_number, self.taxonomy, [self.started_tag])
        logger.info("Device %s migration started", serial_number)

    def finish(self, serial_number):
        logger.info("Finish device %s migration", serial_number)
        self.zentral_client.set_taxonomy_tags(serial_number, self.taxonomy, [self.finished_tag])
        logger.info("Device %s migration finished", serial_number)
