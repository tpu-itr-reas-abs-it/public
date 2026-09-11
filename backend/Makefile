.PHONY: up down logs migrate seed revision dev test db-clean db-reset

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f app worker

migrate:
	docker compose run --rm app migrate

seed:
	docker compose run --rm app seed

revision:
	@test -n "$(m)" || { echo 'нужно описание: make revision m="add task priority"'; exit 1; }
	docker compose run --rm -v "$(CURDIR)/alembic/versions:/app/alembic/versions" app \
		alembic revision --autogenerate -m "$(m)"

db-clean:
	@printf 'Удалить ВСЕ записи из таблиц? Отменить будет нельзя. [y/N] ' \
		&& read ans && [ "$$ans" = "y" ] || { echo 'отменено'; exit 1; }
	docker compose exec -T db psql -U puc -d puc -v ON_ERROR_STOP=1 -c \
		"TRUNCATE users, projects, project_members, tasks, task_dependencies, \
		 comments, notifications RESTART IDENTITY CASCADE;"
	@echo 'таблицы очищены'

db-reset:
	@printf 'Удалить тома БД и Redis вместе со всеми данными? [y/N] ' \
		&& read ans && [ "$$ans" = "y" ] || { echo 'отменено'; exit 1; }
	docker compose down -v
	docker compose up -d db redis
	docker compose run --rm app migrate
	@echo 'база пересоздана; демо-данные — make seed'

dev:
	.venv/bin/uvicorn app.main:app --reload

test:
	.venv/bin/pytest -q
