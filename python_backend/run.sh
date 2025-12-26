#!/bin/bash

# ==========================================
# AI Desk Avatar Backend Launcher
# ==========================================

# Directory setup
BASE_DIR=$(dirname "$(readlink -f "$0")")
cd "$BASE_DIR" || exit 1

# Configuration
LOG_FILE="$BASE_DIR/server.log"
PORT=8000
HOST="0.0.0.0"

# Timestamp function for logging

timestamp() {
    date "+%Y-%m-%d %H:%M:%S"
}

echo "[$(timestamp)] Starting AI Avatar Backend..." >> "$LOG_FILE"
echo "[$(timestamp)] Working Directory: $BASE_DIR" >> "$LOG_FILE"

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo "[$(timestamp)] Error: Poetry is not installed or not in PATH." | tee -a "$LOG_FILE"
    exit 1
fi

# Rotate log if it gets too big (approx 10MB)
if [ -f "$LOG_FILE" ] && [ $(stat -c%s "$LOG_FILE") -ge 10485760 ]; then
    mv "$LOG_FILE" "$LOG_FILE.old"
    echo "[$(timestamp)] Log rotated." >> "$LOG_FILE"
fi

# Run the server
# We use 'exec' so the process ID of shell becomes the process ID of python
# This allows systemd to control the uvicorn process correctly
echo "[$(timestamp)] Launching Uvicorn on port $PORT..." >> "$LOG_FILE"

# Redirect both stdout (1) and stderr (2) to the log file
exec poetry run uvicorn app:app --host "$HOST" --port "$PORT" --reload >> "$LOG_FILE" 2>&1


# poetry run uvicorn app:app --reload --port 8000