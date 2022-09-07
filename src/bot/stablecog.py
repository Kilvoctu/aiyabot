import traceback
import requests
import asyncio
import discord
from discord.ext import commands
from typing import Optional
from io import BytesIO
from PIL import Image
from discord import option

from src.stablediffusion.text2image_diffusers import Text2Image

embed_color = discord.Colour.from_rgb(215, 195, 134)

class StableCog(commands.Cog, name='Stable Diffusion', description='Create images from natural language.'):
    def __init__(self, bot):
        self.text2image_model = Text2Image()
        self.bot = bot

    @commands.slash_command(description='Create an image.')
    @option(
        'prompt',
        str,
        description = 'A prompt to condition the model with.',
        required=True,
    )
    @option(
        'height',
        int,
        description = 'Height of the generated image.',
        required = False,
        choices = [x for x in range(192, 832, 64)]
    )
    @option(
        'width',
        int,
        description = 'Width of the generated image.',
        required = False,
        choices = [x for x in range(192, 832, 64)]
    )
    @option(
        'guidance_scale',
        float,
        description = 'Classifier-Free Guidance scale',
        required = False,
    )
    @option(
        'steps',
        int,
        description = 'The amount of steps to sample the model',
        required = False,
        choices = [x for x in range(5, 105, 5)]
    )
    @option(
        'seed',
        int,
        description = 'The seed to use for reproduceability',
        required = False,
    )
    @option(
        'strength',
        float,
        description = 'The strength used to apply the prompt to the init_image/mask_image'
    )
    @option(
        'init_image',
        discord.Attachment,
        description = 'The image to initialize the latents with for denoising',
        required = False,
    )
    @option(
        'mask_image',
        discord.Attachment,
        description = 'The mask image to use for inpainting',
        required = False,
    )
    async def dream(self, ctx: discord.ApplicationContext, *, query: str, height: Optional[int]=512, width: Optional[int]=512, guidance_scale: Optional[float] = 7.0, steps: Optional[int] = 50, seed: Optional[int] = -1, strength: Optional[float]=0.8, init_image: Optional[discord.Attachment] = None, mask_image: Optional[discord.Attachment] = None):
        print(f'Request -- {ctx.author.name}#{ctx.author.discriminator} -- Prompt: {query}')
        await ctx.defer()
        embed = discord.Embed()
        embed.color = embed_color
        embed.set_footer(text=query)
        try:
            if (init_image is None) and (mask_image is None):
                samples, seed = self.text2image_model.dream(query, steps, False, False, 0.0, 1, 1, guidance_scale, seed, height, width, False)
            elif (init_image is not None):
                image = Image.open(requests.get(init_image.url, stream=True).raw).convert('RGB')
                samples, seed = self.text2image_model.translation(query, image, steps, 0.0, 0, 0, guidance_scale, strength, seed, height, width)
            else:
                image = Image.open(requests.get(init_image.url, stream=True).raw).convert('RGB')
                mask = Image.open(requests.get(mask_image.url, stream=True).raw).convert('RGB')
                samples, seed = self.text2image_model.inpaint(query, image, mask, steps, 0.0, 1, 1, guidance_scale, denoising_strength=strength, seed=seed, height=height, width=width)

            with BytesIO() as buffer:
                samples[0].save(buffer, 'PNG')
                buffer.seek(0)
                await ctx.followup.send(embed=embed, file=discord.File(fp=buffer, filename=f'{seed}.png'))
        except Exception as e:
            embed = discord.Embed(title='txt2img failed', description=f'{e}\n{traceback.print_exc()}', color=embed_color)
            await ctx.followup.send(embed=embed)
    
    @commands.slash_command(description='Test what an image looks like from the model\'s perspective')
    async def vae(self, ctx: discord.ApplicationContext, *, image_url: str, height: Optional[int]=512, width: Optional[int]=512):
        await ctx.defer()
        try:
            image = Image.open(requests.get(image_url, stream=True).raw).convert('RGBA')
            samples = self.text2image_model.vae_test(image, height, width)
            with BytesIO() as buffer:
                samples[0].save(buffer, 'PNG')
                buffer.seek(0)
                await ctx.followup.send(file=discord.File(fp=buffer, filename=f'decoded.png'))
        except Exception as e:
            embed = discord.Embed(title='vae failed', description=f'{e}\n{traceback.print_exc()}', color=embed_color)
            await ctx.followup.send(embed=embed)

def setup(bot):
    bot.add_cog(StableCog(bot))
