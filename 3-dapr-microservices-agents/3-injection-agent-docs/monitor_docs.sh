#!/bin/bash

# Configuration
DOCS_FOLDER="docs" # IMPORTANT: Set this to your actual DOCS folder
PYTHON_SCRIPT="load-files-to-db.py" # IMPORTANT: Set this to your Python script's path
LOG_FILE="log/doc_sync_monitor.log" # Log file for events and script output

# Ensure the docs & log directory exists
mkdir -p "$(dirname "$DOCS_FOLDER")"
mkdir -p "$(dirname "$LOG_FILE")"

echo "$(date): Starting file system monitor for $DOCS_FOLDER" | tee -a "$LOG_FILE"

# -m: monitor mode (keep running indefinitely)
# -r: recursive (watch subdirectories)
# -e: event (specify which events to watch for)
#   create: A file/directory was created in the watched directory.
#   modify: A file was modified.
#   close_write: A file opened for writing was closed. (Good for ensuring file is completely written)
#   moved_to: A file was moved into the watched directory.
# --format: Customize output format (optional, but useful for debugging)
#   %w: watched path
#   %f: filename (if event on a file within a directory)
#   %e: event name(s)
inotifywait -m -r -e create,modify,close_write,moved_to \
    --exclude '\.tmp$' \
    --format '%T %w%f %e' --timefmt '%Y-%m-%d %H:%M:%S' \
    "$DOCS_FOLDER" | while read -r datetime path event; do

    echo "$(date): Detected event: $event on $path" | tee -a "$LOG_FILE"

    # You might want to add a small delay to avoid processing partial writes
    # or to debounce rapid changes if multiple events fire for one file save.
    sleep 5

    # Execute your Python script
    echo "$(date): Triggering Python script..." | tee -a "$LOG_FILE"
    python3 "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1
    echo "$(date): Python script finished." | tee -a "$LOG_FILE"

done

echo "$(date): Monitor script exited." | tee -a "$LOG_FILE"
