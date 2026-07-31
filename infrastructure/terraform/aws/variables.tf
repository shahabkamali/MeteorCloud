variable "installation_name" {
  type        = string
  description = "Installation name used for tagging"
}

variable "environment" {
  type        = string
  description = "Deployment environment"
}

variable "aws_region" {
  type        = string
  description = "AWS region"
}

variable "aws_profile" {
  type        = string
  default     = ""
  description = "Optional AWS profile"
}

variable "availability_zone" {
  type        = string
  default     = ""
  description = "Optional availability zone"
}

variable "instance_type" {
  type        = string
  default     = "t3.small"
  description = "EC2 instance type"
}

variable "architecture" {
  type        = string
  default     = "amd64"
  description = "Instance architecture (amd64 or arm64)"
}

variable "ami_id" {
  type        = string
  default     = ""
  description = "Optional explicit AMI ID"
}

variable "ssh_key_name" {
  type        = string
  description = "EC2 SSH key pair name"
}

variable "root_volume_size_gb" {
  type        = number
  default     = 30
  description = "Root EBS volume size in GB"
}

variable "root_volume_type" {
  type        = string
  default     = "gp3"
  description = "Root EBS volume type"
}

variable "assign_elastic_ip" {
  type        = bool
  default     = true
  description = "Assign and associate an Elastic IP"
}

variable "allowed_ssh_cidrs" {
  type        = list(string)
  description = "CIDR blocks allowed for SSH"
}

variable "allow_http" {
  type        = bool
  default     = true
  description = "Allow HTTP from the internet"
}

variable "allow_https" {
  type        = bool
  default     = true
  description = "Allow HTTPS from the internet"
}

variable "tags" {
  type        = map(string)
  default     = {}
  description = "Additional resource tags"
}
