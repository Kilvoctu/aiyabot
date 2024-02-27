#!/bin/bash
set -eou pipefail

# requirements are installed at runtime instead of during image build
# so that image isn't 6GB+ due to nvidia/torch package sizes
#
# will cause first run to take a long time but subsequent container starts will be fast
if python -m pip show -q py-cord ; then
  printf '****************\nChecking requirements\n****************\n'
else
  printf '****************\nInstalling requirements, this may take some time!\n****************\n'
fi
pip install -r requirements.txt

printf '****************\nRequirements satisfied!\n****************\n'

# Copy the default resource and outputs files if they don't exist.
cp -n "/default/resources/messages.csv" "/app/resources/messages.csv"
cp -n "/default/outputs/.keep" "/app/outputs/.keep"

printf '****************\nChecking for required /generate files/models\n****************\n'
# Download generate pre-reqs
python core/setup_generate.py

printf '****************\nStarting Aiyabot\n****************\n'
# Start the app.
python aiya.py
