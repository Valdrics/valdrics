data "google_project" "current" {
  project_id = var.gcp_project_id
}

locals {
  batch_image                         = trimspace(var.batch_job_image) != "" ? var.batch_job_image : var.api_image
  artifact_registry_image_match       = regex("^([a-z0-9-]+)-docker\\.pkg\\.dev/([^/]+)/([^/]+)/[^@]+@sha256:[0-9a-f]{64}$", var.api_image)
  artifact_registry_region            = local.artifact_registry_image_match[0]
  artifact_registry_project_id        = local.artifact_registry_image_match[1]
  artifact_registry_repository_id     = local.artifact_registry_image_match[2]
  manage_artifact_registry_reader_iam = local.artifact_registry_project_id == var.gcp_project_id
  api_hostname                        = split("/", trimprefix(var.api_url, "https://"))[0]
  frontend_hostname                   = split("/", trimprefix(var.frontend_url, "https://"))[0]
  api_origin                          = trimsuffix(var.api_url, "/")
  cloudflare_origin_allow_cidr_chunks = chunklist(var.cloudflare_origin_allow_cidrs, 10)
  managed_scheduler_jobs              = jsondecode(file("${path.module}/managed_scheduler_jobs.json"))

  runtime_default_env = {
    ENVIRONMENT                                   = var.environment
    API_URL                                       = var.api_url
    FRONTEND_URL                                  = var.frontend_url
    PLATFORM_RUNTIME_PROFILE                      = "gcp"
    OBSERVABILITY_BACKEND                         = "gcp"
    PUBLIC_API_RATE_LIMITING_BACKEND              = "cloudflare"
    RATELIMIT_ENABLED                             = "false"
    GCP_PROJECT_ID                                = var.gcp_project_id
    GCP_REGION                                    = var.gcp_region
    GCP_CLOUD_TASKS_QUEUE                         = google_cloud_tasks_queue.runtime.name
    GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL = google_service_account.internal_invoker.email
    GCP_CLOUD_RUN_SERVICE_NAME                    = var.cloud_run_service_name
    GCP_CLOUD_RUN_BATCH_JOB_NAME                  = var.cloud_run_batch_job_name
    GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS = jsonencode([
      google_service_account.internal_invoker.email,
      google_service_account.scheduler_invoker.email,
    ])
  }

  runtime_env = merge(local.runtime_default_env, var.runtime_plain_env)

  cloudflare_pages_env_vars = {
    PRIVATE_API_ORIGIN = {
      type  = "plain_text"
      value = local.api_origin
    }
    PUBLIC_API_URL = {
      type  = "plain_text"
      value = "${local.api_origin}/api/v1"
    }
    PUBLIC_SUPABASE_URL = {
      type  = "plain_text"
      value = lookup(local.runtime_env, "SUPABASE_URL", "")
    }
    PUBLIC_SUPABASE_ANON_KEY = {
      type  = "plain_text"
      value = lookup(local.runtime_env, "SUPABASE_ANON_KEY", "")
    }
  }
}

resource "google_project_service" "required" {
  for_each = toset([
    "cloudbuild.googleapis.com",
    "cloudtasks.googleapis.com",
    "cloudscheduler.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
  ])

  project            = var.gcp_project_id
  service            = each.key
  disable_on_destroy = false
}

resource "google_service_account" "runtime" {
  account_id   = "${var.environment}-valdrics-runtime"
  display_name = "Valdrics ${var.environment} runtime"
}

resource "google_service_account" "batch" {
  account_id   = "${var.environment}-valdrics-batch"
  display_name = "Valdrics ${var.environment} batch"
}

resource "google_service_account" "internal_invoker" {
  account_id   = "${var.environment}-valdrics-internal"
  display_name = "Valdrics ${var.environment} internal task invoker"
}

resource "google_service_account" "scheduler_invoker" {
  account_id   = "${var.environment}-valdrics-scheduler"
  display_name = "Valdrics ${var.environment} scheduler invoker"
}

resource "google_project_iam_member" "runtime_cloud_tasks_enqueuer" {
  project = var.gcp_project_id
  role    = "roles/cloudtasks.enqueuer"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "runtime_run_developer" {
  project = var.gcp_project_id
  role    = "roles/run.developer"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "runtime_secret_accessor" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_project_iam_member" "batch_secret_accessor" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.batch.email}"
}

resource "google_service_account_iam_member" "allow_cloud_tasks_service_agent" {
  service_account_id = google_service_account.internal_invoker.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-cloudtasks.iam.gserviceaccount.com"
}

resource "google_artifact_registry_repository_iam_member" "cloud_run_service_agent_image_reader" {
  count = local.manage_artifact_registry_reader_iam ? 1 : 0

  project    = local.artifact_registry_project_id
  location   = local.artifact_registry_region
  repository = local.artifact_registry_repository_id
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:service-${data.google_project.current.number}@serverless-robot-prod.iam.gserviceaccount.com"
}

resource "google_artifact_registry_repository_iam_member" "runtime_image_reader" {
  count = local.manage_artifact_registry_reader_iam ? 1 : 0

  project    = local.artifact_registry_project_id
  location   = local.artifact_registry_region
  repository = local.artifact_registry_repository_id
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.runtime.email}"
}

resource "google_artifact_registry_repository_iam_member" "batch_image_reader" {
  count = local.manage_artifact_registry_reader_iam ? 1 : 0

  project    = local.artifact_registry_project_id
  location   = local.artifact_registry_region
  repository = local.artifact_registry_repository_id
  role       = "roles/artifactregistry.reader"
  member     = "serviceAccount:${google_service_account.batch.email}"
}

resource "google_service_account_iam_member" "allow_cloud_scheduler_service_agent" {
  service_account_id = google_service_account.scheduler_invoker.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-cloudscheduler.iam.gserviceaccount.com"
}

resource "google_secret_manager_secret" "runtime" {
  for_each = toset(keys(nonsensitive(var.runtime_secret_env)))

  secret_id = "${var.environment}-${lower(replace(each.value, "_", "-"))}"

  replication {
    auto {}
  }

  depends_on = [google_project_service.required]
}

resource "google_secret_manager_secret_version" "runtime" {
  for_each = toset(keys(nonsensitive(var.runtime_secret_env)))

  secret      = google_secret_manager_secret.runtime[each.value].id
  secret_data = var.runtime_secret_env[each.value]
}

resource "google_cloud_tasks_queue" "runtime" {
  project  = var.gcp_project_id
  location = var.gcp_region
  name     = var.cloud_tasks_queue_name

  retry_config {
    max_attempts       = 10
    max_retry_duration = "3600s"
    max_backoff        = "300s"
    min_backoff        = "5s"
    max_doublings      = 5
  }

  rate_limits {
    max_dispatches_per_second = 25
    max_concurrent_dispatches = 25
  }

  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_service" "api" {
  name                 = var.cloud_run_service_name
  location             = var.gcp_region
  ingress              = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER"
  invoker_iam_disabled = true
  custom_audiences     = [var.api_url]

  template {
    service_account                  = google_service_account.runtime.email
    timeout                          = "${var.api_timeout_seconds}s"
    max_instance_request_concurrency = var.api_concurrency

    scaling {
      min_instance_count = var.api_min_instances
      max_instance_count = var.api_max_instances
    }

    containers {
      image = var.api_image

      ports {
        container_port = 8000
      }

      resources {
        limits = {
          cpu    = var.api_cpu
          memory = var.api_memory
        }
      }

      dynamic "env" {
        for_each = local.runtime_env
        content {
          name  = env.key
          value = env.value
        }
      }

      dynamic "env" {
        for_each = google_secret_manager_secret.runtime
        content {
          name = env.key
          value_source {
            secret_key_ref {
              secret  = env.value.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }

  traffic {
    percent = 100
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
  }

  depends_on = [
    google_project_service.required,
    google_artifact_registry_repository_iam_member.cloud_run_service_agent_image_reader,
    google_artifact_registry_repository_iam_member.runtime_image_reader,
  ]
}

resource "google_compute_global_address" "api_edge" {
  name = "${var.environment}-valdrics-api-edge"

  depends_on = [google_project_service.required]
}

resource "tls_private_key" "api_origin" {
  algorithm = "RSA"
  rsa_bits  = 2048
}

resource "tls_cert_request" "api_origin" {
  private_key_pem = tls_private_key.api_origin.private_key_pem

  subject {
    common_name  = local.api_hostname
    organization = "Valdrics"
  }

  dns_names = [local.api_hostname]
}

resource "cloudflare_origin_ca_certificate" "api_origin" {
  csr                = tls_cert_request.api_origin.cert_request_pem
  hostnames          = [local.api_hostname]
  request_type       = "origin-rsa"
  requested_validity = 5475
}

resource "google_compute_ssl_certificate" "api_origin" {
  name_prefix = "${var.environment}-valdrics-api-origin-"
  private_key = tls_private_key.api_origin.private_key_pem
  certificate = cloudflare_origin_ca_certificate.api_origin.certificate

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [google_project_service.required]
}

resource "google_compute_region_network_endpoint_group" "api" {
  name                  = "${var.environment}-valdrics-api-neg"
  region                = var.gcp_region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = google_cloud_run_v2_service.api.name
  }

  depends_on = [
    google_project_service.required,
    google_cloud_run_v2_service.api,
  ]
}

resource "google_compute_security_policy" "api_edge_origin" {
  name        = "${var.environment}-valdrics-api-origin"
  description = "Allow only Cloudflare edge traffic to reach the Valdrics API origin load balancer."
  type        = "CLOUD_ARMOR"

  dynamic "rule" {
    for_each = {
      for index, cidrs in local.cloudflare_origin_allow_cidr_chunks : index => cidrs
    }

    content {
      action      = "allow"
      priority    = 1000 + tonumber(rule.key)
      description = "Allow Cloudflare origin egress CIDR chunk ${rule.key}."

      match {
        versioned_expr = "SRC_IPS_V1"

        config {
          src_ip_ranges = rule.value
        }
      }
    }
  }

  rule {
    action      = "deny(403)"
    priority    = 2147483647
    description = "Deny direct origin access that bypasses Cloudflare."

    match {
      versioned_expr = "SRC_IPS_V1"

      config {
        src_ip_ranges = ["*"]
      }
    }
  }

  depends_on = [google_project_service.required]
}

resource "google_compute_backend_service" "api" {
  name                  = "${var.environment}-valdrics-api-backend"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTP"
  security_policy       = google_compute_security_policy.api_edge_origin.id

  backend {
    group = google_compute_region_network_endpoint_group.api.id
  }

  depends_on = [google_project_service.required]
}

resource "google_compute_url_map" "api" {
  name            = "${var.environment}-valdrics-api"
  default_service = google_compute_backend_service.api.id

  depends_on = [google_project_service.required]
}

resource "google_compute_target_https_proxy" "api" {
  name             = "${var.environment}-valdrics-api-https"
  url_map          = google_compute_url_map.api.id
  ssl_certificates = [google_compute_ssl_certificate.api_origin.id]

  depends_on = [google_project_service.required]
}

resource "google_compute_global_forwarding_rule" "api_https" {
  name                  = "${var.environment}-valdrics-api-https"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.api_edge.id
  port_range            = "443"
  target                = google_compute_target_https_proxy.api.id

  depends_on = [google_project_service.required]
}

resource "google_compute_url_map" "api_http_redirect" {
  name = "${var.environment}-valdrics-api-http"

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }

  depends_on = [google_project_service.required]
}

resource "google_compute_target_http_proxy" "api_http_redirect" {
  name    = "${var.environment}-valdrics-api-http"
  url_map = google_compute_url_map.api_http_redirect.id

  depends_on = [google_project_service.required]
}

resource "google_compute_global_forwarding_rule" "api_http" {
  name                  = "${var.environment}-valdrics-api-http"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.api_edge.id
  port_range            = "80"
  target                = google_compute_target_http_proxy.api_http_redirect.id

  depends_on = [google_project_service.required]
}

resource "google_cloud_run_v2_job" "batch" {
  name     = var.cloud_run_batch_job_name
  location = var.gcp_region

  template {
    task_count  = var.batch_task_count
    parallelism = var.batch_parallelism

    template {
      service_account = google_service_account.batch.email
      timeout         = "3600s"

      containers {
        image   = local.batch_image
        command = ["python", "-m", "app.shared.orchestration.job_runner"]
        args    = ["--work-item", "background_jobs.process", "--payload", "{}"]

        resources {
          limits = {
            cpu    = var.batch_cpu
            memory = var.batch_memory
          }
        }

        dynamic "env" {
          for_each = local.runtime_env
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = google_secret_manager_secret.runtime
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = env.value.secret_id
                version = "latest"
              }
            }
          }
        }
      }
    }
  }

  depends_on = [
    google_project_service.required,
    google_artifact_registry_repository_iam_member.cloud_run_service_agent_image_reader,
    google_artifact_registry_repository_iam_member.batch_image_reader,
  ]
}

resource "google_cloud_scheduler_job" "managed" {
  for_each = local.managed_scheduler_jobs

  name        = "${var.environment}-${replace(each.key, "_", "-")}"
  description = each.value.description
  project     = var.gcp_project_id
  region      = var.gcp_region
  schedule    = each.value.schedule
  time_zone   = each.value.time_zone

  http_target {
    http_method = "POST"
    uri         = "${google_cloud_run_v2_service.api.uri}/api/v1/internal/scheduler/dispatch"
    headers = {
      "Content-Type" = "application/json"
    }
    body = base64encode(
      jsonencode({
        work_item = each.value.work_item
        payload   = each.value.payload
      })
    )

    oidc_token {
      service_account_email = google_service_account.scheduler_invoker.email
      audience              = var.api_url
    }
  }

  depends_on = [
    google_project_service.required,
    google_cloud_run_v2_service.api,
  ]
}

resource "cloudflare_pages_project" "dashboard" {
  account_id        = var.cloudflare_account_id
  name              = var.cloudflare_pages_project_name
  production_branch = var.cloudflare_pages_production_branch

  deployment_configs = {
    preview = {
      compatibility_date  = "2026-03-01"
      compatibility_flags = ["nodejs_compat"]
      env_vars            = local.cloudflare_pages_env_vars
    }
    production = {
      compatibility_date  = "2026-03-01"
      compatibility_flags = ["nodejs_compat"]
      env_vars            = local.cloudflare_pages_env_vars
    }
  }
}

resource "cloudflare_dns_record" "dashboard" {
  zone_id = var.cloudflare_zone_id
  name    = local.frontend_hostname
  type    = "CNAME"
  content = cloudflare_pages_project.dashboard.subdomain
  proxied = true
  ttl     = 1
  comment = "Valdrics frontend routed through Cloudflare Pages."
}

resource "cloudflare_pages_domain" "dashboard" {
  account_id   = var.cloudflare_account_id
  project_name = cloudflare_pages_project.dashboard.name
  name         = local.frontend_hostname

  depends_on = [cloudflare_dns_record.dashboard]
}

resource "cloudflare_zone_setting" "ssl" {
  zone_id    = var.cloudflare_zone_id
  setting_id = "ssl"
  value      = "strict"
}

resource "cloudflare_zone_setting" "tls_1_3" {
  zone_id    = var.cloudflare_zone_id
  setting_id = "tls_1_3"
  value      = "on"
}

resource "cloudflare_bot_management" "api_zone" {
  zone_id    = var.cloudflare_zone_id
  fight_mode = false
}

resource "cloudflare_dns_record" "api" {
  zone_id = var.cloudflare_zone_id
  name    = local.api_hostname
  type    = "A"
  content = google_compute_global_address.api_edge.address
  proxied = true
  ttl     = 1
  comment = "Valdrics public API edge routed through Cloudflare and GCP external HTTPS load balancer."
}

resource "cloudflare_ruleset" "api_internal_block" {
  zone_id     = var.cloudflare_zone_id
  name        = "${var.environment}-valdrics-api-internal-block"
  description = "Block direct public access to Valdrics internal API paths."
  kind        = "zone"
  phase       = "http_request_firewall_custom"

  rules = [
    {
      ref         = "valdrics-health-probe-skip"
      action      = "skip"
      enabled     = true
      description = "Health probes must bypass Cloudflare browser challenges."
      expression  = "(http.host eq \"${local.api_hostname}\" and (http.request.uri.path eq \"/health\" or http.request.uri.path eq \"/health/live\"))"

      action_parameters = {
        phases = [
          "http_ratelimit",
          "http_request_firewall_managed",
          "http_request_sbfm",
        ]
        products = [
          "bic",
          "rateLimit",
          "securityLevel",
          "uaBlock",
          "waf",
          "zoneLockdown",
        ]
      }
    },
    {
      ref         = "valdrics-internal-api-block"
      action      = "block"
      enabled     = true
      description = "Internal scheduler and task endpoints are not internet-facing."
      expression  = "(http.host eq \"${local.api_hostname}\" and starts_with(http.request.uri.path, \"/api/v1/internal/\"))"
    },
  ]

  lifecycle {
    ignore_changes = [
      description,
      name,
      rules,
    ]
  }
}

resource "cloudflare_ruleset" "api_rate_limit" {
  zone_id     = var.cloudflare_zone_id
  name        = "${var.environment}-valdrics-api-rate-limit"
  description = "Throttle abusive bursts before they reach the Valdrics API origin."
  kind        = "zone"
  phase       = "http_ratelimit"

  rules = [
    {
      ref         = "valdrics-public-api-rate-limit"
      action      = "block"
      enabled     = true
      description = "Public API burst protection at the Cloudflare edge."
      expression  = "(http.host eq \"${local.api_hostname}\")"

      ratelimit = {
        characteristics     = ["cf.colo.id", "ip.src"]
        requests_per_period = var.cloudflare_api_rate_limit_requests_per_period
        period              = var.cloudflare_api_rate_limit_period_seconds
        mitigation_timeout  = var.cloudflare_api_rate_limit_mitigation_timeout_seconds
      }
    },
  ]

  lifecycle {
    ignore_changes = [
      description,
      name,
      rules,
    ]
  }
}

resource "supabase_project" "platform" {
  organization_id   = var.supabase_organization_id
  name              = var.supabase_project_name
  database_password = var.supabase_database_password
  region            = var.supabase_region

  lifecycle {
    ignore_changes = [database_password]
  }
}

resource "supabase_settings" "platform" {
  project_ref = supabase_project.platform.id

  api = jsonencode({
    db_schema            = "public,storage,graphql_public"
    db_extra_search_path = "public,extensions"
    max_rows             = 1000
  })

  auth = jsonencode({
    site_url = var.frontend_url
  })
}
