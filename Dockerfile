# syntax=docker/dockerfile:1

# =============================================================================
# Stage 1 — builder: install dependencies into an isolated virtualenv.
# =============================================================================
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# build-essential covers any dependency that lacks a prebuilt wheel.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt

# =============================================================================
# Stage 2 — runtime: slim image with only the venv + app code, non-root user.
# =============================================================================
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Non-root runtime user.
RUN useradd --create-home --uid 1000 appuser

COPY --from=builder /opt/venv /opt/venv
COPY . .

RUN chmod +x /app/entrypoint.sh && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Container-level health probe hitting the app's /health endpoint.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)" || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
