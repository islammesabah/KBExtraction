FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy project files
COPY . .

# Upgrade pip tooling
RUN pip install --upgrade pip setuptools wheel

# Install CPU-only PyTorch first (prevents CUDA downloads)
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies
RUN pip install -r requirements.lock.txt

RUN pip install gunicorn
# Later you can add gunicorn to requirements.in and regenerate requirements.lock.txt. 
# But for “get a demo link working now”, the Dockerfile line is the quickest.

# Create runtime directory for HF cache
RUN mkdir -p /app/runtime/huggingface

# Set Hugging Face cache location
ENV HF_HOME=/app/runtime/huggingface

ENV PYTHONPATH=/app/src

# Expose port required by Hugging Face Spaces
EXPOSE 7860

# Start Flask app via Gunicorn
CMD ["gunicorn", "ui.wsgi:app", "--bind", "0.0.0.0:7860", "--workers", "1", "--timeout", "600"]
