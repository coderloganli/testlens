variable "name" {
  description = "Name prefix for all VPC resources."
  type        = string
}

variable "cidr_block" {
  description = "IPv4 CIDR block for the VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to spread subnets across."
  type        = number
  default     = 2
}

variable "cluster_name" {
  description = "EKS cluster name, used for the subnet discovery tags load balancers rely on."
  type        = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
