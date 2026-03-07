
output "vpc_id" {
  value = module.network.vpc_id
}

output "eks_cluster_name" {
  value = module.eks.cluster_name
}

output "db_endpoint" {
  value = module.db.db_endpoint
}

output "valdrics_role_arn" {
  value = module.iam.role_arn
}

output "valdrics_active_enforcement_enabled" {
  value = module.iam.active_enforcement_enabled
}

output "runtime_secret_name" {
  value = module.secrets_rotation.runtime_secret_name
}

output "runtime_secret_arn" {
  value = module.secrets_rotation.runtime_secret_arn
}

output "runtime_secret_kms_key_arn" {
  value = module.secrets_rotation.runtime_kms_key_arn
}
