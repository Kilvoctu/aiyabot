import urllib.request
import os

model_folder = "core/MagicPrompt-SD"
os.makedirs(model_folder, exist_ok=True)

base_url = "https://huggingface.co/Gustavosta/MagicPrompt-Stable-Diffusion/resolve/main/"

files_to_download = ["config.json", "merges.txt", "pytorch_model.bin", "vocab.json"]

for file in files_to_download:
    filepath = os.path.join(model_folder, file)
    if not os.path.isfile(filepath):
        print(f"Missing file for /generate. Downloading {file}")
        urllib.request.urlretrieve(base_url + file, filepath)
    