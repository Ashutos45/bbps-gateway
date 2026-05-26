FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port (metadata only)
EXPOSE 8000

# Enable Docker health check using standard python urllib
HEALTHCHECK --interval=30s --timeout=15s --start-period=30s --retries=3 \
  CMD python -c "import os, urllib.request; port = os.environ.get('PORT', '8000'); urllib.request.urlopen(f'http://localhost:{port}/health')" || exit 1

# Command to execute database initialization and run the app
CMD python init_db.py && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
