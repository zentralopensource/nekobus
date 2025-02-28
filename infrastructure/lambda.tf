locals {
  lambda_name = local.namespace
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.lambda_name}"
  retention_in_days = 30
}

data "aws_iam_policy_document" "lambda" {
  statement {
    sid = "WriteLogs"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
    ]
    resources = [
      "arn:${data.aws_partition.current.partition}:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/${local.lambda_name}:*",
    ]
  }

  statement {
    sid = "ReadSecrets"
    actions = [
      "secretsmanager:GetSecretValue"
    ]
    resources = [
      aws_secretsmanager_secret.secrets.arn
    ]
  }
}

resource "aws_iam_policy" "lambda" {
  name        = "${local.namespace}-lambda"
  path        = local.path
  description = "IAM policy for the ${var.name} lambda"
  policy      = data.aws_iam_policy_document.lambda.json

  tags = var.tags
}

resource "aws_iam_role" "lambda" {
  name = "${local.namespace}-lambda"
  path = local.path

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "lambda" {
  role       = aws_iam_role.lambda.name
  policy_arn = aws_iam_policy.lambda.arn
}

resource "aws_lambda_function" "lambda" {
  function_name = local.lambda_name
  description   = "The ${var.name} lambda function"

  architectures = ["x86_64"]
  s3_bucket     = var.zip_archive_s3_bucket
  s3_key        = var.zip_archive_s3_key
  handler       = "lambda_function.lambda_handler"
  timeout       = 120
  runtime       = "python3.12"
  layers = [
    # see https://docs.aws.amazon.com/secretsmanager/latest/userguide/retrieving-secrets_lambda.html
    # see https://docs.aws.amazon.com/systems-manager/latest/userguide/ps-integration-lambda-extensions.html
    # TODO: only valid for us-east-2 on x86_64
    "arn:aws:lambda:us-east-2:590474943231:layer:AWS-Parameters-and-Secrets-Lambda-Extension:14"
  ]

  role = aws_iam_role.lambda.arn

  depends_on = [
    aws_cloudwatch_log_group.lambda
  ]

  environment {
    variables = {
      NEKOBUS_SECRET_NAME      = aws_secretsmanager_secret.secrets.name
      NEKOBUS_JAMF_BASE_URL    = var.jamf_base_url
      NEKOBUS_JAMF_CLIENT_ID   = var.jamf_client_id
      NEKOBUS_ZENTRAL_BASE_URL = var.zentral_base_url
      NEKOBUS_PROFILE_UUID     = var.profile_uuid
      NEKOBUS_TAXONOMY         = var.taxonomy
      NEKOBUS_READY_TAG        = var.ready_tag
      NEKOBUS_STARTED_TAG      = var.started_tag
      NEKOBUS_FINISHED_TAG     = var.finished_tag
    }
  }

  tags = var.tags
}

resource "aws_lambda_function_url" "lambda" {
  function_name      = aws_lambda_function.lambda.function_name
  authorization_type = "NONE"
}
