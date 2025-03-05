# AWS lambda for MDM migration

This AWS lambda function supports four operations:

 - `check`
 - `start`
 - `status`
 - `finish`

Operations are passed as `operation` parameter in the URL query. The `serial_number` query parameter is also required.

### `check`

HTTP Method: `GET`

The lambda verifies in Zentral that the device has the *ready tag* and the correct DEP enrollment assigned in the Apple Business Manager.

Example:

```
curl -s -H "Authorization: Bearer $THE_NEKOBUS_TOKEN" \
'https://xxx.lambda-url.us-east-1.on.aws/?operation=check&serial_number=ABCDEFGHIJK'|jq .

{
  "operation": "check",
  "serial_number": "ABCDEFGHIJK",
  "dep_status": "OK",
  "migration_tags": ["ready"],
  "check": true
}
```

**IMPORTANT:** A migration must not be attempted if `dep_status` is not `OK`!!!


`check` is True if `dep_status` is `OK` and the *ready tag* is present in the `migration_tags`. If the `dep_status` is `OK` but the *ready tag* is not present, that is a good indication that a previous migration didn't finish as expected (not unenrolled, bad authentication, …).

### `start`

HTTP Method: `POST`

**IMPORTANT** The lambda does the same verification as during the `check` operation, and if successful:

 * the device is Unenrolled in Jamf
 * the *ready tag* is removed in Zentral
 * the *started tag* is set in Zentral.

```
curl -s -XPOST -H "Authorization: Bearer $THE_NEKOBUS_TOKEN" \
'https://xxx.lambda-url.us-east-1.on.aws/?operation=start&serial_number=ABCDEFGHIJK'|jq .

{
  "operation": "start",
  "serial_number": "ABCDEFGHIJK",
}
```

### `status`

HTTP Method: `GET`

Return the status of the enrollmemts in Jamf and Zentral. If the device is unenrolled in Jamf, the *started tag* is removed and the *unenrolled tag* is set on the device in Zentral.

```
curl -s -H "Authorization: Bearer $THE_NEKOBUS_TOKEN" \
'https://xxx.lambda-url.us-east-1.on.aws/?operation=confirm&serial_number=ABCDEFGHIJK'|jq .

{
  "operation": "status",
  "serial_number": "ABCDEFGHIJK",
  "jamf_status": "unenrolled",
  "zentral_status": "enrolled"
}
```

### `finish`

HTTP Method: `POST`

The *unenrolled tag* is removed and the *finished tag* is set on the device in Zentral.

```
curl -s -XPOST -H "Authorization: Bearer $THE_NEKOBUS_TOKEN" \
'https://xxx.lambda-url.us-east-1.on.aws/?operation=finish&serial_number=ABCDEFGHIJK'|jq .

{
  "operation": "finish",
  "serial_number": "ABCDEFGHIJK",
}
```

## Configuration

### Jamf

You need a API role with the `Read Computers`, and `Send Computer Unmanage Command` privileges. You also need an API client assigned to this role. Set the `Access token lifetime` to something reasonable like one hour, to avoid having to fetch too many access tokens. Save the `Client ID` and `Client Secret`.

### Zentral

You need a Role with the following permissions:

 * `inventory.add_tag`
 * `inventory.add_taxonomy`
 * `inventory.add_machinetag`
 * `inventory.delete_machinetag`
 * `inventory.view_machinesnapshot`
 * `mdm.view_depdevice`
 * `mdm.view_enrolleddevice`

You need a Service Account attached to this Role. Save its API token.
