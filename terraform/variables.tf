variable "project_name" {
  description = "Project name used as a prefix for all resources"
  type        = string
  default     = "clawhub"
}

variable "region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
}
