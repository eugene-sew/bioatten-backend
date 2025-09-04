# ------------------------------------------------------------------------------
# Base Image: Use bullseye for better manylinux wheel support
# ------------------------------------------------------------------------------
FROM python:3.11-bullseye AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CMAKE_BUILD_PARALLEL_LEVEL=4 \
    DJANGO_SETTINGS_MODULE=bioattend.settings

WORKDIR /app

# ------------------------------------------------------------------------------
# Install System Dependencies
# ------------------------------------------------------------------------------
# - Install build tools only for compiling dependencies like dlib and pygraphviz
# - Will be cleaned up after pip install to keep image small
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    gcc \
    g++ \
    graphviz \
    graphviz-dev \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libpq-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------------------------
# Install Python dependencies
# ------------------------------------------------------------------------------
COPY deploy_requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install "setuptools==80.9.0" && \
    pip install -r deploy_requirements.txt

# ------------------------------------------------------------------------------
# Copy application code
# ------------------------------------------------------------------------------
COPY . /app/

# ------------------------------------------------------------------------------
# Create non-root user
# ------------------------------------------------------------------------------
RUN groupadd -g 1000 appuser && \
    useradd -m -u 1000 -g appuser appuser && \
    chown -R appuser:appuser /app

USER appuser

# ------------------------------------------------------------------------------
# Collect static files
# ------------------------------------------------------------------------------
RUN python manage.py collectstatic --noinput || true

# ------------------------------------------------------------------------------
# Entrypoint
# ------------------------------------------------------------------------------
COPY --chown=appuser:appuser entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
