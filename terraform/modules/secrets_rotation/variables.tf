variable "environment" {
  description = "Deployment environment identifier."
  type        = string
}

variable "enable_secret_rotation" {
  description = "Enable automated Secrets Manager rotation for runtime secrets."
  type        = bool
  default     = false
}

variable "rotation_lambda_arn" {
  description = "ARN of the rotation Lambda used by Secrets Manager."
  type        = string
  default     = ""

  validation {
    condition = (
      var.enable_secret_rotation
      ? length(trimspace(var.rotation_lambda_arn)) > 0
      : true
    )
    error_message = "rotation_lambda_arn must be set when enable_secret_rotation is true."
  }
}

variable "runtime_secret_name" {
  description = "Secrets Manager secret name consumed by Kubernetes ExternalSecrets."
  type        = string
  default     = ""
}

variable "runtime_secret_initial_json" {
  description = "Optional initial JSON payload for the runtime secret."
  type        = string
  default     = ""
  sensitive   = true
}
