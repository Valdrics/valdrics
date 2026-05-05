variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "staging"

  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be staging or production."
  }
}

variable "gcp_project_id" {
  description = "Google Cloud project ID for the environment."
  type        = string
}

variable "gcp_region" {
  description = "Primary Google Cloud region for Cloud Run, Cloud Tasks, and Cloud Scheduler."
  type        = string
  default     = "us-central1"
}

variable "api_image" {
  description = "Digest-pinned Artifact Registry image ref for the API service."
  type        = string
}

variable "batch_job_image" {
  description = "Optional digest-pinned image ref for the Cloud Run batch job. Defaults to api_image when empty."
  type        = string
  default     = ""
}

variable "cloud_run_service_name" {
  description = "Cloud Run service name for the public API."
  type        = string
  default     = "valdrics-api"
}

variable "cloud_run_batch_job_name" {
  description = "Cloud Run Job name used for long-running managed work."
  type        = string
  default     = "valdrics-batch"
}

variable "cloud_tasks_queue_name" {
  description = "Cloud Tasks queue name for request-adjacent async work."
  type        = string
  default     = "valdrics-managed-work"
}

variable "api_url" {
  description = "Public HTTPS API URL exposed to clients."
  type        = string
}

variable "frontend_url" {
  description = "Public HTTPS frontend URL exposed to clients."
  type        = string
}

variable "runtime_plain_env" {
  description = "Non-secret API/runtime environment variables."
  type        = map(string)
  default     = {}
}

variable "runtime_secret_env" {
  description = "Secret API/runtime environment variables stored in Secret Manager."
  type        = map(string)
  default     = {}
  sensitive   = true
}

variable "api_min_instances" {
  description = "Minimum Cloud Run API instances."
  type        = number
  default     = 1
}

variable "api_max_instances" {
  description = "Maximum Cloud Run API instances."
  type        = number
  default     = 10
}

variable "api_concurrency" {
  description = "Maximum concurrent requests per API container."
  type        = number
  default     = 40
}

variable "api_timeout_seconds" {
  description = "Cloud Run API request timeout in seconds."
  type        = number
  default     = 900
}

variable "api_cpu" {
  description = "CPU limit for the API container."
  type        = string
  default     = "1"
}

variable "api_memory" {
  description = "Memory limit for the API container."
  type        = string
  default     = "1Gi"
}

variable "batch_cpu" {
  description = "CPU limit for the batch job container."
  type        = string
  default     = "2"
}

variable "batch_memory" {
  description = "Memory limit for the batch job container."
  type        = string
  default     = "2Gi"
}

variable "batch_parallelism" {
  description = "Parallelism for the Cloud Run batch job."
  type        = number
  default     = 1
}

variable "batch_task_count" {
  description = "Task count for the Cloud Run batch job."
  type        = number
  default     = 1
}

variable "cloudflare_api_token" {
  description = "Cloudflare API token with access to Pages project and DNS management."
  type        = string
  sensitive   = true
}

variable "cloudflare_account_id" {
  description = "Cloudflare account ID that owns the Pages project."
  type        = string
}

variable "cloudflare_zone_id" {
  description = "Cloudflare zone ID that owns the public API hostname."
  type        = string
}

variable "cloudflare_pages_project_name" {
  description = "Cloudflare Pages project name for the dashboard."
  type        = string
  default     = "valdrics"
}

variable "cloudflare_pages_production_branch" {
  description = "Production branch configured on the Cloudflare Pages project."
  type        = string
  default     = "main"
}

variable "cloudflare_api_rate_limit_requests_per_period" {
  description = "Edge rate-limit threshold for the Cloudflare-proxied public API."
  type        = number
  default     = 50

  validation {
    condition     = var.cloudflare_api_rate_limit_requests_per_period >= 1
    error_message = "cloudflare_api_rate_limit_requests_per_period must be >= 1."
  }
}

variable "cloudflare_api_rate_limit_period_seconds" {
  description = "Edge rate-limit rolling window in seconds for the public API."
  type        = number
  default     = 10

  validation {
    condition     = var.cloudflare_api_rate_limit_period_seconds >= 1
    error_message = "cloudflare_api_rate_limit_period_seconds must be >= 1."
  }
}

variable "cloudflare_api_rate_limit_mitigation_timeout_seconds" {
  description = "Block duration in seconds when the Cloudflare API rate-limit threshold is exceeded."
  type        = number
  default     = 60

  validation {
    condition     = var.cloudflare_api_rate_limit_mitigation_timeout_seconds >= 1
    error_message = "cloudflare_api_rate_limit_mitigation_timeout_seconds must be >= 1."
  }
}

variable "cloudflare_origin_allow_cidrs" {
  description = "Cloudflare origin egress CIDR ranges allowed to reach the GCP external HTTPS load balancer."
  type        = list(string)
  default = [
    "173.245.48.0/20",
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "141.101.64.0/18",
    "108.162.192.0/18",
    "190.93.240.0/20",
    "188.114.96.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    "162.158.0.0/15",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "172.64.0.0/13",
    "131.0.72.0/22",
    "2400:cb00::/32",
    "2606:4700::/32",
    "2803:f800::/32",
    "2405:b500::/32",
    "2405:8100::/32",
    "2a06:98c0::/29",
    "2c0f:f248::/32",
  ]

  validation {
    condition     = length(var.cloudflare_origin_allow_cidrs) > 0
    error_message = "cloudflare_origin_allow_cidrs must contain at least one Cloudflare CIDR."
  }
}

variable "supabase_access_token" {
  description = "Supabase access token used by the Terraform provider."
  type        = string
  sensitive   = true
}

variable "supabase_organization_id" {
  description = "Supabase organization ID that owns the environment project."
  type        = string
}

variable "supabase_project_name" {
  description = "Supabase project name for the environment."
  type        = string
}

variable "supabase_database_password" {
  description = "Initial Supabase database password. Import existing projects to avoid recreating them."
  type        = string
  sensitive   = true
}

variable "supabase_region" {
  description = "Supabase region for the environment project."
  type        = string
  default     = "us-east-1"
}
