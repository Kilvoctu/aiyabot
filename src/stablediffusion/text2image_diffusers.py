import os
import torch
import numpy as np
from PIL import Image
from pytorch_lightning import seed_everything
from torch import autocast

from transformers import CLIPTextModel, CLIPTokenizer
from diffusers import AutoencoderKL, UNet2DConditionModel, LMSDiscreteScheduler, StableDiffusionPipeline, DDIMScheduler, PNDMScheduler

from src.stablediffusion.inpaint import StableDiffusionInpaintingPipeline, preprocess, preprocess_mask
from src.stablediffusion.translation import StableDiffusionImg2ImgPipeline
from src.stablediffusion.dream import StableDiffusionPipeline

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

        self.img2img_scheduler = PNDMScheduler(
            beta_start=0.00085,
            beta_end=0.012, 
            beta_schedule="scaled_linear",
            num_train_timesteps=1000,
            skip_prk_steps=True
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
        
    def dream(self, prompt: str, ddim_steps: int, plms: bool, fixed_code: bool, ddim_eta: float, n_iter: int, n_samples: int, cfg_scale: float, seed: int, height: int, width: int, progress: bool):
        rng_seed = seed_everything(seed)

        with autocast('cuda'):
            image = self.dream_pipe(prompt, height=height, width=width, guidance_scale=cfg_scale, eta=ddim_eta, num_inference_steps=ddim_steps, progress=progress)['sample']

        return image, rng_seed
    
    def translation(self, prompt: str, init_img, ddim_steps: int, ddim_eta: float, n_iter: int, n_samples: int, cfg_scale: float, denoising_strength: float, seed: int, height: int, width: int):
        rng_seed = seed_everything(seed)
    
        image = init_img.convert("RGB")
        image = resize_image(1, image, width, height)
        image = np.array(image).astype(np.float32) / 255.0
        image = image[None].transpose(0, 3, 1, 2)
        image = torch.from_numpy(image)
        image = 2.0 * image - 1.0

        with autocast('cuda'):
            image = self.translation_pipe(prompt, image, denoising_strength, ddim_steps, cfg_scale, ddim_eta, None, 'pil')['sample']

        return image, rng_seed

    def inpaint(self, prompt: str, init_img, mask_img, ddim_steps: int, ddim_eta: float, n_iter: int, n_samples: int, cfg_scale: float, denoising_strength: float, seed: int, height: int, width: int):
        rng_seed = seed_everything(seed)

        init_img = resize_image(1, init_img, width, height)

#        mask = np.array(init_img.convert('RGBA').split()[-1])
#        mask = Image.fromarray(mask)

        init_img_tensor = preprocess(init_img.convert('RGB'))

        with autocast('cuda'):
            image = self.inpaint_pipe(prompt, init_img_tensor, mask_img, denoising_strength, ddim_steps, cfg_scale, ddim_eta, None, 'pil')['sample']

        return image, rng_seed

    @torch.no_grad()
    def vae_test(self, image, height: int, width: int):
        image = image.convert("RGB")
        image = resize_image(1, image, width, height)
        image = np.array(image).astype(np.float32) / 255.0
        image = image[None].transpose(0, 3, 1, 2)
        image = torch.from_numpy(image)
        image = 2.0 * image - 1.0

        with autocast('cuda'):
            latent_image = self.vae.decode(self.vae.encode(image.to(self.device)).sample())
            latent_image = (latent_image / 2 + 0.5).clamp(0, 1)
            latent_image = latent_image.cpu().permute(0, 2, 3, 1).numpy()

        if latent_image.ndim == 3:
            latent_image = latent_image[None, ...]
        latent_image = (latent_image * 255).round().astype('uint8')
        latent_image = [Image.fromarray(image) for image in latent_image]

        return latent_image