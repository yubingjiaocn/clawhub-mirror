module "lambda" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "~> 8.0"

  function_name = "${local.name}-api"
  role_name     = "${local.name}-api-${var.region}"
  handler       = "handler.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 512

  publish     = true
  source_path = "${path.module}/../backend"

  environment_variables = {
    TABLE_NAME  = aws_dynamodb_table.this.id
    BUCKET_NAME = module.s3.s3_bucket_id
    REGION      = var.region
    ENVIRONMENT = var.environment
  }

  attach_policy_statements = true
  policy_statements = {
    dynamodb = {
      effect = "Allow"
      actions = [
        "dynamodb:DescribeTable",
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:BatchGetItem",
        "dynamodb:BatchWriteItem",
      ]
      resources = [
        aws_dynamodb_table.this.arn,
        "${aws_dynamodb_table.this.arn}/index/*",
      ]
    }
    s3 = {
      effect = "Allow"
      actions = [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject",
        "s3:HeadObject",
        "s3:ListBucket",
      ]
      resources = [
        module.s3.s3_bucket_arn,
        "${module.s3.s3_bucket_arn}/*",
      ]
    }
  }

  allowed_triggers = {
    apigw = {
      service    = "apigateway"
      source_arn = "${module.api_gateway.api_execution_arn}/*/*"
    }
  }

  tags = local.tags
}
