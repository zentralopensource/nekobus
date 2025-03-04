import logging
from .jamf import JamfClient
from .zentral import ZentralClient


logger = logging.getLogger(__name__)


class MigrationError(Exception):
    def __init__(self, msg, status_code=400):
        super().__init__(msg)
        self.status_code = status_code


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
        ready_tag,
        started_tag,
        unenrolled_tag,
        finished_tag,
    ):
        self.jamf_client = JamfClient(jamf_base_url, jamf_client_id, jamf_client_secret)
        self.zentral_client = ZentralClient(zentral_base_url, zentral_token)
        self.profile_uuid = profile_uuid
        self.taxonomy = taxonomy
        self.ready_tag = ready_tag
        self.started_tag = started_tag
        self.unenrolled_tag = unenrolled_tag
        self.finished_tag = finished_tag

    def check(self, serial_number):
        logger.info("Check device %s", serial_number)
        result = self.zentral_client.check_tag(serial_number, self.ready_tag)
        if result is None:
            raise MigrationError("Device not found", 404)
        elif result:
            logger.info("Device %s has the %s tag", serial_number, self.ready_tag)
        else:
            logger.info("Device %s doesn't have the %s tag", serial_number, self.ready_tag)
            return False
        if self.zentral_client.check_dep_device_enrollment(serial_number, self.profile_uuid):
            logger.info("Device %s DEP enrollment %s OK", serial_number, self.profile_uuid)
            return True
        else:
            logger.info("Device %s DEP enrollment %s OK", serial_number, self.profile_uuid)
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

    def confirm_unenrolled(self, serial_number):
        logger.info("Confirm device %s is unenrolled", serial_number)
        # Just to be sure
        if not self.zentral_client.check_dep_device_enrollment(serial_number, self.profile_uuid):
            raise MigrationError("Device doesn't have the expected DEP enrollment")
        mdm_capable = self.jamf_client.is_computer_device_mdm_capable(serial_number)
        if not mdm_capable:
            self.zentral_client.set_taxonomy_tags(serial_number, self.taxonomy, [self.unenrolled_tag])
            logger.info("Device %s is unenrolled", serial_number)
        else:
            logger.info("Device %s is still enrolled", serial_number)
        return not mdm_capable

    def finish(self, serial_number):
        logger.info("Finish device %s migration", serial_number)
        self.zentral_client.set_taxonomy_tags(serial_number, self.taxonomy, [self.finished_tag])
        logger.info("Device %s migration finished", serial_number)
