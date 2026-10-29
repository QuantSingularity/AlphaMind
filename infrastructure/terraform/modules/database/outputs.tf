output "db_endpoint" {
  description = "Endpoint of the database"
  value       = aws_db_instance.main.endpoint
}

output "db_name" {
  description = "Name of the database"
  value       = aws_db_instance.main.db_name
}

output "db_username" {
  description = "Username of the database"
  value       = aws_db_instance.main.username
  sensitive   = true
}

output "db_instance_identifier" {
  description = "Identifier of the RDS instance"
  value       = try(aws_db_instance.main.identifier, "")
}

output "db_instance_arn" {
  description = "ARN of the RDS instance"
  value       = try(aws_db_instance.main.arn, "")
}
