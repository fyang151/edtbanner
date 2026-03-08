# outputs.tf - Values displayed after terraform apply

output "api_url" {
  description = "API Gateway URL"
  value       = aws_apigatewayv2_api.api.api_endpoint
}

output "s3_bucket" {
  description = "S3 bucket name for images"
  value       = aws_s3_bucket.images.id
}

output "dynamodb_table" {
  description = "DynamoDB table name"
  value       = aws_dynamodb_table.images.name
}

output "upload_url_endpoint" {
  description = "Endpoint to get upload URL"
  value       = "${aws_apigatewayv2_api.api.api_endpoint}/api/upload-url"
}

output "list_images_endpoint" {
  description = "Endpoint to list images"
  value       = "${aws_apigatewayv2_api.api.api_endpoint}/api/images"
}
