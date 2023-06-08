#!/bin/bash
set -eou pipefail

# Copy the default resource and outputs files if they don't exist.
cp -n "/default/resources/messages.csv" "/app/resources/messages.csv"
cp -n "/default/outputs/.keep" "/app/outputs/.keep"

# Download generate pre-reqs
python core/setup_generate.py
# Start the app.
python aiya.py
