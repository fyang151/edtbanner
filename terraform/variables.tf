# variables.tf - Configurable inputs

variable "project_name" {
  description = "Name prefix for all resources"
  type        = string
  default     = "edt-hackathon-banner"
}

variable "aws_region" {
  description = "AWS region to deploy to"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, prod)"
  type        = string
  default     = "dev"
}
