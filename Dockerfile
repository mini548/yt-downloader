FROM python:3.11-slim

# Install system dependencies including FFmpeg, curl, unzip, and Deno (official yt-dlp JS challenge engine)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl ca-certificates unzip && \
    curl -fsSL https://deno.land/install.sh | sh && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV DENO_INSTALL="/root/.deno"
ENV PATH="${DENO_INSTALL}/bin:${PATH}"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=10000
EXPOSE 10000

CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"
