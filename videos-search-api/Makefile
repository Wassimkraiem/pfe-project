COMPOSE = docker compose -f docker-compose.local.yml

.PHONY: up down restart logs ps

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

restart: down up

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps
