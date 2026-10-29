resource "aws_db_subnet_group" "main" {
  name       = "${var.app_name}-${var.environment}-subnet-group"
  subnet_ids = var.database_subnet_ids

  tags = {
    Name        = "${var.app_name}-${var.environment}-subnet-group"
    Environment = var.environment
  }
}

resource "aws_db_parameter_group" "main" {
  name   = "${var.app_name}-${var.environment}-params"
  family = "mysql8.0"

  parameter {
    name  = "slow_query_log"
    value = "1"
  }

  parameter {
    name  = "long_query_time"
    value = "2"
  }

  parameter {
    name  = "log_output"
    value = "FILE"
  }

  tags = {
    Name        = "${var.app_name}-${var.environment}-params"
    Environment = var.environment
  }
}

resource "aws_db_instance" "main" {
  identifier                   = "${var.app_name}-${var.environment}"
  allocated_storage            = 20
  max_allocated_storage        = 100
  storage_type                 = "gp3"
  engine                       = "mysql"
  engine_version               = "8.0"
  instance_class               = var.db_instance_class
  db_name                      = var.db_name
  username                     = var.db_username
  password                     = var.db_password
  parameter_group_name         = aws_db_parameter_group.main.name
  db_subnet_group_name         = aws_db_subnet_group.main.name
  vpc_security_group_ids       = var.security_group_ids
  skip_final_snapshot          = var.environment == "prod" ? false : true
  final_snapshot_identifier    = var.environment == "prod" ? "${var.app_name}-${var.environment}-final-snapshot" : null
  multi_az                     = var.environment == "prod" ? true : false
  backup_retention_period      = var.backup_retention_period
  backup_window                = var.backup_window
  maintenance_window           = var.maintenance_window
  storage_encrypted            = var.storage_encrypted
  kms_key_id                   = var.kms_key_id != "" ? var.kms_key_id : null
  monitoring_interval          = var.monitoring_interval
  performance_insights_enabled = var.performance_insights_enabled
  deletion_protection          = var.environment == "prod" ? true : false
  auto_minor_version_upgrade   = true
  copy_tags_to_snapshot        = true

  tags = {
    Name        = "${var.app_name}-${var.environment}"
    Environment = var.environment
  }
}
