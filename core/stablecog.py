import traceback
from asyncio import AbstractEventLoop
from threading import Thread
import os
import io
import requests
import json
import asyncio
import discord
from discord.ext import commands
from typing import Optional
from PIL import Image, PngImagePlugin
from discord.utils import get
from core import settings
import base64
from discord import option
import random
import time
import csv


embed_color = discord.Colour.from_rgb(222, 89, 28)
global URL
global DIR

#check .env for URL and DIR. if they don't exist, ignore it and go with defaults.
if os.getenv("URL") is not None:
    URL = os.environ.get('URL').rstrip("/")
    print(f'Using URL: {URL}')
else:
    URL = 'http://127.0.0.1:7860'
    print('Using Default URL: http://127.0.0.1:7860')

if os.getenv("DIR") is not None:
    DIR = os.environ.get('DIR')
    print(f'Using outputs directory: {DIR}')
else:
    DIR = "outputs"
    print('Using default outputs directory: outputs')
#if directory in DIR doesn't exist, create it
dir_exists = os.path.exists(DIR)
if dir_exists is False:
    print(f'The folder for DIR doesn\'t exist! Creating folder at {DIR}.')
    os.mkdir(DIR)

class QueueObject:
    def __init__(self, ctx, prompt, negative_prompt, steps, height, width, guidance_scale, sampler, seed,
                 strength, init_image, copy_command):
        self.ctx = ctx
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.steps = steps
        self.height = height
        self.width = width
        self.guidance_scale = guidance_scale
        self.sampler = sampler
        self.seed = seed
        self.strength = strength
        self.init_image = init_image
        self.copy_command = copy_command

class StableCog(commands.Cog, name='Stable Diffusion', description='Create images from natural language.'):
    def __init__(self, bot):
        self.dream_thread = Thread()
        self.event_loop = asyncio.get_event_loop()
        self.queue = []
        self.wait_message = []
        self.bot = bot
        self.url = URL

    @commands.slash_command(name = 'draw', description = 'Create an image')
    @option(
        'prompt',
        str,
        description='A prompt to condition the model with.',
        required=True,
    )
    @option(
        'negative_prompt',
        str,
        description='Negative prompts to exclude from output.',
        required=False,
    )
    @option(
        'steps',
        int,
        description='The amount of steps to sample the model. Default: 30',
        required=False,
        choices=[x for x in range(5, 55, 5)]
    )
    @option(
        'height',
        int,
        description='Height of the generated image. Default: 512',
        required=False,
        choices = [x for x in range(192, 832, 64)]
    )
    @option(
        'width',
        int,
        description='Width of the generated image. Default: 512',
        required=False,
        choices = [x for x in range(192, 832, 64)]
    )
    @option(
        'guidance_scale',
        float,
        description='Classifier-Free Guidance scale. Default: 7.0',
        required=False,
    )
    @option(
        'sampler',
        str,
        description='The sampler to use for generation. Default: Euler a',
        required=False,
        choices=['Euler a', 'Euler', 'LMS', 'Heun', 'DPM2', 'DPM2 a', 'DPM fast', 'DPM adaptive', 'LMS Karras', 'DPM2 Karras', 'DPM2 a Karras', 'DDIM', 'PLMS'],
        default='Euler a'
    )
    @option(
        'seed',
        int,
        description='The seed to use for reproducibility',
        required=False,
    )
    @option(
        'strength',
        float,
        description='The amount in which init_image will be altered (0.0 to 1.0).'
    )
    @option(
        'init_image',
        discord.Attachment,
        description='The starter image for generation. Remember to set strength value!',
        required=False,
    )
    async def dream_handler(self, ctx: discord.ApplicationContext, *,
                            prompt: str, negative_prompt: str = 'unset',
                            steps: Optional[int] = -1,
                            height: Optional[int] = 512, width: Optional[int] = 512,
                            guidance_scale: Optional[float] = 7.0,
                            sampler: Optional[str] = 'unset',
                            seed: Optional[int] = -1,
                            strength: Optional[float] = 0.75,
                            init_image: Optional[discord.Attachment] = None,):
        print(f'Request -- {ctx.author.name}#{ctx.author.discriminator} -- Prompt: {prompt}')

        guild = '% s' % ctx.guild_id
        try:
            sett = settings.read(guild)
        except FileNotFoundError:
            settings.build(guild)
            sett = settings.read(guild)

        if negative_prompt == 'unset':
            negative_prompt = sett['negative_prompt']
        if steps == -1 or steps > sett['max_steps']:
            steps = sett['default_steps']
        if sampler == 'unset':
            sampler = sett['sampler']

        if seed == -1: seed = random.randint(0, 0xFFFFFFFF)
        #increment number of times command is used
        with open('resources/stats.txt', 'r') as f: data = list(map(int, f.readlines()))
        data[0] = data[0] + 1
        with open('resources/stats.txt', 'w') as f: f.write('\n'.join(str(x) for x in data))
        
        #random messages for bot to say
        with open('resources/messages.csv') as csv_file:
            message_data = list(csv.reader(csv_file, delimiter='|'))
            message_row_count = len(message_data) - 1
            for row in message_data: self.wait_message.append( row[0] )
        
        #log the command. can replace bot reply with {copy_command} for easy copy-pasting
        copy_command = f'/draw prompt:{prompt} steps:{steps} height:{str(height)} width:{width} guidance_scale:{guidance_scale} sampler:{sampler} seed:{seed}'
        if negative_prompt != '': copy_command = copy_command + f' negative_prompt:{negative_prompt}'
        if init_image: copy_command = copy_command + f' strength:{strength}'
        print(copy_command)
        
        #formatting bot initial reply
        append_options = ''
        if negative_prompt != '': append_options = append_options + '\nNegative Prompt: ``' + str(negative_prompt) + '``'
        if height != 512: append_options = append_options + '\nHeight: ``' + str(height) + '``'
        if width != 512: append_options = append_options + '\nWidth: ``' + str(width) + '``'
        if guidance_scale != 7.0: append_options = append_options + '\nGuidance Scale: ``' + str(guidance_scale) + '``'
        if sampler != 'Euler a': append_options = append_options + '\nSampler: ``' + str(sampler) + '``'
        if init_image: append_options = append_options + '\nStrength: ``' + str(strength) + '``'
        
        #setup the queue
        if self.dream_thread.is_alive():
            user_already_in_queue = False
            for queue_object in self.queue:
                if queue_object.ctx.author.id == ctx.author.id:
                    user_already_in_queue = True
                    break
            if user_already_in_queue:
                await ctx.send_response(content=f'Please wait! You\'re queued up.', ephemeral=True)
            else:   
                self.queue.append(QueueObject(ctx, prompt, negative_prompt, steps, height, width, guidance_scale, sampler, seed, strength, init_image, copy_command))
                await ctx.send_response(f'<@{ctx.author.id}>, {self.wait_message[random.randint(0, message_row_count)]}\nQueue: ``{len(self.queue)}`` - ``{prompt}``\nSteps: ``{steps}`` - Seed: ``{seed}``{append_options}')
        else:
            await self.process_dream(QueueObject(ctx, prompt, negative_prompt, steps, height, width, guidance_scale, sampler, seed, strength, init_image, copy_command))
            await ctx.send_response(f'<@{ctx.author.id}>, {self.wait_message[random.randint(0, message_row_count)]}\nQueue: ``{len(self.queue)}`` - ``{prompt}``\nSteps: ``{steps}`` - Seed: ``{seed}``{append_options}')

    async def process_dream(self, queue_object: QueueObject):
        self.dream_thread = Thread(target=self.dream,
                                   args=(self.event_loop, queue_object))
        self.dream_thread.start()

    #generate the image
    def dream(self, event_loop: AbstractEventLoop, queue_object: QueueObject):
        try:
            start_time = time.time()

            #construct the payload
            payload = {
                "prompt": queue_object.prompt,
                "negative_prompt": queue_object.negative_prompt,
                "steps": queue_object.steps,
                "height": queue_object.height,
                "width": queue_object.width,
                "cfg_scale": queue_object.guidance_scale,
                "sampler_index": queue_object.sampler,
                "seed": queue_object.seed,
                "seed_resize_from_h": 0,
                "seed_resize_from_w": 0,
                "denoising_strength": None
            }
            if queue_object.init_image is not None:
                image = base64.b64encode(requests.get(queue_object.init_image.url, stream=True).content).decode('utf-8')
                img_payload = {
                    "init_images": [
                        'data:image/png;base64,' + image
                    ],
                    "denoising_strength": queue_object.strength
                }
                payload.update(img_payload)

            payload_json = json.dumps(payload)

            #send payload to webui
            with requests.Session() as s:
                if os.environ.get('USER'):
                    login_payload = {
                    'username': os.getenv('USER'),
                    'password': os.getenv('PASS')
                    }
                    s.post(URL + '/login', data=login_payload)
                else:
                    s.post(URL + '/login')
                if queue_object.init_image is not None:
                    response = requests.post(url=f'{self.url}/sdapi/v1/img2img', data=payload_json).json()
                else:
                    response = requests.post(url=f'{self.url}/sdapi/v1/txt2img', data=payload_json).json()

            end_time = time.time()

            #save local copy of image
            for i in response['images']:
                image = Image.open(io.BytesIO(base64.b64decode(i)))
                metadata = PngImagePlugin.PngInfo()
                epoch_time = int(time.time())
                metadata.add_text("parameters", str(response['info']))
                image.save(f'{DIR}\{epoch_time}-{queue_object.seed}-{queue_object.prompt[0:120]}.png', pnginfo=metadata)
                print(f'Saved image: {DIR}\{epoch_time}-{queue_object.seed}-{queue_object.prompt[0:120]}.png')

            #post to discord
            with io.BytesIO() as buffer:
                image.save(buffer, 'PNG')
                buffer.seek(0)
                embed = discord.Embed()
                embed.colour = embed_color
                if os.getenv("COPY") is not None:
                    embed.add_field(name='My drawing of', value=f'``{queue_object.copy_command}``', inline=False)
                else:
                    embed.add_field(name='My drawing of', value=f'``{queue_object.prompt}``', inline=False)
                embed.add_field(name='took me', value='``{0:.3f}`` seconds'.format(end_time-start_time), inline=False)
                if queue_object.ctx.author.avatar is None:
                    embed.set_footer(text=f'{queue_object.ctx.author.name}#{queue_object.ctx.author.discriminator}')
                else:
                    embed.set_footer(text=f'{queue_object.ctx.author.name}#{queue_object.ctx.author.discriminator}', icon_url=queue_object.ctx.author.avatar.url)
                event_loop.create_task(
                    queue_object.ctx.channel.send(content=f'<@{queue_object.ctx.author.id}>', embed=embed,
                                                  file=discord.File(fp=buffer, filename=f'{queue_object.seed}.png')))

        except Exception as e:
            embed = discord.Embed(title='txt2img failed', description=f'{e}\n{traceback.print_exc()}',
                                  color=embed_color)
            event_loop.create_task(queue_object.ctx.channel.send(embed=embed))
        if self.queue:
            event_loop.create_task(self.process_dream(self.queue.pop(0)))

def setup(bot):
    bot.add_cog(StableCog(bot))