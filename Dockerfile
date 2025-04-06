# Stage 1: Build
FROM python:3.13-slim as builder
WORKDIR /app
COPY pyproject.toml ./
RUN pip install uv
RUN uv sync

# Stage 2: Production
FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /app /app
COPY src/ /app/src/
CMD ["python", "-m", "tarnfui"]
