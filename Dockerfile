FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies (curl for healthcheck)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 9880

# Start service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9880"]