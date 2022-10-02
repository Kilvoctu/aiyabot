import os
import torch
import numpy as np
from PIL import Image
from pytorch_lightning import seed_everything
from torch import autocast

from src.stablediffusion.ldm.generate import Generate

import uuid
import shutil

# 0 = resize
# 1 = crop and resize
# 2 = resize and fill
def resize_image(resize_mode, im, width, height):
    LANCZOS = (Image.Resampling.LANCZOS if hasattr(Image, 'Resampling') else Image.LANCZOS)
    if resize_mode == 0:
        res = im.resize((width, height), resample=LANCZOS)
    elif resize_mode == 1:
        ratio = width / height
        src_ratio = im.width / im.height

        src_w = width if ratio > src_ratio else im.width * height // im.height
        src_h = height if ratio <= src_ratio else im.height * width // im.width

        resized = im.resize((src_w, src_h), resample=LANCZOS)
        res = Image.new("RGB", (width, height))
        res.paste(resized, box=(width // 2 - src_w // 2, height // 2 - src_h // 2))
    else:
        ratio = width / height
        src_ratio = im.width / im.height

        src_w = width if ratio < src_ratio else im.width * height // im.height
        src_h = height if ratio >= src_ratio else im.height * width // im.width

        resized = im.resize((src_w, src_h), resample=LANCZOS)
        res = Image.new("RGB", (width, height))
        res.paste(resized, box=(width // 2 - src_w // 2, height // 2 - src_h // 2))

        if ratio < src_ratio:
            fill_height = height // 2 - src_h // 2
            res.paste(resized.resize((width, fill_height), box=(0, 0, width, 0)), box=(0, 0))
            res.paste(resized.resize((width, fill_height), box=(0, resized.height, width, resized.height)), box=(0, fill_height + src_h))
        elif ratio > src_ratio:
            fill_width = width // 2 - src_w // 2
            res.paste(resized.resize((fill_width, height), box=(0, 0, 0, height)), box=(0, 0))
            res.paste(resized.resize((fill_width, height), box=(resized.width, 0, resized.width, height)), box=(fill_width + src_w, 0))

    return res

class Text2Image:
    def __init__(self, model_path='models/model-epoch06-full.ckpt', use_gpu=True):
        self.generator = Generate(weights=model_path, config='models/v1-inference.yaml')
        try:
            self.generator.load_model()
        except:
            import sys, traceback
            traceback.print_exc(file=sys.stdout)
        
    def dream(self, prompt: str, ddim_steps: int, plms: bool, fixed_code: bool, ddim_eta: float, n_iter: int, n_samples: int, cfg_scale: float, seed: int, height: int, width: int, progress: bool, sampler_name: str):
        seed = seed_everything(seed)
        id = str(uuid.uuid4())
        results = self.generator.txt2img(prompt=prompt, iterations = 1, steps=ddim_steps, seed=seed, cfg_scale=cfg_scale, ddim_eta=ddim_eta, width=width, height=height, sampler_name=sampler_name, outdir='storage/outputs')
        shutil.move(results[0][0], f'storage/outputs/{id}.png')
        return [Image.open(f'storage/outputs/{id}.png')], results[0][1]
    
    def translation(self, prompt: str, init_img, ddim_steps: int, ddim_eta: float, n_iter: int, n_samples: int, cfg_scale: float, denoising_strength: float, seed: int, height: int, width: int, sampler_name: str):
        seed = seed_everything(seed)
        id = str(uuid.uuid4())
        image = init_img.convert("RGB")
        image = resize_image(1, image, width, height)
        image.save(f'storage/init/{id}.png')
        results = self.generator.txt2img(prompt=prompt, iterations = 1, steps=ddim_steps, seed=seed, cfg_scale=cfg_scale, ddim_eta=ddim_eta, width=width, height=height, sampler_name=sampler_name, outdir='storage/outputs', init_img=f'storage/init/{id}.png', strength=denoising_strength)
        shutil.move(results[0][0], f'storage/outputs/{id}.png')
        return [Image.open(f'storage/outputs/{id}.png')], results[0][1]

    def inpaint(self, prompt: str, init_img, mask_img, ddim_steps: int, ddim_eta: float, n_iter: int, n_samples: int, cfg_scale: float, denoising_strength: float, seed: int, height: int, width: int):
        seed = seed_everything(seed)
        id = str(uuid.uuid4())
        image = init_img.convert("RGB")
        image = resize_image(1, image, width, height)
        image.save(f'storage/init/{id}.png')
        image_mask = mask_image.convert("RGB")
        image_mask = resize_image(1, image_mask, width, height)
        image_mask.save(f'storage/init/{id}-mask.png')
        results = self.generator.txt2img(prompt=prompt, iterations = 1, steps=ddim_steps, seed=seed, cfg_scale=cfg_scale, ddim_eta=ddim_eta, width=width, height=height, sampler_name=sampler_name, outdir='storage/outputs', init_img=f'storage/init/{id}.png', init_mask=f'storage/init/{id}-mask.png', strength=denoising_strength)
        shutil.move(results[0][0], f'storage/outputs/{id}.png')
        return [Image.open(f'storage/outputs/{id}.png')], results[0][1]
