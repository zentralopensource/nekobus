resource "random_bytes" "nekobus-token-bytes" {
  length = 64
}

resource "aws_secretsmanager_secret" "secrets" {
  name = "${local.namespace}-secrets"

  # DANGER!!!
  recovery_window_in_days = 7

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "secrets" {
  secret_id = aws_secretsmanager_secret.secrets.id
  secret_string = jsonencode({
    nekobus_token      = random_bytes.nekobus-token-bytes.hex
    jamf_client_secret = var.jamf_client_secret
    zentral_token      = var.zentral_token
  })
}
