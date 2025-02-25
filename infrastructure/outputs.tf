output "secret_name" {
  value = aws_secretsmanager_secret.secrets.name
}

output "lambda_url" {
  value = aws_lambda_function_url.lambda.function_url
}
