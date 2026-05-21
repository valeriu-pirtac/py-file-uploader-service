# AI Agent Guidelines & Project Rules

Welcome! This file serves as the centralized **single source of truth** for all AI coding agents (such as Antigravity, Cursor, and Cline) working on the **File Upload Service** repository. 

Adhering strictly to these rules ensures environment isolation, robust architecture, and high code quality.

---

## 1. Environment & Dependency Isolation (Flox)

This project uses **Flox** for project-level isolation and dependency management. To prevent package pollution or version drift, always run commands within the Flox environment.

* **Command Execution**: Always prefix all Python, package-management (e.g., `uv`), or Node.js commands with `flox activate -- ` (or run them within an active `flox activate` interactive shell).
  
  **Correct:**
  ```bash
  flox activate -- python -m pytest
  flox activate -- uv pip install fastapi
  ```

  **Incorrect:**
  ```bash
  python -m pytest
  uv pip install fastapi
  ```

* **Package Auditing**: To view available packages installed in this environment, run:
  ```bash
  flox list
  ```
  *Do not rely on standard `pip list` or `uv pip list` as the source of truth for declared project dependencies.*

---

## 2. Project Architecture (Clean Architecture)

This project follows a strict **Clean Architecture** paradigm to ensure business logic remains isolated, testable, and independent of external systems (databases, APIs, message brokers).

### The Inward Dependency Flow
All code dependencies must flow inwards towards the Domain layer:

$$\text{Presentation} \rightarrow \text{Application} \rightarrow \text{Domain} \leftarrow \text{Infrastructure (via Protocols)}$$

#### A. Presentation Layer
* **Role**: Entry points to the application (FastAPI routers, Django views/controllers, CLI command-line entry points, HTTP schemas, request/response models).
* **Dependencies**: Depends strictly on the *Application* layer. Must never import directly from the *Infrastructure* layer.

#### B. Application Layer
* **Role**: Core application use cases, transaction orchestration, and command/query handlers. It coordinates the execution of business logic.
* **Dependencies**: Depends strictly on the *Domain* layer. Must never import directly from the *Infrastructure* layer.

#### C. Domain Layer
* **Role**: The core business heart of the application containing pure domain entities, business rules, value logic, and **Protocols/Interfaces** (abstractions for external systems).
* **Dependencies**: Has **zero** external dependencies. It must not import from any outer layer (Presentation, Application, or Infrastructure) or external database libraries/ORMs.

#### D. Infrastructure Layer
* **Role**: Technical details and implementations of protocols defined in the Domain/Application layers (e.g., S3/MinIO client wrappers, NATS JetStream event publishers, database repositories, external API clients).
* **Dependencies**: Depends on the *Domain* and *Application* layers via protocols.

---

## 3. Strict Architectural Rules

1. **Dependency Inversion Principle (DIP)**: Outer layers (`Infrastructure`, `Presentation`) can depend on inner layers, but inner layers (`Domain`, `Application`) **must not** depend on outer layers.
2. **Interface Definitions**: Define all repository, storage, and message-bus interfaces inside the `Domain` layer (or `Application` layer if the contract is strictly use-case specific) using Python's `typing.Protocol` or `abc.ABC`.
3. **No Direct Imports of Infrastructure**: Under no circumstances should `Domain` or `Application` import modules or functions from `Infrastructure`.
4. **Runtime Dependency Injection**: Concrete implementations from the `Infrastructure` layer must be injected into the application layers at runtime (e.g., via FastAPI dependency injection or lightweight DI container patterns).
