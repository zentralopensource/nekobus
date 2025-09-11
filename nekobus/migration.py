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
        self.migration_tags = (
            self.ready_tag,
            self.started_tag,
            self.unenrolled_tag,
            self.finished_tag,
        )

    def check(self, serial_number):
        logger.info("Check device %s", serial_number)
        # tags
        tags = self.zentral_client.get_tags(serial_number)
        has_expected_tag = False
        if tags is None:
            logger.warning("Device %s not found in inventory", serial_number)
            migration_tags = []
        else:
            migration_tags = [t["name"] for t in tags if t["name"] in self.migration_tags]
            has_expected_tag = self.ready_tag in migration_tags
            if has_expected_tag:
                logger.info("Device %s has the %s tag", serial_number, self.ready_tag)
            else:
                logger.warning("Device %s doesn't have the %s tag", serial_number, self.ready_tag)
        # DEP status
        dep_status = self.zentral_client.get_dep_status(serial_number, self.profile_uuid)
        has_expected_dep_status = dep_status == "OK"
        if has_expected_dep_status:
            logger.info("Device %s DEP status %s", serial_number, dep_status)
        else:
            logger.warning("Device %s DEP status %s", serial_number, dep_status)
        # 404 and default tags
        if tags is None and dep_status == "unknown":
            raise MigrationError("Device not found", 404)
        return {
            "dep_status": dep_status,
            "migration_tags": migration_tags,
            "check": has_expected_tag and has_expected_dep_status
        }

    def start(self, serial_number):
        logger.info("Start device %s migration", serial_number)
        # IMPORTANT, we need to check otherwise this could be used to unenroll the whole fleet
        # without making sure that they can enroll again
        if not self.check(serial_number):
            raise MigrationError("Device not ready for migration")
        self.jamf_client.unmanage_computer_device(serial_number)
        self.zentral_client.set_taxonomy_tags(serial_number, self.taxonomy, [self.started_tag])
        logger.info("Device %s migration started", serial_number)

    def status(self, serial_number):
        logger.info("Get device %s MDM status", serial_number)
        # Just to be sure
        if not self.zentral_client.get_dep_status(serial_number, self.profile_uuid) == "OK":
            raise MigrationError("Device doesn't have the expected DEP enrollment")
        jamf_status = self.jamf_client.get_mdm_status(serial_number)
        if jamf_status == "unenrolled":
            self.zentral_client.set_taxonomy_tags(serial_number, self.taxonomy, [self.unenrolled_tag])
        zentral_status = self.zentral_client.get_mdm_status(serial_number)
        return {
            "jamf_status": jamf_status,
            "zentral_status": zentral_status,
        }

    def finish(self, serial_number):
        logger.info("Finish device %s migration", serial_number)
        self.zentral_client.set_taxonomy_tags(serial_number, self.taxonomy, [self.finished_tag])
        logger.info("Device %s migration finished", serial_number)
