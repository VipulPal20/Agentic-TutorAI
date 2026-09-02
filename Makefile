# Convenience targets for local development.
.PHONY: install lint fmt test run ingest up down logs web web-install web-build

# ---- Backend ----
install:
	pip install -r requirements-dev.txt

lint:
	ruff check .

fmt:
	ruff format .
	ruff check --fix .

test:
	pytest

run:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

ingest:
	python -m database.ingest --path data/sample_docs

# ---- Frontend ----
web-install:
	cd frontend && npm install

web:
	cd frontend && npm run dev

web-build:
	cd frontend && npm run build

# ---- Docker (db + api + web) ----
up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f api web
