module "vpc" {
  source       = "../../modules/vpc"
  name         = var.name
  cluster_name = var.name
}

module "eks" {
  source       = "../../modules/eks"
  cluster_name = var.name
  subnet_ids   = module.vpc.private_subnet_ids
}

module "rds" {
  source                     = "../../modules/rds"
  name                       = var.name
  vpc_id                     = module.vpc.vpc_id
  subnet_ids                 = module.vpc.private_subnet_ids
  allowed_security_group_ids = { eks_nodes = module.eks.cluster_security_group_id }
  deletion_protection        = false
}

module "elasticache" {
  source                     = "../../modules/elasticache"
  name                       = var.name
  vpc_id                     = module.vpc.vpc_id
  subnet_ids                 = module.vpc.private_subnet_ids
  allowed_security_group_ids = { eks_nodes = module.eks.cluster_security_group_id }
}
