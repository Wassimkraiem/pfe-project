COMPOSE = docker compose -f docker-compose.local.yml

.PHONY: up down restart logs ps test-search-eval

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

restart: down up

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

test-search-eval:
	python -m pytest -q test_search_accuracy_speed.py -s
