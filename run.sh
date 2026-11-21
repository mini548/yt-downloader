#!/bin/bash
echo "======================================================"
echo "   Starting YouTube Downloader Server..."
echo "======================================================"

python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
