from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_network_module_uses_one_nat_gateway_per_private_subnet_az() -> None:
    text = (REPO_ROOT / "terraform/modules/network/main.tf").read_text(
        encoding="utf-8"
    )

    assert 'resource "aws_eip" "nat" {' in text
    assert "count  = length(var.private_subnet_cidrs)" in text
    assert 'resource "aws_nat_gateway" "main" {' in text
    assert "aws_nat_gateway.main[count.index].id" in text
    assert "aws_route_table.private[count.index].id" in text
    assert "precondition" in text


def test_cache_module_enables_multi_az_failover() -> None:
    text = (REPO_ROOT / "terraform/modules/cache/main.tf").read_text(
        encoding="utf-8"
    )

    assert "num_cache_clusters         = 2" in text
    assert "automatic_failover_enabled = true" in text
    assert "multi_az_enabled           = true" in text


def test_db_module_enables_multi_az_rds() -> None:
    text = (REPO_ROOT / "terraform/modules/db/main.tf").read_text(encoding="utf-8")

    assert "multi_az                     = local.replica_enabled ? false : var.multi_az" in text
    assert 'contains(["prod", "production"], lower(var.environment))' in text


def test_terraform_root_supports_optional_secondary_region_failover() -> None:
    providers = (REPO_ROOT / "terraform/providers.tf").read_text(encoding="utf-8")
    variables = (REPO_ROOT / "terraform/variables.tf").read_text(encoding="utf-8")
    root_main = (REPO_ROOT / "terraform/main.tf").read_text(encoding="utf-8")
    db_module = (REPO_ROOT / "terraform/modules/db/main.tf").read_text(encoding="utf-8")

    assert 'alias  = "secondary"' in providers
    assert 'variable "enable_multi_region_failover"' in variables
    assert 'variable "secondary_aws_region"' in variables
    assert 'module "secondary_network"' in root_main
    assert 'module "secondary_eks"' in root_main
    assert 'module "secondary_db"' in root_main
    assert 'module "secondary_cache"' in root_main
    assert "replicate_source_db_arn = module.db.db_arn" in root_main
    assert "replicate_source_db          = local.replica_enabled ? var.replicate_source_db_arn : null" in db_module
    assert 'resource "aws_kms_key" "replica"' in db_module
