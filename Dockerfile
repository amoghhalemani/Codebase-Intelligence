# Multi-stage or clean Python slim build
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PORT=5050 \
    HOST=0.0.0.0

# Install system dependencies for git operations and tree-sitter builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency definition and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Pre-index demo_project so the dashboard is ready to explore immediately
RUN python cli.py index demo_project

# Expose Web Dashboard (5050) and optional REST API (8000)
EXPOSE 5050 8000

# Declare persistent storage volume for indexing databases
VOLUME ["/app/.codebase-intelligence"]

# Default command: run visual web dashboard server
CMD ["python", "demo_dashboard/server.py", "--no-browser"]
