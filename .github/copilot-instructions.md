My requirements document is located here: #file:Design.md. Update it as the implementation progresses, and feel free to add items for remaining tasks or potential improvements.

# Prompt for GitHub Copilot: Initializing a Modern Python Project

## Objective

Generate the base structure and initial configuration files for a new Python project. This project emphasizes modern dependency management, quality tooling, containerized development, deployment via Docker/Helm/Kubernetes, CI/CD automation with GitHub Actions, systematic unit testing, and a focus on memory efficiency.

## Technical Specifications

1. **Language:** Python (latest stable version or specify if needed, e.g., 3.13+)
2. **Dependency Management:** Use `uv` for dependency installation and management.
    * Generate an initial `pyproject.toml` file configured for `uv`.
    * Include `ruff` as a development dependency.
    * Include `pytest` as a development dependency for testing.
    * Add placeholders for production dependencies.
3. **Code Quality (Linting & Formatting):** Use `ruff` for formatting and linting.
    * Configure `ruff` in `pyproject.toml` with reasonable default rules (e.g., enable default rules, isort, flake8).
    * Configure `ruff format`.
4. **Development Environment:** VS Code Dev Container.
    * Create a `.devcontainer` directory.
    * Generate a `.devcontainer/devcontainer.json` file configured for Python, using an appropriate base image (e.g., `mcr.microsoft.com/devcontainers/python:3.13`).
    * Configure `devcontainer.json` to automatically install `uv` and `ruff`.
    * Include recommended VS Code extensions (e.g., `ms-python.python`, `ms-azuretools.vscode-docker`, `charliermarsh.ruff`).
    * Configure `postCreateCommand` or `postAttachCommand` if necessary to install dependencies with `uv sync` via `pyproject.toml`.
    * Generate a basic `.devcontainer/Dockerfile` if customizations to the dev image are needed (otherwise, the base image may suffice).
5. **Project Structure:**
    * Use a structure like `src/tarnfui/` for source code.
    * Create a `tests/` directory for unit tests.
    * Include a `.gitignore` file tailored for Python projects and environment files (VSCode, etc.).
    * Create a basic `README.md` with sections for installation, usage, testing, and deployment.
6. **Packaging & Deployment:**
    * **Docker:** Generate a multi-stage `Dockerfile` optimized for production.
        * Use a slim Python base image.
        * Copy only necessary dependencies and source code.
        * Run the application as a non-root user.
        * Account for dependency installation via `uv`.
    * **Helm:** Create a basic Helm chart structure in a `charts/tarnfui/` directory.
        * `Chart.yaml`
        * `values.yaml` (with placeholders for image, tag, replicas, resources, etc.)
        * `templates/deployment.yaml` (using values from `values.yaml`)
        * `templates/service.yaml` (basic)
        * `templates/_helpers.tpl` (if needed)
        * `.helmignore`
7. **Automation (CI/CD):** GitHub Actions.
    * Create a `.github/workflows` directory.
    * Generate a workflow (`ci.yaml`) triggered on `push` (branches `main`/`master`) and `pull_request`. This workflow should:
        * Checkout the code.
        * Setup Python.
        * Install `uv`.
        * Install dependencies (`uv sync --dev`).
        * Run `ruff check .` and `ruff format --check .`.
        * Run unit tests with `pytest`.
    * Generate a workflow (`cd.yaml`) triggered on `push` to the `main` branch (after successful CI). This workflow should (with placeholders for secrets/registries):
        * Build the production Docker image.
        * Tag the Docker image (e.g., with the commit SHA).
        * Push the Docker image to a registry (e.g., GitHub Container Registry - GHCR).
        * Update and publish the Helm chart to a public repository.
8. **Testing:**
    * Require unit tests for every feature.
    * Generate a simple example test file in `tests/` (e.g., `tests/test_example.py`) using `pytest`, which tests a sample function.
    * Create a corresponding example source file (e.g., `src/tarnfui/example.py`).
9. **Performance (Memory Efficiency):**
    * Write code with memory efficiency in mind, especially when handling a large number of objects/resources.
    * Add a comment in the `README.md` or a `CONTRIBUTING.md` file (to be created) mentioning this constraint and suggesting the use of generators, iterators, memory views (`memoryview`), or libraries like `psutil` or memory profilers if needed.
