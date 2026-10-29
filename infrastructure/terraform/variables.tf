# Core Infrastructure Variables
variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-west-2"

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-[0-9]$", var.aws_region))
    error_message = "AWS region must be in the format: us-west-2, eu-west-1, etc."
  }
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be one of: dev, staging, prod."
  }
}

variable "app_name" {
  description = "Application name"
  type        = string
  default     = "alphamind"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]*[a-z0-9]$", var.app_name))
    error_message = "App name must start with a letter, contain only lowercase letters, numbers, and hyphens."
  }
}

# Network Configuration
variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "VPC CIDR must be a valid IPv4 CIDR block."
  }
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b", "us-west-2c"]

  validation {
    condition     = length(var.availability_zones) >= 2
    error_message = "At least 2 availability zones must be specified for high availability."
  }
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.4.0/24", "10.0.5.0/24", "10.0.6.0/24"]
}

variable "database_subnet_cidrs" {
  description = "CIDR blocks for database subnets"
  type        = list(string)
  default     = ["10.0.7.0/24", "10.0.8.0/24", "10.0.9.0/24"]
}

# Security Configuration
variable "allowed_cidr_blocks" {
  description = "CIDR blocks allowed to access the application"
  type        = list(string)
  default     = ["0.0.0.0/0"] # Should be restricted in production
}

variable "assume_role_arn" {
  description = "ARN of the role to assume for cross-account access"
  type        = string
  default     = null
}

# Compute Configuration
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium" # Upgraded for financial workloads

  validation {
    condition     = can(regex("^[a-z][0-9][a-z]?\\.(nano|micro|small|medium|large|xlarge|[0-9]+xlarge)$", var.instance_type))
    error_message = "Instance type must be a valid EC2 instance type."
  }
}

variable "key_name" {
  description = "SSH key name for EC2 instances"
  type        = string
  default     = null
}

# Auto Scaling Configuration
variable "asg_min_size" {
  description = "Minimum size of the Auto Scaling Group"
  type        = number
  default     = 2
}

variable "asg_max_size" {
  description = "Maximum size of the Auto Scaling Group"
  type        = number
  default     = 10
}

variable "asg_desired_capacity" {
  description = "Desired capacity of the Auto Scaling Group"
  type        = number
  default     = 3
}

# Database Configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.medium" # Upgraded for financial workloads
}

variable "db_name" {
  description = "Database name"
  type        = string
  default     = "alphamind"
}

variable "db_username" {
  description = "Database username"
  type        = string
  sensitive   = true
  default     = "alphamind_user"
}

variable "db_password" {
  description = "Database password"
  type        = string
  sensitive   = true

  validation {
    condition     = length(var.db_password) >= 12
    error_message = "Database password must be at least 12 characters long for PCI DSS compliance."
  }
}

variable "database_port" {
  description = "Database port"
  type        = number
  default     = 3306
}

variable "application_port" {
  description = "Application port"
  type        = number
  default     = 8080
}

# Database Backup Configuration
variable "db_backup_retention_period" {
  description = "Number of days to retain database backups"
  type        = number
  default     = 2555 # 7 years for financial compliance
}

variable "db_backup_window" {
  description = "Preferred backup window"
  type        = string
  default     = "03:00-04:00"
}

variable "db_maintenance_window" {
  description = "Preferred maintenance window"
  type        = string
  default     = "sun:04:00-sun:05:00"
}

# Encryption Configuration
variable "kms_deletion_window" {
  description = "KMS key deletion window in days"
  type        = number
  default     = 30

  validation {
    condition     = var.kms_deletion_window >= 7 && var.kms_deletion_window <= 30
    error_message = "KMS deletion window must be between 7 and 30 days."
  }
}

# WAF Configuration
variable "waf_rate_limit" {
  description = "WAF rate limit per 5-minute period"
  type        = number
  default     = 2000
}

# S3 Configuration
variable "s3_lifecycle_rules" {
  description = "S3 lifecycle rules for compliance"
  type = list(object({
    id     = string
    status = string
    transitions = list(object({
      days          = number
      storage_class = string
    }))
    expiration = object({
      days = number
    })
  }))
  default = [
    {
      id     = "financial_data_lifecycle"
      status = "Enabled"
      transitions = [
        {
          days          = 30
          storage_class = "STANDARD_IA"
        },
        {
          days          = 90
          storage_class = "GLACIER"
        },
        {
          days          = 365
          storage_class = "DEEP_ARCHIVE"
        }
      ]
      expiration = {
        days = 2555 # 7 years for financial compliance
      }
    }
  ]
}

# Monitoring Configuration
variable "log_retention_days" {
  description = "CloudWatch log retention period in days"
  type        = number
  default     = 2555 # 7 years for financial compliance
}

variable "alert_email_addresses" {
  description = "Email addresses for alerts"
  type        = list(string)
  default     = []
}

# Backup Configuration
variable "backup_schedule" {
  description = "Backup schedule in cron format"
  type        = string
  default     = "cron(0 2 * * ? *)" # Daily at 2 AM UTC
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 2555 # 7 years for financial compliance
}

# Compliance Tags
variable "default_tags" {
  description = "Default tags for all resources"
  type        = map(string)
  default = {
    Project    = "AlphaMind"
    Owner      = "Platform Team"
    CostCenter = "Engineering"
    Terraform  = "true"
  }
}

# Security Standards Configuration
variable "enable_pci_dss_compliance" {
  description = "Tag resources Compliance:PCI-DSS and subscribe Security Hub to the PCI DSS standard"
  type        = bool
  default     = true
}

variable "enable_gdpr_compliance" {
  description = "Tag resources Compliance:GDPR"
  type        = bool
  default     = true
}

variable "enable_sox_compliance" {
  description = "Tag resources Compliance:SOX"
  type        = bool
  default     = true
}

variable "enable_nist_csf_compliance" {
  description = "Tag resources Compliance:NIST-CSF"
  type        = bool
  default     = true
}

variable "enable_iso27001_compliance" {
  description = "Tag resources Compliance:ISO-27001"
  type        = bool
  default     = true
}

# Data Classification
variable "data_classification" {
  description = "Data classification level"
  type        = string
  default     = "Financial"

  validation {
    condition     = contains(["Public", "Internal", "Confidential", "Financial", "Restricted"], var.data_classification)
    error_message = "Data classification must be one of: Public, Internal, Confidential, Financial, Restricted."
  }
}

# Incident Response Configuration
variable "incident_response_email" {
  description = "Email address for incident response team"
  type        = string
  default     = "security@company.com"
}

variable "compliance_officer_email" {
  description = "Email address for compliance officer"
  type        = string
  default     = "compliance@company.com"
}

# Network Security Configuration
variable "enable_vpc_flow_logs" {
  description = "Create VPC Flow Logs in the network module"
  type        = bool
  default     = true
}

variable "enable_guardduty" {
  description = "Create the GuardDuty module (threat detection)"
  type        = bool
  default     = true
}

variable "enable_config" {
  description = "Create the AWS Config module (compliance recording; Security Hub standards rely on it)"
  type        = bool
  default     = true
}

variable "enable_cloudtrail" {
  description = "Create the CloudTrail module (audit logging)"
  type        = bool
  default     = true
}

variable "enable_security_hub" {
  description = "Create the Security Hub module (centralized findings; keep enable_config true for control results)"
  type        = bool
  default     = true
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS listener on the load balancer"
  type        = string
  default     = ""
}
