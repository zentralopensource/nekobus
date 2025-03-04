import hmac
import json
import logging
import os
import requests
from nekobus.migration import MigrationError, MigrationManager


logger = logging.getLogger()
logger.setLevel(logging.INFO)


# NEKOBUS_SECRET_NAME
# references a AWS secret with a JSON value containing:
# - nekobus_token
# - jamf_client_secret
# - zentral_token
# NEKOBUS_JAMF_BASE_URL
# NEKOBUS_JAMF_CLIENT_ID
# NEKOBUS_ZENTRAL_BASE_URL
# NEKOBUS_PROFILE_UUID
# NEKOBUS_TAXONOMY
# NEKOBUS_READY_TAG
# NEKOBUS_STARTED_TAG
# NEKOBUS_UNENROLLED_TAG
# NEKOBUS_FINISHED_TAG


def build_response(status_code, err=None, body=None, headers=None):
    if body is None:
        body = {}
    if err:
        body["error"] = err
    response = {
        "statusCode": status_code,
        "body": json.dumps(body),
        "headers": {"content-type": "application/json"},
        "isBase64Encoded": False,
    }
    if headers:
        response["headers"].update(headers)
    return response


class LambdaError(Exception):
    def __init__(self, message, status_code, body=None, headers=None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body
        self.headers = headers

    def build_response(self):
        return build_response(
            self.status_code, err=self.args[0], body=self.body, headers=self.headers
        )


class LamdbaHandler:
    allowed_operations = {
        "check": "GET",
        "start": "POST",
        "status": "GET",
        "finish": "POST",
    }

    expected_secrets = (
        "nekobus_token",
        "jamf_client_secret",
        "zentral_token",
    )

    def get_secrets(self):
        logger.info("Get secrets")
        try:
            r = requests.get(
                "http://localhost:2773/secretsmanager/get",
                params={"secretId": os.environ["NEKOBUS_SECRET_NAME"]},
                headers={
                    "X-Aws-Parameters-Secrets-Token": os.environ["AWS_SESSION_TOKEN"]
                },
            )
            r.raise_for_status()
            secrets = json.loads(r.json()["SecretString"])
            assert isinstance(secrets, dict), "Invalid secret"
            assert set(secrets.keys()) == set(
                self.expected_secrets
            ), "Invalid secret keys"
            assert all(
                isinstance(v, str) and len(v) > 2 for v in secrets.values()
            ), "Invalid secret values"
        except Exception:
            logger.exception("Could not retrieve secret")
            raise LambdaError("Internal server error", 500)
        else:
            return (secrets[k] for k in self.expected_secrets)

    def __init__(self):
        self._initialized = False
        self.nekobus_token_bytes = None
        self.mm = None

    def initialize(self):
        if not self._initialized:
            nekobus_token, jamf_client_secret, zentral_token = self.get_secrets()
            self.nekobus_token_bytes = nekobus_token.encode("utf-8")
            self.mm = MigrationManager(
                os.environ["NEKOBUS_JAMF_BASE_URL"],
                os.environ["NEKOBUS_JAMF_CLIENT_ID"],
                jamf_client_secret,
                os.environ["NEKOBUS_ZENTRAL_BASE_URL"],
                zentral_token,
                os.environ["NEKOBUS_PROFILE_UUID"],
                os.environ["NEKOBUS_TAXONOMY"],
                os.environ["NEKOBUS_READY_TAG"],
                os.environ["NEKOBUS_STARTED_TAG"],
                os.environ["NEKOBUS_UNENROLLED_TAG"],
                os.environ["NEKOBUS_FINISHED_TAG"],
            )

    def authenticate(self, event):
        try:
            value = event["headers"]["authorization"]
        except KeyError:
            raise LambdaError("Missing 'Authorization' header", 401)
        else:
            request_token = value.removeprefix("Bearer ").encode("utf-8")
            if not hmac.compare_digest(request_token, self.nekobus_token_bytes):
                raise LambdaError("Unauthorized", 401)

    def process_params(self, event):
        try:
            params = event["queryStringParameters"]
            op = params["operation"]
            allowed_http_method = self.allowed_operations[op]
            serial_number = params["serial_number"]
            assert (
                isinstance(serial_number, str) and len(serial_number) > 2
            ), "Invalid serial number"
        except Exception:
            err = "Bad request"
            logger.exception(err)
            raise LambdaError(err, 400)
        if allowed_http_method != event["requestContext"]["http"]["method"]:
            raise LambdaError(
                "Method not Allowed", 405, headers={"Allow": allowed_http_method}
            )
        return op, serial_number

    def execute_operation(self, op, serial_number):
        logger.info("Operation %s device %s", op, serial_number)
        body = {
            "operation": op,
            "serial_number": serial_number,
        }
        try:
            result = getattr(self.mm, op)(serial_number)
        except MigrationError as e:
            logger.error("Operation %s device %s error: %s", op, serial_number, e)
            raise LambdaError("Not found" if e.status_code == 404 else "Bad request", e.status_code, body=body)
        except Exception:
            logger.exception("Operation %s device %s error", op, serial_number)
            raise LambdaError("Internal server error", 500, body=body)
        else:
            logger.info("Operation %s device %s OK", op, serial_number)
            if op in ("check", "status"):
                body.update(result)
            return build_response(200, body=body)

    def process_event(self, event):
        self.initialize()
        self.authenticate(event)
        op, serial_number = self.process_params(event)
        return self.execute_operation(op, serial_number)

    def __call__(self, event, context):
        logger.info("New request")
        try:
            return self.process_event(event)
        except LambdaError as e:
            return e.build_response()


lambda_handler = LamdbaHandler()
