resource "aws_ecs_task_definition" "web" {
  family                   = "authentic-rights-api-${var.ENV}-web"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  memory                   = 4096
  cpu                      = 2048
  execution_role_arn       = "arn:aws:iam::534453370017:role/authentic-rights-api-staging-ecs-execution-role"

  ephemeral_storage {
    size_in_gib = 21
  }

  container_definitions = jsonencode([{
    name      = "authentic-rights-web-container-${var.ENV}"
    image     = "534453370017.dkr.ecr.us-east-1.amazonaws.com/authentic_rights_api:${var.ENV == "prod" ? "main" : "staging"}"
    memory    = 4096
    cpu       = 2048
    essential = true

    command = [
      "sh",
      "-c",
      "alembic upgrade head && gunicorn app.app:app -k uvicorn.workers.UvicornWorker -w 5 --bind 0.0.0.0:80 --timeout 120 --graceful-timeout 30 --keep-alive 75"
    ]

    portMappings = [
      {
        containerPort = 80
        hostPort      = 80
        protocol      = "tcp"
      }
    ]

    logConfiguration = {
      "logDriver" = "awslogs",
      "options" = {
        "awslogs-group"             = aws_cloudwatch_log_group.ecs_task_log_group_web.name,
        "awslogs-region"            = var.aws_region,
        "awslogs-stream-prefix"     = "ecs",
        "mode"                      = "non-blocking",
        "max-buffer-size"           = "25m",
        "awslogs-multiline-pattern" = "^(\\{|\\d{4}-\\d{2}-\\d{2})"
      }
    }

    environment = [
      { name = "TASK_REVISION", value = timestamp() }
    ]

    secrets = [
      for name, arn in local.ssm_name_arn_map : {
        name      = element(split("/", name), length(split("/", name)) - 1)
        valueFrom = arn
      }
    ]
  }])

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_cloudwatch_log_group" "ecs_task_log_group_web" {
  name              = "/ecs/logs/authentic-rights-web-${var.ENV}"
  retention_in_days = 14
}

output "web_task_definition_revision" {
  value = aws_ecs_task_definition.web.revision
}