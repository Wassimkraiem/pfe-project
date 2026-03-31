variable "aws_region" {
  description = "The AWS region to create resources in."
  type        = string
  default     = "us-east-1"
}

variable "ENV" {
  description = "Deployment environment (e.g., staging, prod)"
  type        = string
  default     = "staging"
}

variable "PROJECT_NAME" {
  type     = string
  nullable = true
  default  = null
}

variable "FRONTEND_URL" {
  type     = string
  nullable = true
  default  = null
}

variable "CORS_ORIGINS" {
  type     = string
  nullable = true
  default  = null
}

variable "CELERY_BROKER_URL" {
  type     = string
  nullable = true
  default  = null
}

variable "CELERY_RESULT_BACKEND" {
  type     = string
  nullable = true
  default  = null
}

variable "DATABASE_URL" {
  type     = string
  nullable = true
  default  = null
}

variable "STRIPE_WEBHOOK_SECRET" {
  type     = string
  nullable = true
  default  = null
}

variable "STRIPE_SECRET_KEY" {
  type     = string
  nullable = true
  default  = null
}

variable "STRIPE_PRICE_ID_MONTHLY" {
  type     = string
  nullable = true
  default  = null
}

variable "STRIPE_PRICE_ID_YEARLY" {
  type     = string
  nullable = true
  default  = null
}

variable "STRIPE_API_VERSION" {
  type     = string
  nullable = true
  default  = null
}

variable "CLERK_SECRET_KEY" {
  type     = string
  nullable = true
  default  = null
}

variable "CLERK_JWKS_URL" {
  type     = string
  nullable = true
  default  = null
}

variable "CLERK_SESSION_TOKEN_EXPIRES_IN_SECONDS" {
  type     = string
  nullable = true
  default  = null
}

variable "SMTP_HOST" {
  type     = string
  nullable = true
  default  = null
}

variable "SMTP_PORT" {
  type     = string
  nullable = true
  default  = null
}

variable "SMTP_USERNAME" {
  type     = string
  nullable = true
  default  = null
}

variable "SMTP_PASSWORD" {
  type     = string
  nullable = true
  default  = null
}

variable "SMTP_REGION" {
  type     = string
  nullable = true
  default  = null
}

variable "SMTP_USE_TLS" {
  type     = string
  nullable = true
  default  = null
}

variable "EMAIL_SENDER" {
  type     = string
  nullable = true
  default  = null
}

variable "EMAIL_SENDER_NAME" {
  type     = string
  nullable = true
  default  = null
}

variable "SMS_BASE_URL" {
  type     = string
  nullable = true
  default  = null
}

variable "SMS_X_API_KEY" {
  type     = string
  nullable = true
  default  = null
}

variable "SMS_API_KEY" {
  type     = string
  nullable = true
  default  = null
}

variable "STARTUP_ENABLE_DDB_CHECK" {
  type     = string
  nullable = true
  default  = null
}

variable "DDB_TABLE_NAME" {
  type     = string
  nullable = true
  default  = null
}

variable "DDB_REGION" {
  type     = string
  nullable = true
  default  = null
}

variable "CANTO_AUTH_URL" {
  type     = string
  nullable = true
  default  = null
}

variable "CANTO_APP_ID" {
  type     = string
  nullable = true
  default  = null
}

variable "CANTO_APP_SECRET" {
  type     = string
  nullable = true
  default  = null
}

variable "SENTRY_DSN" {
  type     = string
  nullable = true
  default  = null
}

variable "SLACK_WEBHOOK_URL" {
  type     = string
  nullable = true
  default  = null
}

# Infra / tagging (optional; not all stored as SSM)
variable "owner" {
  type     = string
  nullable = true
  default  = null
}

variable "cost_center" {
  type     = string
  nullable = true
  default  = null
}

variable "ecr_repository_name" {
  type     = string
  nullable = true
  default  = null
}

variable "image_tag" {
  type     = string
  nullable = true
  default  = null
}

variable "deploy_app_services" {
  type    = bool
  default = true # when not set, keep existing param (avoid destroy)
}

variable "db_name" {
  type     = string
  nullable = true
  default  = null
}

variable "db_username" {
  type     = string
  nullable = true
  default  = null
}

variable "db_password" {
  type     = string
  nullable = true
  default  = null
}

variable "rds_instance_class" {
  type     = string
  nullable = true
  default  = null
}

variable "redis_node_type" {
  type     = string
  nullable = true
  default  = null
}

variable "worker_runtime" {
  type     = string
  nullable = true
  default  = null
}

variable "alarm_email" {
  type     = string
  nullable = true
  default  = null
}
