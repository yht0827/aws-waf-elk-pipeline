variable "aws_region" {
  description = "AWS deployment region"
  type        = string
  default     = "ap-northeast-2" # 서울 리전
}

variable "project_name" {
  description = "Project name prefix"
  type        = string
  default     = "sec-pipeline"
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "production"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "Map of public subnet CIDR blocks by availability zone suffix"
  type        = map(string)
  default = {
    "a" = "10.0.1.0/24"
    "c" = "10.0.2.0/24"
  }
}

variable "private_subnet_cidrs" {
  description = "Map of private subnet CIDR blocks by availability zone suffix"
  type        = map(string)
  default = {
    "a" = "10.0.10.0/24"
  }
}

variable "instance_type" {
  description = "EC2 instance type for backend web servers"
  type        = string
  default     = "t3.micro"
}

variable "waf_rate_limit" {
  description = "Rate limit threshold for custom DDoS rule (requests per 5 minutes per IP)"
  type        = number
  default     = 100
}

variable "waf_log_retention_days" {
  description = "CloudWatch log retention period in days for WAF logs"
  type        = number
  default     = 7
}
