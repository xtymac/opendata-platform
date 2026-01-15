terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# IAM Role for Lambda
resource "aws_iam_role" "ec2_scheduler_role" {
  name = "ec2-scheduler-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy" "ec2_scheduler_policy" {
  name = "ec2-scheduler-policy"
  role = aws_iam_role.ec2_scheduler_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ec2:StartInstances",
          "ec2:StopInstances"
        ]
        Resource = "arn:aws:ec2:${var.aws_region}:*:instance/${var.instance_id}"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# Lambda function to START EC2
data "archive_file" "start_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/start.py"
  output_path = "${path.module}/lambda/start.zip"
}

resource "aws_lambda_function" "start_ec2" {
  filename         = data.archive_file.start_lambda_zip.output_path
  function_name    = "ec2-start-instance"
  role             = aws_iam_role.ec2_scheduler_role.arn
  handler          = "start.lambda_handler"
  source_code_hash = data.archive_file.start_lambda_zip.output_base64sha256
  runtime          = "python3.12"
  timeout          = 30

  environment {
    variables = {
      INSTANCE_ID = var.instance_id
      REGION      = var.aws_region
    }
  }
}

# Lambda function to STOP EC2
data "archive_file" "stop_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda/stop.py"
  output_path = "${path.module}/lambda/stop.zip"
}

resource "aws_lambda_function" "stop_ec2" {
  filename         = data.archive_file.stop_lambda_zip.output_path
  function_name    = "ec2-stop-instance"
  role             = aws_iam_role.ec2_scheduler_role.arn
  handler          = "stop.lambda_handler"
  source_code_hash = data.archive_file.stop_lambda_zip.output_base64sha256
  runtime          = "python3.12"
  timeout          = 30

  environment {
    variables = {
      INSTANCE_ID = var.instance_id
      REGION      = var.aws_region
    }
  }
}

# EventBridge rule to START EC2 at 08:00 JST
resource "aws_cloudwatch_event_rule" "start_ec2_rule" {
  name                = "ec2-start-morning"
  description         = "Start EC2 at 08:00 JST"
  schedule_expression = var.start_schedule
}

resource "aws_cloudwatch_event_target" "start_ec2_target" {
  rule      = aws_cloudwatch_event_rule.start_ec2_rule.name
  target_id = "start-ec2-lambda"
  arn       = aws_lambda_function.start_ec2.arn
}

resource "aws_lambda_permission" "allow_eventbridge_start" {
  statement_id  = "AllowEventBridgeStart"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.start_ec2.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.start_ec2_rule.arn
}

# EventBridge rule to STOP EC2 at 20:00 JST
resource "aws_cloudwatch_event_rule" "stop_ec2_rule" {
  name                = "ec2-stop-evening"
  description         = "Stop EC2 at 20:00 JST"
  schedule_expression = var.stop_schedule
}

resource "aws_cloudwatch_event_target" "stop_ec2_target" {
  rule      = aws_cloudwatch_event_rule.stop_ec2_rule.name
  target_id = "stop-ec2-lambda"
  arn       = aws_lambda_function.stop_ec2.arn
}

resource "aws_lambda_permission" "allow_eventbridge_stop" {
  statement_id  = "AllowEventBridgeStop"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stop_ec2.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.stop_ec2_rule.arn
}
