import traceback
from asyncio import AbstractEventLoop
from threading import Thread
import os

import requests
import json
import asyncio
import discord
from discord.ext import commands
from discord.commands import OptionChoice
from typing import Optional
import base64
from discord import option
import random
import time
import csv

from core import PayloadFormatter

embed_color = discord.Colour.from_rgb(222, 89, 28)


class QueueObject:
    def __init__(self, ctx, prompt, negative_prompt, steps, height, width, guidance_scale, sampler, seed,
                 strength, init_image):
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

class StableCog(commands.Cog, name='Stable Diffusion', description='Create images from natural language.'):
    def __init__(self, bot):
        port = os.getenv('port')
        self.dream_thread = Thread()
        self.event_loop = asyncio.get_event_loop()
        self.queue = []
        self.wait_message = []
        self.bot = bot
        self.url = f'http://127.0.0.1:{port}/api/predict'
        #initialize indices for PayloadFormatter
        self.prompt_ind = 0
        self.exclude_ind = 0
        self.sample_ind = 0
        self.resy_ind = 0
        self.resx_ind = 0
        self.conform_ind = 0
        self.sampling_methods_ind = 0
        self.seed_ind = 0
        self.denoise_ind = 0
        self.data_ind = 0

    @commands.slash_command(name = "draw", description = "Create an image")
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
        description='The seed to use for reproduceability',
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
                            prompt: str, negative_prompt: str = '',
                            steps: Optional[int] = 30,
                            height: Optional[int] = 512, width: Optional[int] = 512,
                            guidance_scale: Optional[float] = 7.0,
                            sampler: Optional[str] = 'Euler a',
                            seed: Optional[int] = -1,
                            strength: Optional[float] = 0.75,
                            init_image: Optional[discord.Attachment] = None,):
        print(f'Request -- {ctx.author.name}#{ctx.author.discriminator} -- Prompt: {prompt}')
        #apply indices from PayloadFormatter and confirm
        PayloadFormatter.do_format(self, PayloadFormatter.PayloadFormat.TXT2IMG)
        print(f'Indices-prompt:{self.prompt_ind}, exclude:{self.exclude_ind}, steps:{self.sample_ind}, height:{self.resy_ind}, width:{self.resx_ind}, cfg scale:{self.conform_ind}, sampler:{self.sampling_methods_ind}, seed:{self.seed_ind}')
        if init_image:
            PayloadFormatter.do_format(self, PayloadFormatter.PayloadFormat.IMG2IMG)
            print(f'Indices-denoising strength:{self.denoise_ind}, init image:{self.data_ind}')

        if seed == -1: seed = random.randint(0, 0xFFFFFFFF)
        #increment number of times command is used
        with open("resources/stats.txt", 'r') as f: data = list(map(int, f.readlines()))
        data[0] = data[0] + 1
        with open("resources/stats.txt", 'w') as f: f.write('\n'.join(str(x) for x in data))
        
        #random messages for bot to say
        with open('resources/messages.csv') as csv_file:
            message_data = list(csv.reader(csv_file, delimiter='|'))
            message_row_count = len(message_data) - 1
            for row in message_data: self.wait_message.append( row[0] )
        
        #log the command. can replace bot reply with {copy_command} for easy copy-pasting
        copy_command = f'/draw prompt:{prompt} negative_prompt:{negative_prompt} steps:{steps} height:{str(height)} width:{width} guidance_scale:{guidance_scale} sampler:{sampler} seed:{seed}'
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
                self.queue.append(QueueObject(ctx, prompt, negative_prompt, steps, height, width, guidance_scale, sampler, seed, strength, init_image))
                await ctx.send_response(f'<@{ctx.author.id}>, {self.wait_message[random.randint(0, message_row_count)]}\nQueue: ``{len(self.queue)}`` - ``{prompt}``\nSteps: ``{steps}`` - Seed: ``{seed}``{append_options}')
        else:
            await self.process_dream(QueueObject(ctx, prompt, negative_prompt, steps, height, width, guidance_scale, sampler, seed, strength, init_image))
            await ctx.send_response(f'<@{ctx.author.id}>, {self.wait_message[random.randint(0, message_row_count)]}\nQueue: ``{len(self.queue)}`` - ``{prompt}``\nSteps: ``{steps}`` - Seed: ``{seed}``{append_options}')

    async def process_dream(self, queue_object: QueueObject):
        self.dream_thread = Thread(target=self.dream,
                                   args=(self.event_loop, queue_object))
        self.dream_thread.start()

    #generate the image
    def dream(self, event_loop: AbstractEventLoop, queue_object: QueueObject):
        try:
            start_time = time.time()
            #load copy of payload into memory
            if queue_object.init_image is not None:
                f = open('imgdata.json')
                postObj = json.load(f)
                image = base64.b64encode(requests.get(queue_object.init_image.url, stream=True).content).decode('utf-8')
                postObj['data'][self.denoise_ind] = queue_object.strength
                postObj['data'][self.data_ind] = "data:image/png;base64," + image
            else:
                f = open('data.json')
                postObj = json.load(f)

            postObj['data'][self.prompt_ind] = queue_object.prompt
            postObj['data'][self.exclude_ind] = queue_object.negative_prompt
            postObj['data'][self.sample_ind] = queue_object.steps
            postObj['data'][self.resy_ind] = queue_object.height
            postObj['data'][self.resx_ind] = queue_object.width
            postObj['data'][self.conform_ind] = queue_object.guidance_scale
            postObj['data'][self.sampling_methods_ind] = queue_object.sampler
            postObj['data'][self.seed_ind] = queue_object.seed

            #send payload to webui
            response = requests.post(self.url, json=postObj)

            end_time = time.time()

            #post to discord
            picture = discord.File(response.json()['data'][0][0]['name'])
            embed = discord.Embed()
            embed.color = embed_color
            embed.add_field(name='My drawing of', value=f'``{queue_object.prompt}``', inline=False)
            embed.add_field(name='took me', value='``{0:.3f}`` seconds'.format(end_time-start_time), inline=False)
            if queue_object.ctx.author.avatar is None:
                embed.set_footer(text=f'{queue_object.ctx.author.name}#{queue_object.ctx.author.discriminator}')
            else:
                embed.set_footer(text=f'{queue_object.ctx.author.name}#{queue_object.ctx.author.discriminator}', icon_url=queue_object.ctx.author.avatar.url)
            event_loop.create_task(
                queue_object.ctx.channel.send(content=f'<@{queue_object.ctx.author.id}>', embed=embed, file=picture))

        except Exception as e:
            embed = discord.Embed(title='txt2img failed', description=f'{e}\n{traceback.print_exc()}',
                                  color=embed_color)
            event_loop.create_task(queue_object.ctx.channel.send(embed=embed))
        if self.queue:
            event_loop.create_task(self.process_dream(self.queue.pop(0)))

def setup(bot):
    bot.add_cog(StableCog(bot))
