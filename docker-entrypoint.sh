#!/bin/bash
set -eou pipefail

USE_GEN="${USE_GENERATE:=true}"

# requirements are installed at runtime instead of during image build
# so that image isn't 6GB+ due to nvidia/torch package sizes
#
# will cause first run to take a long time but subsequent container starts will be fast
if python -m pip show -q py-cord ; then
  printf '****************\nChecking requirements\n****************\n'
else
  printf '****************\nInstalling requirements, this may take some time!\n****************\n'
fi

if [ "$USE_GEN" = "true" ]; then
  pip install -r requirements.txt
else
  # don't use full requirements if user explicitly disabled /generate command
  pip install -r requirements_no_generate.txt
fi

printf '****************\nRequirements satisfied!\n****************\n'

# Copy the default resource and outputs files if they don't exist.
cp -n "/default/resources/messages.csv" "/app/resources/messages.csv"
cp -n "/default/outputs/.keep" "/app/outputs/.keep"

if [ "$USE_GEN" = "true" ]; then
  printf '****************\nChecking for required /generate files/models\n****************\n'
  # Download generate pre-reqs
  python core/setup_generate.py
fi

printf '****************\nStarting Aiyabot\n****************\n'
# Start the app.
python aiya.py
