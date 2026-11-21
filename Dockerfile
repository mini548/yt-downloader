FROM python:3.11-slim

# Install system dependencies including FFmpeg and Node.js (for yt-dlp JavaScript challenge solver)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl ca-certificates nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose port (Render automatically provides PORT environment variable, defaults to 10000)
ENV PORT=10000
EXPOSE 10000

# Start FastAPI server via Uvicorn with PORT expansion
CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"
