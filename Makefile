.PHONY: help dev stop test lint format install-backend install-frontend install-installer clean

COMPOSE := docker compose -f docker-compose.yml -f docker-compose.dev.yml
BACKEND_DIR := platform/backend
FRONTEND_DIR := platform/frontend
INSTALLER_DIR := installer

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

dev: ## Start the development stack
	@test -f .env || cp .env.example .env
	$(COMPOSE) up --build -d
	@echo ""
	@echo "Development stack is starting:"
	@echo "  Backend:  http://localhost:8000"
	@echo "  Frontend: http://localhost:5173"
	@echo "  API docs: http://localhost:8000/docs"
	@echo "  Health:   http://localhost:8000/health"

stop: ## Stop the development stack
	$(COMPOSE) down

logs: ## Tail development stack logs
	$(COMPOSE) logs -f

install-backend: ## Install backend Python dependencies
	cd $(BACKEND_DIR) && python -m pip install -e ".[dev]"

install-frontend: ## Install frontend Node dependencies
	cd $(FRONTEND_DIR) && npm install

install-installer: ## Install installer Python dependencies
	cd $(INSTALLER_DIR) && python -m pip install -e ".[dev]"

install: install-backend install-frontend install-installer ## Install all local dependencies

test: ## Run all tests
	@echo "==> Installer tests"
	cd $(INSTALLER_DIR) && python -m pytest -q
	@echo "==> Backend tests"
	cd $(BACKEND_DIR) && python -m pytest -q
	@echo "==> Frontend tests"
	cd $(FRONTEND_DIR) && npm test -- --run

lint: ## Lint all projects
	@echo "==> Installer lint"
	cd $(INSTALLER_DIR) && python -m ruff check .
	@echo "==> Backend lint"
	cd $(BACKEND_DIR) && python -m ruff check .
	@echo "==> Frontend lint"
	cd $(FRONTEND_DIR) && npm run lint

format: ## Format all projects
	@echo "==> Installer format"
	cd $(INSTALLER_DIR) && python -m ruff format . && python -m ruff check --fix .
	@echo "==> Backend format"
	cd $(BACKEND_DIR) && python -m ruff format . && python -m ruff check --fix .
	@echo "==> Frontend format"
	cd $(FRONTEND_DIR) && npm run format

clean: ## Remove local build artifacts
	$(COMPOSE) down -v --remove-orphans || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(FRONTEND_DIR)/node_modules $(FRONTEND_DIR)/dist $(FRONTEND_DIR)/coverage
