output "api_url" {
  description = "API Gateway invoke URL"
  value       = module.api_gateway.stage_invoke_url
}

output "dynamodb_table_name" {
  description = "DynamoDB table name"
  value       = module.dynamodb.dynamodb_table_id
}

output "s3_bucket_name" {
  description = "S3 bucket name for skill archives"
  value       = module.s3.s3_bucket_id
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = module.lambda.lambda_function_name
}
