# Use official Python 3.10 slim image — pip is built-in
FROM python:3.10-slim

# Install FFmpeg (needed for Reel video generation) + fonts
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fontconfig \
    fonts-dejavu-core \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Create necessary data directories
RUN mkdir -p backend/data \
    backend/assets/generated \
    backend/assets/thumbnails \
    backend/assets/music \
    backend/assets/fonts

# Expose port (Railway sets PORT env var dynamically)
EXPOSE 8000

# Start the API server (scheduler runs inside it)
CMD ["python", "backend/api_server.py"]
