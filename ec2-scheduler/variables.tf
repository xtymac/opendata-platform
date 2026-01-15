variable "instance_id" {
  description = "EC2 Instance ID to schedule"
  type        = string
  default     = "i-0f50d5e5fd924b944"
}

variable "aws_region" {
  description = "AWS Region"
  type        = string
  default     = "ap-northeast-1"
}

variable "start_schedule" {
  description = "Cron expression for start (UTC)"
  type        = string
  default     = "cron(0 23 ? * * *)" # 23:00 UTC = 08:00 JST
}

variable "stop_schedule" {
  description = "Cron expression for stop (UTC)"
  type        = string
  default     = "cron(0 13 ? * * *)" # 13:00 UTC = 22:00 JST
}
