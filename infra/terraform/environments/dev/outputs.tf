output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "postgres_address" {
  value = module.rds.address
}

output "postgres_master_secret_arn" {
  description = "Read the generated password from here to build DATABASE_URL for the Kubernetes Secret."
  value       = module.rds.master_user_secret_arn
}

output "redis_url" {
  value = module.elasticache.redis_url
}
