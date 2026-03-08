# main.tf - Hackathon Banner Infrastructure

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.0"
}

provider "aws" {
  region = var.aws_region
}

# --------------------------------------------
# S3 Bucket for Images
# --------------------------------------------
resource "aws_s3_bucket" "images" {
  bucket = "${var.project_name}-images-${var.environment}"
}

resource "aws_s3_bucket_cors_configuration" "images" {
  bucket = aws_s3_bucket.images.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = ["*"]
    max_age_seconds = 3000
  }
}

# --------------------------------------------
# DynamoDB Table for Image Metadata
# --------------------------------------------
resource "aws_dynamodb_table" "images" {
  name         = "${var.project_name}-images-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "imageId"

  attribute {
    name = "imageId"
    type = "S"
  }
}

# --------------------------------------------
# IAM Role for Lambda Functions
# --------------------------------------------
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role-${var.environment}"

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

resource "aws_iam_role_policy" "lambda_policy" {
  name = "${var.project_name}-lambda-policy-${var.environment}"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.images.arn,
          "${aws_s3_bucket.images.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Scan",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.images.arn
      },
      {
        Effect = "Allow"
        Action = [
          "rekognition:DetectModerationLabels"
        ]
        Resource = "*"
      }
    ]
  })
}

# --------------------------------------------
# Lambda Functions
# --------------------------------------------

# Package Lambda code
data "archive_file" "get_upload_url" {
  type        = "zip"
  source_file = "${path.module}/../lambdas/get_upload_url.py"
  output_path = "${path.module}/zip/get_upload_url.zip"
}

data "archive_file" "process_image" {
  type        = "zip"
  source_file = "${path.module}/../lambdas/process_image.py"
  output_path = "${path.module}/zip/process_image.zip"
}

data "archive_file" "list_images" {
  type        = "zip"
  source_file = "${path.module}/../lambdas/list_images.py"
  output_path = "${path.module}/zip/list_images.zip"
}

# Lambda: getUploadUrl
resource "aws_lambda_function" "get_upload_url" {
  filename         = data.archive_file.get_upload_url.output_path
  source_code_hash = data.archive_file.get_upload_url.output_base64sha256
  function_name    = "${var.project_name}-getUploadUrl-${var.environment}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "get_upload_url.lambda_handler"
  runtime          = "python3.11"
  timeout          = 30

  environment {
    variables = {
      S3_BUCKET      = aws_s3_bucket.images.id
      DYNAMODB_TABLE = aws_dynamodb_table.images.name
    }
  }
}

# Lambda: processImage
resource "aws_lambda_function" "process_image" {
  filename         = data.archive_file.process_image.output_path
  source_code_hash = data.archive_file.process_image.output_base64sha256
  function_name    = "${var.project_name}-processImage-${var.environment}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "process_image.lambda_handler"
  runtime          = "python3.11"
  timeout          = 60

  environment {
    variables = {
      S3_BUCKET      = aws_s3_bucket.images.id
      DYNAMODB_TABLE = aws_dynamodb_table.images.name
    }
  }
}

# Lambda: listImages
resource "aws_lambda_function" "list_images" {
  filename         = data.archive_file.list_images.output_path
  source_code_hash = data.archive_file.list_images.output_base64sha256
  function_name    = "${var.project_name}-listImages-${var.environment}"
  role             = aws_iam_role.lambda_role.arn
  handler          = "list_images.lambda_handler"
  runtime          = "python3.11"
  timeout          = 30

  environment {
    variables = {
      S3_BUCKET      = aws_s3_bucket.images.id
      DYNAMODB_TABLE = aws_dynamodb_table.images.name
    }
  }
}

# --------------------------------------------
# S3 Trigger for processImage Lambda
# --------------------------------------------
resource "aws_lambda_permission" "s3_trigger" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.process_image.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.images.arn
}

resource "aws_s3_bucket_notification" "image_upload" {
  bucket = aws_s3_bucket.images.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.process_image.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "uploads/"
  }

  depends_on = [aws_lambda_permission.s3_trigger]
}

# --------------------------------------------
# API Gateway
# --------------------------------------------
resource "aws_apigatewayv2_api" "api" {
  name          = "${var.project_name}-api-${var.environment}"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type"]
  }
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.api.id
  name        = "$default"
  auto_deploy = true
}

# API Gateway -> Lambda integrations
resource "aws_apigatewayv2_integration" "get_upload_url" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.get_upload_url.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_integration" "list_images" {
  api_id                 = aws_apigatewayv2_api.api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.list_images.invoke_arn
  payload_format_version = "2.0"
}

# API Routes
resource "aws_apigatewayv2_route" "get_upload_url" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "POST /api/upload-url"
  target    = "integrations/${aws_apigatewayv2_integration.get_upload_url.id}"
}

resource "aws_apigatewayv2_route" "list_images" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "GET /api/images"
  target    = "integrations/${aws_apigatewayv2_integration.list_images.id}"
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "api_get_upload_url" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_upload_url.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_list_images" {
  statement_id  = "AllowAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.list_images.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.api.execution_arn}/*/*"
}
