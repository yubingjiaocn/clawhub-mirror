module "api_gateway" {
  source  = "terraform-aws-modules/apigateway-v2/aws"
  version = "~> 6.0"

  name          = local.name
  description   = "ClawHub Enterprise Registry API"
  protocol_type = "HTTP"

  create_domain_name = false

  cors_configuration = {
    allow_headers = ["*"]
    allow_methods = ["*"]
    allow_origins = ["*"]
  }

  routes = {
    "ANY /" = {
      integration = {
        uri                    = module.lambda.lambda_function_arn
        payload_format_version = "2.0"
      }
    }
    "ANY /{proxy+}" = {
      integration = {
        uri                    = module.lambda.lambda_function_arn
        payload_format_version = "2.0"
      }
    }
  }

  tags = local.tags
}
