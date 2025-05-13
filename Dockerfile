# Use an official Python runtime as a parent image
# Using slim-bullseye for a smaller image size. Choose a version compatible with your dependencies.
FROM python:3.10-slim-bullseye

# Set the working directory in the container
WORKDIR /app

# Set environment variables for Hugging Face cache to keep it inside the container (and potentially mountable)
# This helps avoid re-downloading models on every start if a volume is mounted.
ENV HF_HOME=/app/.cache/huggingface
ENV TRANSFORMERS_CACHE=/app/.cache/huggingface/hub
ENV HF_HUB_CACHE=/app/.cache/huggingface/hub

# Prevent Python from writing pyc files to disc (optional)
ENV PYTHONDONTWRITEBYTECODE 1
# Ensure Python output is sent straight to terminal (useful for logs)
ENV PYTHONUNBUFFERED 1

# Install system dependencies that might be needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install pip dependencies
# Copy only requirements first to leverage Docker cache
COPY requirements.txt .
# Make sure pip is up-to-date
RUN pip install --upgrade pip
# Install dependencies, including torch with CUDA support
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Create the cache directory and set permissions
RUN mkdir -p $HF_HOME && chmod -R 777 $HF_HOME
RUN mkdir -p /app/results && chmod -R 777 /app/results

# Create entrypoint script to run main.py
RUN echo '#!/bin/bash\npython main.py "$@"' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Use entrypoint script as the default command
ENTRYPOINT ["/app/entrypoint.sh"]

# Default values for command-line arguments
CMD ["--acordao_file", "data/Acórdão 733 de 2025 Plenário.pdf", "--resumo_file", "data/Acórdão 733-2025 resumos.txt", "--output_dir", "results"] 