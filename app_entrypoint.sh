#!/bin/sh
set -e

# Check if the FIREBASE_KEY_JSON environment variable is set and not empty
if [ -n "$FIREBASE_KEY_JSON" ] && [ -n "$GOOGLE_APPLICATION_CREDENTIALS" ]; then
  echo "Found Firebase credentials. Writing to file: $GOOGLE_APPLICATION_CREDENTIALS"
  # Take the content of the environment variable and write it to the file path specified by GOOGLE_APPLICATION_CREDENTIALS
  echo "$FIREBASE_KEY_JSON" > "$GOOGLE_APPLICATION_CREDENTIALS"
else
  echo "Firebase credentials not found in environment variables. Skipping file creation."
fi

# The "exec" command will run the command passed to the script as arguments.
# This allows the Dockerfile's CMD to be executed as the main process.
echo "Executing main command: $@"
echo "Running database migrations..."  
   alembic stamp head    
exec "$@"

