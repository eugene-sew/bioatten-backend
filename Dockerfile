FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies (no Postgres; add libs for OpenCV/dlib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    cmake \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project
COPY . /app/

# Create a non-root user to run the app
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Collect static files at build time (safe for SQLite)
RUN python manage.py collectstatic --noinput || true

# Copy and configure entrypoint
COPY --chown=appuser:appuser entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

# Use entrypoint to handle migrations and start server
ENTRYPOINT ["/app/entrypoint.sh"]
