variable "project_name" {
  description = "Project name used as a prefix for all resources"
  type        = string
  default     = "clawhub"
}

variable "region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "admin_username" {
  description = "Default admin username (seeded on first deploy)"
  type        = string
  default     = "admin"
}

variable "admin_password" {
  description = "Default admin password (seeded on first deploy). Change after first login."
  type        = string
  default     = "changeme123"
  sensitive   = true
}
