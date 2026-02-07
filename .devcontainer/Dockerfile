# Use Python 3.11 as base image
FROM python:3.11-slim

# Install system dependencies for OCR and PDF processing
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    ghostscript \
    git \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /workspace

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Install additional Python tools for development
RUN pip install black pylint flake8 mypy pytest

# Create non-root user
RUN useradd -m -s /bin/zsh vscode && \
    chown -R vscode:vscode /workspace

# Switch to non-root user
USER vscode

# Set up git configuration (optional, can be overridden by user)
RUN git config --global init.defaultBranch main

# Default command
CMD ["sleep", "infinity"]