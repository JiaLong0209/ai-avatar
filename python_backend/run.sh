#!/bin/bash

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

# Logging function
log() {
    echo "[$(timestamp)] $1" | tee -a "$LOG_FILE"
}

log "=========================================="
log "Starting AI Avatar Backend..."
log "Working Directory: $BASE_DIR"
log "Log File: $LOG_FILE"
log "=========================================="

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    log "ERROR: Poetry is not installed or not in PATH."
    exit 1
fi

# Check if config.yaml exists
if [ ! -f "$BASE_DIR/config.yaml" ]; then
    log "WARNING: config.yaml not found. Using defaults and environment variables."
fi

# Rotate log if it gets too big (approx 10MB)
if [ -f "$LOG_FILE" ] && [ $(stat -c%s "$LOG_FILE" 2>/dev/null || echo 0) -ge 10485760 ]; then
    mv "$LOG_FILE" "$LOG_FILE.old" 2>/dev/null
    log "Log rotated (previous log saved as $LOG_FILE.old)"
fi

# Run the server
# We use 'exec' so the process ID of shell becomes the process ID of python
# This allows systemd to control the uvicorn process correctly
log "Launching Uvicorn on $HOST:$PORT..."

# Redirect both stdout (1) and stderr (2) to the log file
# This ensures all output is captured for systemd logging
# 只要這樣寫，就會同時在螢幕顯示，並存入 server.log

exec poetry run uvicorn app:app --host "$HOST" --port "$PORT" --reload 2>&1 | tee -a "$LOG_FILE"

# exec poetry run uvicorn app:app --host "$HOST" --port "$PORT" --reload >> "$LOG_FILE" 2>&1
# exec poetry run uvicorn app:app --host "$HOST" --port "$PORT" --reload 2>&1 | tee -a "$LOG_FILE" 1
