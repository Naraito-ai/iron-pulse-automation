# ==========================================
# STAGE 1: Build the Next.js Dashboard
# ==========================================
FROM node:20-alpine AS builder

WORKDIR /app/dashboard
COPY dashboard/package*.json ./
RUN npm install
COPY dashboard/ ./
RUN npm run build

# ==========================================
# STAGE 2: Python Backend (Runs API + Serves Dashboard)
# ==========================================
FROM python:3.10-slim

# Install FFmpeg (needed for Reel video generation) + fonts
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fontconfig \
    fonts-dejavu-core \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the backend code
COPY backend/ ./backend/

# Copy the built dashboard from Stage 1 into the python container
COPY --from=builder /app/dashboard/out /app/dashboard/out

# Create necessary data directories
RUN mkdir -p backend/data \
    backend/assets/generated \
    backend/assets/thumbnails \
    backend/assets/music \
    backend/assets/fonts

# Start the API server (serves the dashboard at / and API at /api)
CMD ["python", "backend/api_server.py"]
