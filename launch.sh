#!/bin/bash
python -m venv venv

source ./venv/bin/activate
pip install -r requirements.txt

python core/setup_generate.py
python aiya.py
