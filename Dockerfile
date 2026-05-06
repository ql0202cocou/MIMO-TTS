FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies (curl for healthcheck)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -r -s /bin/false appuser

# Install Python dependencies (production only)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Set ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 9880

# Security labels
LABEL maintainer="MIMO-TTS Team"
LABEL security.capabilities="NET_BIND_SERVICE"

# Start service with request size limit
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9880", "--limit-max-request-size", "1048576"]
