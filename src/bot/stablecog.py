import traceback
import requests
import asyncio
import discord
from discord.ext import commands
from typing import Optional
from io import BytesIO
from PIL import Image

from src.stablediffusion.text2image_diffusers import Text2Image

embed_color = discord.Colour.from_rgb(215, 195, 134)

class StableCog(commands.Cog, name='Stable Diffusion', description='Create images from natural language.'):
    def __init__(self, bot):
        self.text2image_model = Text2Image()
        self.bot = bot

    @commands.slash_command(description='Create a image from a natural language query.')
    async def dream(self, ctx: discord.ApplicationContext, *, query: str, height: Optional[int]=512, width: Optional[int]=512, guidance_scale: Optional[float] = 7.0, steps: Optional[int] = 50, seed: Optional[int] = -1, progress: Optional[bool] = False):
        print(f'Request -- {ctx.author.name}#{ctx.author.discriminator} -- Prompt: {query}')
        await ctx.defer()
        embed = discord.Embed()
        embed.color = embed_color
        embed.set_footer(text=query)

        try:
            if steps > 100:
                steps = 100
            samples, seed = self.text2image_model.dream(query, steps, False, False, 0.0, 1, 1, guidance_scale, seed, height, width, progress)

            with BytesIO() as buffer:
                samples[0].save(buffer, 'PNG')
                buffer.seek(0)
                if progress == False:
                    await ctx.followup.send(embed=embed, file=discord.File(fp=buffer, filename=f'{seed}.png'))
                else:
                    await ctx.followup.send(embed=embed, files=[discord.File(fp=buffer, filename=f'{seed}.png'), discord.File(open('output.gif', 'rb'), filename=f'{seed}.gif')])
        except Exception as e:
            embed = discord.Embed(title='txt2img failed', description=f'{e}\n{traceback.print_exc()}', color=embed_color)
            await ctx.followup.send(embed=embed)

    @commands.slash_command(description='Create an image from another image.')
    async def translate(self, ctx: discord.ApplicationContext, *, query: str, image_url: str, denoising_strength: Optional[float]=0.7, height: Optional[int]=512, width: Optional[int]=512, guidance_scale: Optional[float] = 7.0, steps: Optional[int] = 50, seed: Optional[int] = -1):
        print(f'Request -- {ctx.author.name}#{ctx.author.discriminator} -- Prompt: {query}')
        await ctx.defer()
        embed = discord.Embed()
        embed.color = embed_color
        embed.set_footer(text=query)
        try:
            if steps > 100:
                steps = 100
            image = Image.open(requests.get(image_url, stream=True).raw).convert('RGB')
            samples, seed = self.text2image_model.translation(query, image, steps, 0.0, 1, 1, guidance_scale, denoising_strength=denoising_strength, seed=seed, height=height, width=width)
            with BytesIO() as buffer:
                samples[0].save(buffer, 'PNG')
                buffer.seek(0)
                await ctx.followup.send(embed=embed, file=discord.File(fp=buffer, filename=f'{seed}.png'))
        except Exception as e:
            embed = discord.Embed(title='img2img failed', description=f'{e}\n{traceback.print_exc()}', color=embed_color)
            await ctx.followup.send(embed=embed)
    
    @commands.message_command(name='Refine')
    async def refine(self, ctx: discord.ApplicationContext, message: discord.Message):
        await ctx.defer()
        embed = discord.Embed()
        embed.color = embed_color
        try:
            if (not message.embeds) or (not message.attachments):
                raise Exception('Not an AI generated image')
            query = message.embeds[0].footer.text
            embed.set_footer(text=query)
            image = Image.open(requests.get(message.attachments[0].url, stream=True).raw).convert('RGB')
            samples, seed = self.text2image_model.translation(query, image, 40, 0.0, 1, 1, 7.0, denoising_strength=0.4, seed=-1, height=image.height, width=image.width)
            with BytesIO() as buffer:
                samples[0].save(buffer, 'PNG')
                buffer.seek(0)
                await ctx.followup.send(embed=embed, file=discord.File(fp=buffer, filename=f'{seed}.png'))
        except Exception as e:
            embed = discord.Embed(title='refinement failed', description=f'{e}\n{traceback.print_exc()}', color=embed_color)
            await ctx.followup.send(embed=embed)
    
    @commands.message_command(name='Psychedelico')
    async def butcher(self, ctx: discord.ApplicationContext, message: discord.Message):
        await ctx.defer()
        embed = discord.Embed()
        embed.color = embed_color
        try:
            if not message.attachments:
                raise Exception('Not an image')
            image = Image.open(requests.get(message.attachments[0].url, stream=True).raw).convert('RGB')
            samples, seed = self.text2image_model.translation('fractal rendered image in colorful psychedelic style. dmt lsd drugs. hallucinations bad trip.', image, 40, 0.0, 1, 1, 7.0, denoising_strength=0.75, seed=-1, height=512, width=512)
            with BytesIO() as buffer:
                samples[0].save(buffer, 'PNG')
                buffer.seek(0)
                await ctx.followup.send(file=discord.File(fp=buffer, filename=f'{seed}.png'))
        except Exception as e:
            embed = discord.Embed(title='trip failed', description=f'{e}\n{traceback.print_exc()}', color=embed_color)
            await ctx.followup.send(embed=embed)

    
    @commands.slash_command(description='Fill empty gaps in an image.')
    @commands.max_concurrency(5, per=commands.BucketType.default, wait=False)
    async def inpaint(self, ctx: discord.ApplicationContext, *, query: str, image_url: str, mask_url: str, denoising_strength: Optional[float]=0.7, height: Optional[int]=512, width: Optional[int]=512, guidance_scale: Optional[float] = 7.0, steps: Optional[int] = 50, seed: Optional[int] = -1):
        await ctx.defer()
        embed = discord.Embed()
        embed.color = embed_color
        embed.set_footer(text=query)
        try:
            image = Image.open(requests.get(image_url, stream=True).raw).convert('RGBA')
            mask_image = Image.open(requests.get(mask_url, stream=True).raw).convert('RGBA')
            samples, seed = self.text2image_model.inpaint(query, image, mask_image, steps, 0.0, 1, 1, guidance_scale, denoising_strength=denoising_strength, seed=seed, height=height, width=width)

            embed.title = None
            embed.description = None
            embed.set_footer(text=query)

            with BytesIO() as buffer:
                samples[0].save(buffer, 'PNG')
                buffer.seek(0)
                await ctx.followup.send(embed=embed, file=discord.File(fp=buffer, filename=f'{seed}.png'))
        except Exception as e:
            embed = discord.Embed(title='inpaint failed', description=f'{e}\n{traceback.print_exc()}', color=embed_color)
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
