.PHONY: help install run test lint format clean docker-build docker-run

help:
	@echo "Driver Insight Agent - Available Commands:"
	@echo ""
	@echo "  make install      - Install dependencies"
	@echo "  make run          - Run the application"
	@echo "  make run-mcp      - Run the MCP Tool Server"
	@echo "  make test         - Run tests"
	@echo "  make test-cov     - Run tests with coverage"
	@echo "  make lint         - Run linters"
	@echo "  make format       - Format code"
	@echo "  make clean        - Clean up generated files"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run with Docker Compose"
	@echo "  make docker-down  - Stop Docker containers"

install:
	pip install -r requirements.txt

run:
	python app.py

run-mcp:
	cd mcp_tool_server && python app.py

test:
	pytest

test-cov:
	pytest --cov=. --cov-report=html --cov-report=term

lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --max-complexity=10 --max-line-length=127 --statistics
	mypy . --ignore-missing-imports

format:
	black .
	isort .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete

docker-build:
	docker-compose build

docker-run:
	docker-compose up

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f driver-insight-agent

setup:
	bash setup.sh

dev:
	uvicorn app:app --reload --host 0.0.0.0 --port 8080
