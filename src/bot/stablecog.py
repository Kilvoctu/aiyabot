import traceback
from asyncio import AbstractEventLoop
from threading import Thread

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


class QueueObject:
    def __init__(self, ctx, query, height, width, guidance_scale, steps, seed, strength,
                 init_image, mask_image):
        self.ctx = ctx
        self.query = query
        self.height = height
        self.width = width
        self.guidance_scale = guidance_scale
        self.steps = steps
        self.seed = seed
        self.strength = strength
        self.init_image = init_image
        self.mask_image = mask_image


class StableCog(commands.Cog, name='Stable Diffusion', description='Create images from natural language.'):
    def __init__(self, bot):
        self.dream_thread = Thread()
        self.text2image_model = Text2Image()
        self.event_loop = asyncio.get_event_loop()
        self.queue = []
        self.bot = bot

    @commands.slash_command(name='dream', description='Create an image.')
    @option(
        'prompt',
        str,
        description='A prompt to condition the model with.',
        required=True,
    )
    @option(
        'height',
        int,
        description='Height of the generated image.',
        required=False,
        choices = [x for x in range(192, 832, 64)]
    )
    @option(
        'width',
        int,
        description='Width of the generated image.',
        required=False,
        choices = [x for x in range(192, 832, 64)]
    )
    @option(
        'guidance_scale',
        float,
        description='Classifier-Free Guidance scale',
        required=False,
    )
    @option(
        'steps',
        int,
        description='The amount of steps to sample the model',
        required=False,
        choices=[x for x in range(5, 55, 5)]
    )
    @option(
        'seed',
        int,
        description='The seed to use for reproduceability',
        required=False,
    )
    @option(
        'strength',
        float,
        description='The strength used to apply the prompt to the init_image/mask_image'
    )
    @option(
        'init_image',
        discord.Attachment,
        description='The image to initialize the latents with for denoising',
        required=False,
    )
    @option(
        'mask_image',
        discord.Attachment,
        description='The mask image to use for inpainting',
        required=False,
    )
    async def dream_handler(self, ctx: discord.ApplicationContext, *, query: str, height: Optional[int] = 512,
                            width: Optional[int] = 512, guidance_scale: Optional[float] = 7.0,
                            steps: Optional[int] = 50,
                            seed: Optional[int] = -1, strength: Optional[float] = 0.8,
                            init_image: Optional[discord.Attachment] = None,
                            mask_image: Optional[discord.Attachment] = None):
        print(f'Request -- {ctx.author.name}#{ctx.author.discriminator} -- Prompt: {query}')
        if self.dream_thread.is_alive():
            user_already_in_queue = False
            for queue_object in self.queue:
                if queue_object.ctx.author.id == ctx.author.id:
                    user_already_in_queue = True
                    break
            if user_already_in_queue:
                await ctx.send_response(content=f'Please wait for your current image to finish generating before generating a new image', ephemeral=True)
            else:
                self.queue.append(QueueObject(ctx, query, height, width, guidance_scale, steps, seed,
                                              strength,
                                              init_image, mask_image))
                await ctx.send_response(content=f'Dreaming for <@{ctx.author.id}> - Queue Position: ``{len(self.queue)}`` - ``{query}``')
        else:
            await self.process_dream(QueueObject(ctx, query, height, width, guidance_scale, steps, seed,
                                                 strength,
                                                 init_image, mask_image))
            await ctx.send_response(content=f'Dreaming for <@{ctx.author.id}> - Queue Position: ``{len(self.queue)}`` - ``{query}``')

    async def process_dream(self, queue_object: QueueObject):
        self.dream_thread = Thread(target=self.dream,
                                   args=(self.event_loop, queue_object))
        self.dream_thread.start()

    @commands.slash_command(description='Test what an image looks like from the model\'s perspective')
    @option(
        'init_image',
        discord.Attachment,
        description='The image to pass through the VAE',
        required=False,
    )
    @option(
        'height',
        int,
        description='Height of the generated image.',
        required=False,
        choices = [x for x in range(192, 832, 64)]
    )
    @option(
        'width',
        int,
        description='Width of the generated image.',
        required=False,
        choices = [x for x in range(192, 832, 64)]
    )
    async def vae(self, ctx: discord.ApplicationContext, *, init_image: Optional[discord.Attachment] = None, height: Optional[int] = 512, width: Optional[int] = 512):
        await ctx.defer()
        try:
            image = Image.open(requests.get(init_image.url, stream=True).raw).convert('RGBA')
            samples = self.text2image_model.vae_test(image, height, width)
            with BytesIO() as buffer:
                samples[0].save(buffer, 'PNG')
                buffer.seek(0)
                await ctx.followup.send(file=discord.File(fp=buffer, filename=f'decoded.png'))
        except Exception as e:
            embed = discord.Embed(title='vae failed', description=f'{e}\n{traceback.print_exc()}', color=embed_color)
            await ctx.followup.send(embed=embed)

    def dream(self, event_loop: AbstractEventLoop, queue_object: QueueObject):
        try:
            if (queue_object.init_image is None) and (queue_object.mask_image is None):
                samples, seed = self.text2image_model.dream(queue_object.query, queue_object.steps, False, False, 0.0,
                                                            1, 1, queue_object.guidance_scale, queue_object.seed,
                                                            queue_object.height, queue_object.width, False)
            elif queue_object.init_image is not None:
                image = Image.open(requests.get(queue_object.init_image.url, stream=True).raw).convert('RGB')
                samples, seed = self.text2image_model.translation(queue_object.query, image, queue_object.steps, 0.0, 0,
                                                                  0, queue_object.guidance_scale,
                                                                  queue_object.strength, queue_object.seed,
                                                                  queue_object.height, queue_object.width)
            else:
                image = Image.open(requests.get(queue_object.init_image.url, stream=True).raw).convert('RGB')
                mask = Image.open(requests.get(queue_object.mask_image.url, stream=True).raw).convert('RGB')
                samples, seed = self.text2image_model.inpaint(queue_object.query, image, mask, queue_object.steps, 0.0,
                                                              1, 1, queue_object.guidance_scale,
                                                              denoising_strength=queue_object.strength,
                                                              seed=queue_object.seed, height=queue_object.height,
                                                              width=queue_object.width)

            with BytesIO() as buffer:
                samples[0].save(buffer, 'PNG')
                buffer.seek(0)
                embed = discord.Embed()
                embed.color = embed_color
                embed.add_field(name='Parameters', value=f'prompt: ``{queue_object.query}``\nseed: ``{seed}``\nresolution: ``{str(queue_object.width)}``x``{str(queue_object.height)}``\nsteps: ``{queue_object.steps}``\ncfg_scale: ``{queue_object.guidance_scale}``', inline=False)
                embed.set_footer(
                    text=f'{queue_object.ctx.author.name}#{queue_object.ctx.author.discriminator}', icon_url=queue_object.ctx.author.avatar.url)
                event_loop.create_task(
                    queue_object.ctx.channel.send(content=f'<@{queue_object.ctx.author.id}>', embed=embed, file=discord.File(fp=buffer, filename=f'{seed}.png')))
        except Exception as e:
            embed = discord.Embed(title='txt2img failed', description=f'{e}\n{traceback.print_exc()}',
                                  color=embed_color)
            event_loop.create_task(queue_object.ctx.channel.send(embed=embed))
        if self.queue:
            event_loop.create_task(self.process_dream(self.queue.pop(0)))


def setup(bot):
    bot.add_cog(StableCog(bot))
