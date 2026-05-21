# File Uploader Service

A production-ready **FastAPI** file uploader service built on **Clean Architecture** (Hexagonal Architecture) principles.

---

## Features

- **FastAPI** - modern async web framework with automatic OpenAPI docs
- **Clean Architecture** - strict dependency rules between all layers
- **Pydantic Settings** - type-safe, environment-driven configuration with `.env` support
- **Structlog** - structured JSON logging (or pretty console for development)
- **Prometheus** - metrics via `prometheus-fastapi-instrumentator`
- **CORS + Request Logging** - middleware wired at startup via FastAPI lifespan
- **Global Exception Handling** - domain and application errors mapped to HTTP responses
- **Mypy** strict mode type checking
- **Ruff** linting and auto-formatting
- **Pytest** with unit, integration, and e2e test suites and coverage reporting
- **GitHub Actions** CI pipeline (lint, type-check, test)
- **MkDocs Material** documentation site
- **uv** fast dependency management with lock file
- **flox** reproducible developer environment

## Project Structure

```md
py-file-uploader-service/
│
├── src/
│   ├── application/                    # Use-case orchestration layer
│   │   ├── dtos/                       # Data Transfer Objects
│   │   ├── exceptions.py               # Application-layer exceptions
│   │   ├── ports/                      # Additional application interfaces
│   │   ├── services/                   # Application services
│   │   └── use_cases/                  # Use case implementations
│   ├── configuration/                  # Settings and dependency injection
│   │   ├── dependencies.py             # FastAPI Depends() wiring
│   │   └── settings.py                 # Pydantic BaseSettings (env-driven)
│   ├── domain/                         # Pure business logic (no framework deps)
│   │   ├── entities/                   # Domain entities (identity + lifecycle)
│   │   ├── exceptions.py               # Domain exception hierarchy
│   │   ├── protocols/                  # Abstract interfaces for infrastructure
│   │   ├── services/                   # Domain services (stateless logic)
│   │   └── value_objects/              # Immutable value types
│   ├── infrastructure/                 # External service adapters
│   ├── observability/                  # Logging and metrics setup
│   │   ├── logging.py                  # structlog JSON configuration
│   │   └── metrics.py                  # Prometheus metrics registration
│   └── presentation/                   # FastAPI HTTP interface
│       ├── main.py                     # App factory + lifespan + middleware
│       └── api/
│           ├── middleware/
│           │   ├── error_handler.py    # Domain -> HTTP error mapping
│           │   └── request_logging.py  # Per-request structured logging
│           └── v1/
│               ├── routers/
│               │   ├── health.py       # GET /v1/health
│               │   └── index.py        # GET /v1/
│               └── schemas/            # Pydantic request/response models
├── tests/
│   ├── conftest.py                     # Shared fixtures (TestClient, settings)
│   ├── e2e/                            # Full API workflow tests
│   ├── integration/                    # Infrastructure tests (real services)
│   └── unit/                           # Domain + application unit tests
│       ├── application/
│       ├── configuration/
│       ├── domain/
│       ├── observability/
│       └── presentation/
├── docs/                               # MkDocs documentation source
├── .github/workflows/ci.yml            # GitHub Actions CI pipeline
├── .env.example                        # Environment variable reference
├── Makefile                            # Developer workflow automation
├── pyproject.toml                      # Project manifest and dependencies
├── ruff.toml                           # Ruff linter/formatter config
├── mypy.ini                            # Mypy strict type-checking config
└── pytest.ini                          # Pytest + coverage config
```

## Architecture

This template follows **Clean Architecture** (Hexagonal / Ports and Adapters).

> **Dependencies always point inward.** The domain knows nothing about infrastructure or the web framework.

| Layer              | Responsibility                      | Depends On                   |
| ------------------ | ----------------------------------- | ---------------------------- |
| **Domain**         | Business rules, entities, protocols | Nothing                      |
| **Application**    | Use case orchestration              | Domain                       |
| **Infrastructure** | DB, HTTP, queue adapters            | Domain protocols             |
| **Presentation**   | HTTP routing, serialization         | Application + Infrastructure |
| **Configuration**  | Settings, DI wiring                 | All layers                   |

## Getting Started

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) - fast package manager
- [flox](https://flox.dev/) - reproducible dev environment (optional)

### Setup

```bash
make setup
cp .env.example .env
```

### Development Server

```bash
make dev         # auto-reload on http://localhost:8000
make dev-debug   # with debug logging
```

### Endpoints

- **API root**: http://localhost:8000/v1/
- **Health**: http://localhost:8000/v1/health
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Metrics**: http://localhost:8000/metrics

### Configuration

Copy `.env.example` to `.env` and adjust as needed:

| Variable          | Default                   | Description                               |
| ----------------- | ------------------------- | ----------------------------------------- |
| `APP_NAME`        | `file-uploader-service` | Application Name                          |
| `APP_ENV`         | `dev`                     | Environment (dev / test / staging / prod) |
| `LOG_LEVEL`       | `INFO`                    | DEBUG / INFO / WARNING / ERROR / CRITICAL |
| `LOG_FORMAT`      | `json`                    | `json` or `console`                       |
| `METRICS_ENABLED` | `true`                    | Enable Prometheus `/metrics`              |
| `HOST`            | `0.0.0.0`                 | Server bind address                       |
| `PORT`            | `8000`                    | Server bind port                          |
| `WORKERS`         | `1`                       | uvicorn worker processes                  |

### Development Workflow

```bash
# Help Message
make help                  # Show this help message

# Setup & Installation
make setup                 # Initialize project: create venv, install dependencies
make install               # Install/sync dependencies (after pyproject.toml changes)
make install-dev           # Install with dev dependencies

# Code Quality
make lint                  # Run ruff linter
make format                # Format code with ruff
make format-check          # Check code formatting without modifying files
make type-check            # Run mypy type checker
make check                 # Run all code quality checks (format, lint, type)

# Testing
make test                  # Run all tests
make test-unit             # Run unit tests
make test-integration      # Run integration tests
make test-e2e              # Run end-to-end tests
make test-coverage         # Run tests with coverage report
make test-watch            # Run tests in watch mode

# Development
make dev                   # Start development server with auto-reload
make dev-debug             # Start development server with debug logging
make shell                 # Start Python shell with project context

# Documentation
make docs                  # Build documentation with MkDocs
make docs-serve            # Serve documentation locally at http://127.0.0.1:8000

# Cleanup
make clean                 # Remove build artifacts, cache files, and venv
make clean-cache           # Remove only cache files (keep venv)

# Utilities
make info                  # Display project information
make deps-outdated         # Check for outdated dependencies
make lock                  # Regenerate uv.lock file

# CI/CD Pipeline
make ci                    # Run full CI pipeline (clean, check, test)
make ci-coverage           # Run CI with coverage report
```

### License

[MIT](LICENSE)
