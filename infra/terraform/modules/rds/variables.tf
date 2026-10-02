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
  description = "Security groups allowed to connect on the PostgreSQL port, keyed by a static label (keys must be known at plan time)."
  type        = map(string)
}

variable "engine_version" {
  description = "PostgreSQL major version; minor versions are applied automatically."
  type        = string
  default     = "17"
}

variable "instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "allocated_storage" {
  type    = number
  default = 20
}

variable "database_name" {
  type    = string
  default = "testlens"
}

variable "master_username" {
  type    = string
  default = "testlens"
}

variable "multi_az" {
  type    = bool
  default = false
}

variable "deletion_protection" {
  type    = bool
  default = true
}

variable "tags" {
  type    = map(string)
  default = {}
}
