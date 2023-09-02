import urllib.request
import os

model_folder = "core/DistilGPT2-Stable-Diffusion-V2"
os.makedirs(model_folder, exist_ok=True)

base_url = "https://huggingface.co/FredZhang7/distilgpt2-stable-diffusion-v2/resolve/main/"

files_to_download = ["config.json", "pytorch_model.bin", "tokenizer.json", "training_args.bin"]

for file in files_to_download:
    filepath = os.path.join(model_folder, file)
    if not os.path.isfile(filepath):
        print(f"Missing file for /generate. Downloading {file}")
        urllib.request.urlretrieve(base_url + file, filepath)
