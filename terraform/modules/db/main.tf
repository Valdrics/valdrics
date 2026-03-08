
data "aws_vpc" "selected" {
  id = var.vpc_id
}

locals {
  replica_enabled = trimspace(var.replicate_source_db_arn) != ""
  db_identifier   = "valdrics-db-${var.environment}${var.name_suffix}"
}

resource "aws_kms_key" "replica" {
  count                   = local.replica_enabled ? 1 : 0
  description             = "KMS key for cross-region Valdrics DB replica (${var.environment}${var.name_suffix})"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

resource "aws_db_subnet_group" "main" {
  name       = "valdrics-db-subnet-group-${var.environment}${var.name_suffix}"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "Valdrics DB Subnet Group"
  }
}

resource "aws_security_group" "rds" {
  name        = "valdrics-rds-sg-${var.environment}${var.name_suffix}"
  description = "Allow inbound traffic from EKS"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [var.eks_worker_sg_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [data.aws_vpc.selected.cidr_block]
  }

  tags = {
    Name = "valdrics-rds-sg-${var.environment}${var.name_suffix}"
  }
}

resource "aws_db_instance" "main" {
  identifier                   = local.db_identifier
  allocated_storage            = 20
  storage_type                 = "gp3"
  engine                       = "postgres"
  engine_version               = "16.3"
  instance_class               = var.db_instance_class
  db_name                      = local.replica_enabled ? null : var.db_name
  username                     = local.replica_enabled ? null : var.db_username
  password                     = local.replica_enabled ? null : var.db_password
  replicate_source_db          = local.replica_enabled ? var.replicate_source_db_arn : null
  parameter_group_name         = "default.postgres16"
  db_subnet_group_name         = aws_db_subnet_group.main.name
  vpc_security_group_ids       = [aws_security_group.rds.id]
  skip_final_snapshot          = var.skip_final_snapshot
  storage_encrypted            = true
  kms_key_id                   = local.replica_enabled ? aws_kms_key.replica[0].arn : null
  performance_insights_enabled = true
  multi_az                     = local.replica_enabled ? false : var.multi_az
  deletion_protection          = contains(["prod", "production"], lower(var.environment))

  backup_retention_period = local.replica_enabled ? max(var.backup_retention_period, 7) : var.backup_retention_period
  backup_window           = "03:00-04:00"
  copy_tags_to_snapshot   = true

  tags = {
    Name        = local.db_identifier
    Environment = var.environment
  }
}
