import os
import torch
import numpy as np
from PIL import Image
from pytorch_lightning import seed_everything
from torch import autocast

from transformers import CLIPTextModel, CLIPTokenizer
from diffusers import AutoencoderKL, UNet2DConditionModel, LMSDiscreteScheduler, StableDiffusionPipeline, DDIMScheduler

from src.stablediffusion.inpaint import StableDiffusionInpaintingPipeline, preprocess, preprocess_mask
from src.stablediffusion.translation import StableDiffusionImg2ImgPipeline
from src.stablediffusion.dream import StableDiffusionPipeline

class Text2Image:
    def __init__(self, use_gpu=True):
        self.device = torch.device('cuda' if use_gpu else 'cpu')
        model_name = 'CompVis/stable-diffusion-v1-4'
        token = os.environ['HF_TOKEN']
        
        self.vae = AutoencoderKL.from_pretrained(model_name, subfolder='vae', revision="fp16", use_auth_token=token)
        self.unet = UNet2DConditionModel.from_pretrained(model_name, subfolder="unet", revision="fp16", use_auth_token=token)
        self.tokenizer = CLIPTokenizer.from_pretrained("openai/clip-vit-large-patch14")
        self.text_encoder = CLIPTextModel.from_pretrained("openai/clip-vit-large-patch14")

        self.scheduler = LMSDiscreteScheduler(
            beta_start=0.00085, 
            beta_end=0.012, 
            beta_schedule="scaled_linear", 
            num_train_timesteps=1000
        )

        self.img2img_scheduler = DDIMScheduler(
            beta_start=0.00085,
            beta_end=0.012, 
            beta_schedule="scaled_linear", 
            clip_sample=False, 
            set_alpha_to_one=False
        )

        self.vae = self.vae.half().eval().to(self.device)
        self.text_encoder = self.text_encoder.half().eval().to(self.device)
        self.unet = self.unet.half().eval().to(self.device)

        self.inpaint_pipe = StableDiffusionInpaintingPipeline(
            self.vae,
            self.text_encoder,
            self.tokenizer,
            self.unet,
            self.img2img_scheduler
        )
        
        self.dream_pipe = StableDiffusionPipeline(
            self.vae,
            self.text_encoder,
            self.tokenizer,
            self.unet,
            self.scheduler
        )

        self.translation_pipe = StableDiffusionImg2ImgPipeline(
            self.vae,
            self.text_encoder,
            self.tokenizer,
            self.unet,
            self.img2img_scheduler
        )
        
    def dream(self, prompt: str, ddim_steps: int, plms: bool, fixed_code: bool, ddim_eta: float, n_iter: int, n_samples: int, cfg_scale: float, seed: int, height: int, width: int):
        rng_seed = seed_everything(seed)

        with autocast('cuda'):
            image = self.dream_pipe(prompt, height=height, width=width, guidance_Scale=cfg_scale, eta=ddim_eta, num_inference_steps=ddim_steps)['sample']

        return image, rng_seed
    
    def translation(self, prompt: str, init_img, ddim_steps: int, ddim_eta: float, n_iter: int, n_samples: int, cfg_scale: float, denoising_strength: float, seed: int, height: int, width: int):
        rng_seed = seed_everything(seed)
    
        image = init_img.convert("RGB")
        w, h = image.size
        w, h = map(lambda x: x - x % 64, (width, height))  # resize to integer multiple of 32
        image = image.resize((w, h), resample=Image.LANCZOS)
        image = np.array(image).astype(np.float32) / 255.0
        image = image[None].transpose(0, 3, 1, 2)
        image = torch.from_numpy(image)
        image = 2.0 * image - 1.0

        with autocast('cuda'):
            image = self.translation_pipe(prompt, image, denoising_strength, ddim_steps, cfg_scale, ddim_eta, None, 'pil')['sample']

        return image, rng_seed

    def inpaint(self, prompt: str, init_img, mask_img, ddim_steps: int, ddim_eta: float, n_iter: int, n_samples: int, cfg_scale: float, denoising_strength: float, seed: int, height: int, width: int):
        rng_seed = seed_everything(seed)

        w, h = init_img.size
        w, h = map(lambda x: x - x % 64, (width, height))
        init_img = init_img.resize((w, h), resample=Image.LANCZOS)

#        mask = np.array(init_img.convert('RGBA').split()[-1])
#        mask = Image.fromarray(mask)

        init_img_tensor = preprocess(init_img.convert('RGB'))

        with autocast('cuda'):
            image = self.inpaint_pipe(prompt, init_img_tensor, mask_img, denoising_strength, ddim_steps, cfg_scale, ddim_eta, None, 'pil')['sample']

        return image, rng_seed
