
variable "aws_region" {
  default = "us-east-1"
}

variable "secondary_aws_region" {
  description = "Secondary AWS region used for warm-standby regional failover."
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  default = "prod"
}

variable "cluster_name" {
  description = "Primary EKS cluster name prefix."
  type        = string
  default     = "valdrics"
}

variable "secondary_cluster_name" {
  description = "Secondary EKS cluster name prefix used for regional failover."
  type        = string
  default     = "valdrics-dr"
}

variable "enable_multi_region_failover" {
  description = "Provision warm-standby secondary-region infrastructure and cross-region database replication."
  type        = bool
  default     = false
}

variable "external_id" {
  description = "External ID for Valdrics cross-account access"
  type        = string
}

variable "valdrics_account_id" {
  description = "Valdrics's central account ID"
  type        = string
}

variable "enable_active_enforcement" {
  description = "Attach tag-scoped active remediation IAM permissions."
  type        = bool
  default     = false
}

variable "active_enforcement_resource_tag_key" {
  description = "Resource tag key required for active enforcement actions."
  type        = string
  default     = "ValdricsManaged"
}

variable "active_enforcement_resource_tag_value" {
  description = "Resource tag value required for active enforcement actions."
  type        = string
  default     = "true"
}

variable "enable_secret_rotation" {
  description = "Enable 90-day automatic Secrets Manager rotation for runtime secrets."
  type        = bool
  default     = false
}

variable "secret_rotation_lambda_arn" {
  description = "Rotation Lambda ARN for Secrets Manager rotation (required when enable_secret_rotation=true)."
  type        = string
  default     = ""
}

variable "runtime_secret_name" {
  description = "Secrets Manager secret name read by Kubernetes ExternalSecrets."
  type        = string
  default     = ""
}

variable "runtime_secret_initial_json" {
  description = "Optional initial JSON payload for the runtime secret."
  type        = string
  default     = ""
  sensitive   = true
}
