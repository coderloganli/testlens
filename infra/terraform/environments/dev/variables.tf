variable "region" {
  type    = string
  default = "us-east-1"
}

variable "name" {
  description = "Name prefix for every resource in this environment."
  type        = string
  default     = "testlens-dev"
}
