FROM python:3.11-slim-bookworm

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 9880

# Start service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9880"]