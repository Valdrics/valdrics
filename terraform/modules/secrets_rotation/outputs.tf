output "runtime_secret_name" {
  value = aws_secretsmanager_secret.runtime.name
}

output "runtime_secret_arn" {
  value = aws_secretsmanager_secret.runtime.arn
}

output "runtime_kms_key_arn" {
  value = aws_kms_key.runtime_secrets.arn
}
