# AWS lambda for MDM migration

This AWS lambda function supports three operations:

 - `check`
 - `start`
 - `finish`

Operations are passed as `operation` parameter in the URL query. The `serial_number` query parameter is also required.

### `check`

HTTP Method: `GET`

The lambda verifies in Zentral that the device has the correct DEP enrollment assigned in the Apple Business Manager.

Example:

```
curl -s -H "Authorization: Bearer $THE_NEKOBUS_TOKEN" \
'https://xxx.lambda-url.us-east-1.on.aws/?operation=check&serial_number=ABCDEFGHIJK'|jq .

{
  "operation": "check",
  "serial_number": "ABCDEFGHIJK",
  "check": true,
}
```

### `start`

HTTP Method: `POST`

**IMPORTANT** The lambda does the same verification as during the `check` operation, and if successful, the device is Unenrolled in Jamf, and the *started tag* is set on it in Zentral.

```
curl -s -XPOST -H "Authorization: Bearer $THE_NEKOBUS_TOKEN" \
'https://xxx.lambda-url.us-east-1.on.aws/?operation=start&serial_number=ABCDEFGHIJK'|jq .

{
  "operation": "start",
  "serial_number": "ABCDEFGHIJK",
}
```

### `finish`

HTTP Method: `POST`

The *finished tag* is set on the device in Zentral.

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
 * `mdm.view_depdevice`

You need a Service Account attached to this Role. Save its API token.
