python -m venv venv
venv\Scripts\pip.exe install -r requirements.txt

venv\Scripts\python.exe core/setup_generate.py
venv\Scripts\python.exe aiya.py
