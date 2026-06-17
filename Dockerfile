FROM python:3.10-slim

# Install system dependencies needed for scientific packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    gfortran \
    libopenblas-dev \
    libblas-dev \
    liblapack-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt ./

# Upgrade pip and install requirements
RUN python -m pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app

ENV PYTHONUNBUFFERED=1

# Expose port (app uses 8000 by default via gunicorn)
EXPOSE 8000

# Use gunicorn to serve the Flask app defined in wsgi.py
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8000", "wsgi:app"]
