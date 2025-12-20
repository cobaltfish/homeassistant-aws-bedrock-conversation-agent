PYTHON ?= python3
VENV ?= .venv

# Extract version from custom_components/bedrock_conversation/manifest.json
VERSION := $(shell grep -o '"version": "[^"]*"' custom_components/bedrock_conversation/manifest.json | cut -d'"' -f4)
TAG := v$(VERSION)

.PHONY: help venv deps test lint format typecheck clean release

help: ## Show this help message
	@printf "AWS Bedrock Conversation for Home Assistant\n"
	@printf "Usage: make [target]\n\n"
	@printf "Available targets:\n"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | \
		sed -E 's/^([a-zA-Z0-9_-]+):.*?## (.*)$$/  \1\t\2/'

venv: ## Create Python virtual environment
	$(PYTHON) -m venv $(VENV)
	. $(VENV)/bin/activate && pip install --upgrade pip

deps: venv ## Install all dependencies (dev + test)
	. $(VENV)/bin/activate && pip install -r requirements-test.txt
	@printf "\n✅ Dependencies installed\n"

test: deps ## Run unit tests with coverage
	@printf "🧪 Running tests...\n"
	. $(VENV)/bin/activate && pytest tests/ --cov=custom_components.bedrock_conversation --cov-report=term-missing --cov-report=html
	@printf "\n✅ Tests complete. Coverage report: htmlcov/index.html\n"

lint: deps ## Run linting checks
	@printf "🔍 Running linters...\n"
	. $(VENV)/bin/activate && ruff check custom_components/ tests/ || true
	. $(VENV)/bin/activate && flake8 custom_components/ tests/ --max-line-length=120 --ignore=E203,W503 || true
	@printf "\n✅ Linting complete\n"

format: deps ## Format code with black and isort
	@printf "✨ Formatting code...\n"
	. $(VENV)/bin/activate && black custom_components/ tests/
	. $(VENV)/bin/activate && isort custom_components/ tests/
	@printf "\n✅ Code formatted\n"

typecheck: deps ## Run type checking with mypy
	@printf "🔎 Type checking...\n"
	. $(VENV)/bin/activate && mypy custom_components/ --ignore-missing-imports || true
	@printf "\n✅ Type checking complete\n"

clean: ## Clean build artifacts and cache
	@printf "🧹 Cleaning...\n"
	rm -rf $(VENV)
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	@printf "\n✅ Cleaned\n"

release: test ## Tag and create release (VERSION from manifest.json)
	@if [ -z "$(VERSION)" ]; then \
		echo "❌ ERROR: Could not determine version from manifest.json"; \
		exit 1; \
	fi
	@if ! git diff --quiet || ! git diff --cached --quiet; then \
		echo "❌ ERROR: Working tree not clean; commit changes before releasing"; \
		exit 1; \
	fi
	@if git rev-parse "$(TAG)" >/dev/null 2>&1; then \
		echo "❌ ERROR: Tag $(TAG) already exists"; \
		exit 1; \
	fi
	@printf "📦 Creating release $(TAG)...\\n"
	@git tag -a "$(TAG)" -m "Release $(TAG)"
	@git push origin "$(TAG)"
	@printf "\\n✅ Git tag $(TAG) created and pushed.\\n"
	@if command -v gh >/dev/null 2>&1; then \
		printf "\\n📦 Creating GitHub release with gh for $(TAG)...\\n"; \
		gh release create "$(TAG)" --verify-tag --title "$(TAG)" --notes "Release $(TAG)"; \
		printf "\\n✅ GitHub release $(TAG) created.\\n"; \
	else \
		printf "\\n⚠️ gh CLI not found; skipped GitHub release creation.\\n"; \
	fi
	@printf "\\nNext steps:\\n"
	@printf "  1. Review the GitHub release for $(TAG) and adjust notes if needed\\n"
	@printf "  2. Submit to HACS\\n"

version: ## Show current version
	@printf "Current version: $(VERSION)\n"
	@printf "Release tag: $(TAG)\n"
