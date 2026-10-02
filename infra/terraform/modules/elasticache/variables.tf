variable "name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "allowed_security_group_ids" {
  description = "Security groups allowed to connect on the Redis port, keyed by a static label (keys must be known at plan time)."
  type        = map(string)
}

variable "engine_version" {
  type    = string
  default = "7.1"
}

variable "node_type" {
  type    = string
  default = "cache.t4g.small"
}

variable "num_cache_clusters" {
  description = "Primary plus replicas. Values above 1 enable automatic failover and Multi-AZ."
  type        = number
  default     = 2
}

variable "tags" {
  type    = map(string)
  default = {}
}
