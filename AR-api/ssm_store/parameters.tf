# SSM parameters for authentic_rights_api (one resource per param, count for optional)

resource "aws_ssm_parameter" "ENV" {
  count = var.ENV != null && var.ENV != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/ENV"
  type  = "String"
  value = var.ENV

}

resource "aws_ssm_parameter" "PROJECT_NAME" {
  count = var.PROJECT_NAME != null && var.PROJECT_NAME != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/PROJECT_NAME"
  type  = "SecureString"
  value = var.PROJECT_NAME

}

resource "aws_ssm_parameter" "FRONTEND_URL" {
  count = var.FRONTEND_URL != null && var.FRONTEND_URL != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/FRONTEND_URL"
  type  = "SecureString"
  value = var.FRONTEND_URL

}

resource "aws_ssm_parameter" "CORS_ORIGINS" {
  count = var.CORS_ORIGINS != null && var.CORS_ORIGINS != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/CORS_ORIGINS"
  type  = "SecureString"
  value = var.CORS_ORIGINS

}

resource "aws_ssm_parameter" "CELERY_BROKER_URL" {
  count = var.CELERY_BROKER_URL != null && var.CELERY_BROKER_URL != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/CELERY_BROKER_URL"
  type  = "SecureString"
  value = var.CELERY_BROKER_URL

}

resource "aws_ssm_parameter" "CELERY_RESULT_BACKEND" {
  count = var.CELERY_RESULT_BACKEND != null && var.CELERY_RESULT_BACKEND != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/CELERY_RESULT_BACKEND"
  type  = "SecureString"
  value = var.CELERY_RESULT_BACKEND

}

resource "aws_ssm_parameter" "DATABASE_URL" {
  count = var.DATABASE_URL != null && var.DATABASE_URL != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/DATABASE_URL"
  type  = "SecureString"
  value = var.DATABASE_URL

}

resource "aws_ssm_parameter" "STRIPE_WEBHOOK_SECRET" {
  count = var.STRIPE_WEBHOOK_SECRET != null ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/STRIPE_WEBHOOK_SECRET"
  type  = "SecureString"
  value = var.STRIPE_WEBHOOK_SECRET
  lifecycle { prevent_destroy = true }
}

resource "aws_ssm_parameter" "STRIPE_SECRET_KEY" {
  count = var.STRIPE_SECRET_KEY != null ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/STRIPE_SECRET_KEY"
  type  = "SecureString"
  value = var.STRIPE_SECRET_KEY
  lifecycle { prevent_destroy = true }
}

resource "aws_ssm_parameter" "STRIPE_PRICE_ID_MONTHLY" {
  count = var.STRIPE_PRICE_ID_MONTHLY != null ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/STRIPE_PRICE_ID_MONTHLY"
  type  = "SecureString"
  value = var.STRIPE_PRICE_ID_MONTHLY
  lifecycle { prevent_destroy = true }
}

resource "aws_ssm_parameter" "STRIPE_PRICE_ID_YEARLY" {
  count = var.STRIPE_PRICE_ID_YEARLY != null ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/STRIPE_PRICE_ID_YEARLY"
  type  = "SecureString"
  value = var.STRIPE_PRICE_ID_YEARLY
  lifecycle { prevent_destroy = true }
}

resource "aws_ssm_parameter" "STRIPE_API_VERSION" {
  count = var.STRIPE_API_VERSION != null ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/STRIPE_API_VERSION"
  type  = "SecureString"
  value = var.STRIPE_API_VERSION
  lifecycle { prevent_destroy = true }
}

resource "aws_ssm_parameter" "CLERK_SECRET_KEY" {
  count = var.CLERK_SECRET_KEY != null && var.CLERK_SECRET_KEY != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/CLERK_SECRET_KEY"
  type  = "SecureString"
  value = var.CLERK_SECRET_KEY

}

resource "aws_ssm_parameter" "CLERK_JWKS_URL" {
  count = var.CLERK_JWKS_URL != null && var.CLERK_JWKS_URL != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/CLERK_JWKS_URL"
  type  = "SecureString"
  value = var.CLERK_JWKS_URL

}

resource "aws_ssm_parameter" "CLERK_SESSION_TOKEN_EXPIRES_IN_SECONDS" {
  count = var.CLERK_SESSION_TOKEN_EXPIRES_IN_SECONDS != null && var.CLERK_SESSION_TOKEN_EXPIRES_IN_SECONDS != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/CLERK_SESSION_TOKEN_EXPIRES_IN_SECONDS"
  type  = "SecureString"
  value = var.CLERK_SESSION_TOKEN_EXPIRES_IN_SECONDS

}

resource "aws_ssm_parameter" "SMTP_HOST" {
  count = var.SMTP_HOST != null && var.SMTP_HOST != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/SMTP_HOST"
  type  = "SecureString"
  value = var.SMTP_HOST

}

resource "aws_ssm_parameter" "SMTP_PORT" {
  count = var.SMTP_PORT != null && var.SMTP_PORT != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/SMTP_PORT"
  type  = "SecureString"
  value = var.SMTP_PORT

}

resource "aws_ssm_parameter" "SMTP_USERNAME" {
  count = var.SMTP_USERNAME != null && var.SMTP_USERNAME != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/SMTP_USERNAME"
  type  = "SecureString"
  value = var.SMTP_USERNAME

}

resource "aws_ssm_parameter" "SMTP_PASSWORD" {
  count = var.SMTP_PASSWORD != null && var.SMTP_PASSWORD != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/SMTP_PASSWORD"
  type  = "SecureString"
  value = var.SMTP_PASSWORD

}

resource "aws_ssm_parameter" "SMTP_REGION" {
  count = var.SMTP_REGION != null && var.SMTP_REGION != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/SMTP_REGION"
  type  = "SecureString"
  value = var.SMTP_REGION

}

resource "aws_ssm_parameter" "SMTP_USE_TLS" {
  count = var.SMTP_USE_TLS != null && var.SMTP_USE_TLS != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/SMTP_USE_TLS"
  type  = "SecureString"
  value = var.SMTP_USE_TLS

}

resource "aws_ssm_parameter" "EMAIL_SENDER" {
  count = var.EMAIL_SENDER != null && var.EMAIL_SENDER != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/EMAIL_SENDER"
  type  = "SecureString"
  value = var.EMAIL_SENDER

}

resource "aws_ssm_parameter" "EMAIL_SENDER_NAME" {
  count = var.EMAIL_SENDER_NAME != null && var.EMAIL_SENDER_NAME != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/EMAIL_SENDER_NAME"
  type  = "SecureString"
  value = var.EMAIL_SENDER_NAME

}

resource "aws_ssm_parameter" "SMS_BASE_URL" {
  count = var.SMS_BASE_URL != null && var.SMS_BASE_URL != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/SMS_BASE_URL"
  type  = "SecureString"
  value = var.SMS_BASE_URL

}

resource "aws_ssm_parameter" "SMS_X_API_KEY" {
  count = var.SMS_X_API_KEY != null && var.SMS_X_API_KEY != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/SMS_X_API_KEY"
  type  = "SecureString"
  value = var.SMS_X_API_KEY

}

resource "aws_ssm_parameter" "SMS_API_KEY" {
  count = var.SMS_API_KEY != null && var.SMS_API_KEY != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/SMS_API_KEY"
  type  = "SecureString"
  value = var.SMS_API_KEY

}

resource "aws_ssm_parameter" "STARTUP_ENABLE_DDB_CHECK" {
  count = var.STARTUP_ENABLE_DDB_CHECK != null && var.STARTUP_ENABLE_DDB_CHECK != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/STARTUP_ENABLE_DDB_CHECK"
  type  = "SecureString"
  value = var.STARTUP_ENABLE_DDB_CHECK

}

resource "aws_ssm_parameter" "DDB_TABLE_NAME" {
  count = var.DDB_TABLE_NAME != null && var.DDB_TABLE_NAME != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/DDB_TABLE_NAME"
  type  = "SecureString"
  value = var.DDB_TABLE_NAME

}

resource "aws_ssm_parameter" "DDB_REGION" {
  count = var.DDB_REGION != null && var.DDB_REGION != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/DDB_REGION"
  type  = "SecureString"
  value = var.DDB_REGION

}

resource "aws_ssm_parameter" "CANTO_AUTH_URL" {
  count = var.CANTO_AUTH_URL != null && var.CANTO_AUTH_URL != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/CANTO_AUTH_URL"
  type  = "SecureString"
  value = var.CANTO_AUTH_URL

}

resource "aws_ssm_parameter" "CANTO_APP_ID" {
  count = var.CANTO_APP_ID != null && var.CANTO_APP_ID != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/CANTO_APP_ID"
  type  = "SecureString"
  value = var.CANTO_APP_ID

}

resource "aws_ssm_parameter" "CANTO_APP_SECRET" {
  count = var.CANTO_APP_SECRET != null && var.CANTO_APP_SECRET != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/CANTO_APP_SECRET"
  type  = "SecureString"
  value = var.CANTO_APP_SECRET

}

resource "aws_ssm_parameter" "SENTRY_DSN" {
  count = var.SENTRY_DSN != null && var.SENTRY_DSN != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/SENTRY_DSN"
  type  = "SecureString"
  value = var.SENTRY_DSN

}

resource "aws_ssm_parameter" "SLACK_WEBHOOK_URL" {
  count = var.SLACK_WEBHOOK_URL != null && var.SLACK_WEBHOOK_URL != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/SLACK_WEBHOOK_URL"
  type  = "SecureString"
  value = var.SLACK_WEBHOOK_URL

}

resource "aws_ssm_parameter" "owner" {
  count = var.owner != null && var.owner != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/owner"
  type  = "String"
  value = var.owner

}

resource "aws_ssm_parameter" "cost_center" {
  count = var.cost_center != null && var.cost_center != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/cost_center"
  type  = "String"
  value = var.cost_center

}

resource "aws_ssm_parameter" "ecr_repository_name" {
  count = var.ecr_repository_name != null && var.ecr_repository_name != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/ecr_repository_name"
  type  = "String"
  value = var.ecr_repository_name

}

resource "aws_ssm_parameter" "image_tag" {
  count = var.image_tag != null && var.image_tag != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/image_tag"
  type  = "String"
  value = var.image_tag

}

resource "aws_ssm_parameter" "deploy_app_services" {
  count = var.deploy_app_services != null && var.deploy_app_services != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/deploy_app_services"
  type  = "String"
  value = tostring(var.deploy_app_services)

}

resource "aws_ssm_parameter" "db_name" {
  count = var.db_name != null && var.db_name != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/db_name"
  type  = "SecureString"
  value = var.db_name

}

resource "aws_ssm_parameter" "db_username" {
  count = var.db_username != null && var.db_username != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/db_username"
  type  = "SecureString"
  value = var.db_username

}

resource "aws_ssm_parameter" "db_password" {
  count = var.db_password != null && var.db_password != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/db_password"
  type  = "SecureString"
  value = var.db_password

}

resource "aws_ssm_parameter" "rds_instance_class" {
  count = var.rds_instance_class != null && var.rds_instance_class != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/rds_instance_class"
  type  = "String"
  value = var.rds_instance_class

}

resource "aws_ssm_parameter" "redis_node_type" {
  count = var.redis_node_type != null && var.redis_node_type != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/redis_node_type"
  type  = "String"
  value = var.redis_node_type

}

resource "aws_ssm_parameter" "worker_runtime" {
  count = var.worker_runtime != null && var.worker_runtime != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/worker_runtime"
  type  = "String"
  value = var.worker_runtime

}

resource "aws_ssm_parameter" "alarm_email" {
  count = var.alarm_email != null && var.alarm_email != "" ? 1 : 0
  name  = "/bviral/authentic_rights_api/${var.ENV}/alarm_email"
  type  = "String"
  value = var.alarm_email

}
