FROM python:3.11-slim

# Install system dependencies including FFmpeg, curl, unzip, Deno, and bgutil-pot (Rust PO Token server)
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg curl ca-certificates unzip && \
    curl -fsSL https://deno.land/install.sh | sh && \
    curl -fsSL -o /usr/local/bin/bgutil-pot https://github.com/jim60105/bgutil-ytdlp-pot-provider-rs/releases/download/v0.8.1/bgutil-pot-linux-x86_64 && \
    chmod +x /usr/local/bin/bgutil-pot && \
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

CMD sh -c "bgutil-pot server & uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"
