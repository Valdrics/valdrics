# Failover and Availability Architecture

## Current State

The checked-in configuration provides in-region high availability by default
and supports opt-in automated secondary-region failover when
`enable_multi_region_failover=true` is applied in Terraform.

The repository does include a scheduled rebuild-and-verify disaster recovery
drill workflow (`.github/workflows/disaster-recovery-drill.yml`) so the manual
regional recovery path is exercised regularly instead of remaining a paper-only
procedure.

Repository-backed rebuild-and-verify objective:

- the automated drill must complete within 1200 seconds
- the drill evidence artifact records `duration_seconds`
- the drill evidence artifact records `regional_recovery_mode=manual_restore_redeploy_reroute`
- the drill evidence artifact records `regional_recovery_rto_seconds=1200`
- the drill evidence artifact records `regional_recovery_rpo_contract=provider_backup_restore_external_to_repository`
- this objective validates application rebuild, migrations, worker bootstrap,
  and API verification only; it does not claim a cloud-provider regional
  backup-restore RTO
- operator-controlled regional recovery for the repository-owned surface is
  therefore defined as: once restored data endpoints and replacement
  infrastructure are available, application rebuild, migrations, worker
  bootstrap, and traffic-cutover verification must complete within 1200 seconds
- repository-owned regional recovery therefore has an explicit manual contract:
  `RTO <= 1200s` for rebuild-and-verify after restored data endpoints are
  available, while `RPO` remains provider-backup/restore dependent outside the
  repository-managed application surface

Optional automated failover surface:

- Terraform can provision a warm-standby secondary region through
  `enable_multi_region_failover=true`
- the root Terraform outputs expose `secondary_eks_cluster_name` and
  `secondary_db_endpoint`
- `.github/workflows/regional-failover.yml` executes the scripted cutover path
- `.github/workflows/regional-failover.yml` requires `aws_role_to_assume` and
  configures AWS credentials through GitHub OIDC before mutation
- `scripts/run_regional_failover.py` promotes the secondary DB replica, verifies
  both `/health/live` and dependency-aware `/health`, requires healthy
  background job processing plus Celery worker heartbeat coverage, and only
  accepts a Cloudflare API response when `success=true`
- the automated cutover evidence records `aws_execution_identity` so the
  assumed AWS principal is part of the failover artifact
- the automated cutover evidence records
  `regional_recovery_mode=automated_secondary_region_failover`

## Availability Building Blocks

- Edge/frontend: Cloudflare Pages or ingress fronting the API surface
- API: multi-replica Helm deployment with anti-affinity and rolling updates
- Database: AWS RDS with Multi-AZ enabled
- Cache/rate-limit coordination: ElastiCache replication group with Multi-AZ enabled

## Failure Handling Model

### In-Region Failures

- RDS and Redis are expected to fail over inside the provisioned region.
- API replicas are expected to survive node-level failures through Kubernetes scheduling and anti-affinity.

### Cross-Region Failures

Cross-region recovery has two supported paths:

1. Default/manual profile when only the primary region is provisioned:

   1. Restore data from backups or snapshots into the target region.
   2. Apply infrastructure and deploy the application stack in that region.
   3. Update Cloudflare or other edge routing to direct traffic to the recovered stack.

2. Automated warm-standby profile when `enable_multi_region_failover=true` is enabled:

   1. Keep the secondary region provisioned with standby EKS, cache, and cross-region DB replica resources.
   2. Execute `scripts/run_regional_failover.py` or `.github/workflows/regional-failover.yml` with `aws_role_to_assume`.
   3. Promote the secondary DB replica, verify `/health/live` and `/health`, require healthy worker heartbeat coverage, and cut Cloudflare API DNS to the secondary origin only when the API reports dependency-ready status and Cloudflare returns `success=true`.

## What This Document Does Not Claim

- No DNS-provider-driven automatic failover is defined in the checked-in infrastructure.
- Autonomous failover without an operator-triggered script or workflow is not part of the supported production contract today.
