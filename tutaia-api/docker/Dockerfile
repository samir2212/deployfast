FROM python:3.12-slim

# Install system dependencies
# docker-cli: for pushing images to ECR
# curl: for installing nixpacks
RUN apt-get update && apt-get install -y \
    docker.io \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Nixpacks
RUN curl -sSL https://nixpacks.com/install.sh | bash

# Verify installations
RUN nixpacks --version
RUN docker --version

WORKDIR /app

# Install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Non-root user for security
RUN useradd -m -u 1000 tutaia && chown -R tutaia:tutaia /app

# Docker socket access - needed to run docker build/push
# The container needs access to the host Docker socket
RUN usermod -aG docker tutaia

USER tutaia

EXPOSE 3000

# Production: use uvicorn with multiple workers
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "3000", \
     "--workers", "2", \
     "--log-level", "info"]
