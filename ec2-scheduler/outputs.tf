output "start_lambda_arn" {
  value = aws_lambda_function.start_ec2.arn
}

output "stop_lambda_arn" {
  value = aws_lambda_function.stop_ec2.arn
}

output "start_schedule" {
  value = "08:00 JST (${var.start_schedule})"
}

output "stop_schedule" {
  value = "22:00 JST (${var.stop_schedule})"
}
