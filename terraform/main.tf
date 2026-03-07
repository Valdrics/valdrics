
data "aws_availability_zones" "available" {}

module "network" {
  source             = "./modules/network"
  environment        = var.environment
  availability_zones = slice(data.aws_availability_zones.available.names, 0, 2)
}

module "eks" {
  source             = "./modules/eks"
  environment        = var.environment
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
