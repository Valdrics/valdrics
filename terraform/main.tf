
data "aws_availability_zones" "available" {}

data "aws_availability_zones" "secondary" {
  count    = var.enable_multi_region_failover ? 1 : 0
  provider = aws.secondary
}

module "network" {
  source             = "./modules/network"
  environment        = var.environment
  cluster_name       = var.cluster_name
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 2)
}

module "eks" {
  source             = "./modules/eks"
  environment        = var.environment
  cluster_name       = var.cluster_name
  vpc_id             = module.network.vpc_id
  private_subnet_ids = module.network.private_subnet_ids
}

module "db" {
  source             = "./modules/db"
  environment        = var.environment
  vpc_id             = module.network.vpc_id
  private_subnet_ids = module.network.private_subnet_ids
  eks_worker_sg_id   = module.eks.node_security_group_id
}

module "cache" {
  source             = "./modules/cache"
  environment        = var.environment
  vpc_id             = module.network.vpc_id
  private_subnet_ids = module.network.private_subnet_ids
  eks_worker_sg_id   = module.eks.node_security_group_id
}

module "iam" {
  source                                = "./modules/iam"
  external_id                           = var.external_id
  valdrics_account_id                   = var.valdrics_account_id
  enable_active_enforcement             = var.enable_active_enforcement
  active_enforcement_resource_tag_key   = var.active_enforcement_resource_tag_key
  active_enforcement_resource_tag_value = var.active_enforcement_resource_tag_value
}

module "secrets_rotation" {
  source                      = "./modules/secrets_rotation"
  environment                 = var.environment
  enable_secret_rotation      = var.enable_secret_rotation
  rotation_lambda_arn         = var.secret_rotation_lambda_arn
  runtime_secret_name         = var.runtime_secret_name
  runtime_secret_initial_json = var.runtime_secret_initial_json
}

module "secondary_network" {
  count = var.enable_multi_region_failover ? 1 : 0

  source = "./modules/network"
  providers = {
    aws = aws.secondary
  }

  environment        = var.environment
  cluster_name       = var.secondary_cluster_name
  availability_zones = slice(data.aws_availability_zones.secondary[0].names, 0, 2)
}

module "secondary_eks" {
  count = var.enable_multi_region_failover ? 1 : 0

  source = "./modules/eks"
  providers = {
    aws = aws.secondary
  }

  environment        = var.environment
  cluster_name       = var.secondary_cluster_name
  name_suffix        = "-dr-${var.secondary_aws_region}"
  vpc_id             = module.secondary_network[0].vpc_id
  private_subnet_ids = module.secondary_network[0].private_subnet_ids
}

module "secondary_db" {
  count = var.enable_multi_region_failover ? 1 : 0

  source = "./modules/db"
  providers = {
    aws = aws.secondary
  }

  environment             = var.environment
  name_suffix             = "-dr-${var.secondary_aws_region}"
  vpc_id                  = module.secondary_network[0].vpc_id
  private_subnet_ids      = module.secondary_network[0].private_subnet_ids
  eks_worker_sg_id        = module.secondary_eks[0].node_security_group_id
  replicate_source_db_arn = module.db.db_arn
  multi_az                = false
  backup_retention_period = 7
}

module "secondary_cache" {
  count = var.enable_multi_region_failover ? 1 : 0

  source = "./modules/cache"
  providers = {
    aws = aws.secondary
  }

  environment        = var.environment
  vpc_id             = module.secondary_network[0].vpc_id
  private_subnet_ids = module.secondary_network[0].private_subnet_ids
  eks_worker_sg_id   = module.secondary_eks[0].node_security_group_id
}
