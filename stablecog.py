import traceback
from asyncio import AbstractEventLoop
from threading import Thread

import requests
import json
import asyncio
import discord
from discord.ext import commands
from discord.commands import OptionChoice
from typing import Optional
from discord import option
import random
import time
import csv

from core import PayloadFormatter

embed_color = discord.Colour.from_rgb(222, 89, 28)


class QueueObject:
    def __init__(self, ctx, prompt, negative_prompt, steps, height, width, guidance_scale, seed):
        self.ctx = ctx
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.steps = steps
        self.height = height
        self.width = width
        self.guidance_scale = guidance_scale
        self.seed = seed

class StableCog(commands.Cog, name='Stable Diffusion', description='Create images from natural language.'):
    def __init__(self, bot):
        self.dream_thread = Thread()
        self.event_loop = asyncio.get_event_loop()
        self.queue = []
        self.wait_message = []
        self.bot = bot
        self.url = "http://127.0.0.1:7860/api/predict"
        #initialize indices for PayloadFormatter
        self.prompt_ind = 0
        self.exclude_ind = 0
        self.sample_ind = 0
        self.resy_ind = 0
        self.resx_ind = 0
        self.conform_ind = 0
        self.seed_ind = 0

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
        'seed',
        int,
        description='The seed to use for reproduceability',
        required=False,
    )
    async def dream_handler(self, ctx: discord.ApplicationContext, *,
                            prompt: str, negative_prompt: str = '',
                            steps: Optional[int] = 30,
                            height: Optional[int] = 512, width: Optional[int] = 512,
                            guidance_scale: Optional[float] = 7.0,
                            seed: Optional[int] = -1):
        print(f'Request -- {ctx.author.name}#{ctx.author.discriminator} -- Prompt: {prompt}')
        #apply indices from PayloadFormatter and confirm
        PayloadFormatter.do_format(self, PayloadFormatter.PayloadFormat.TXT2IMG)
        print(f'Indices-prompt:{self.prompt_ind}, exclude:{self.exclude_ind}, steps:{self.sample_ind}, height:{self.resy_ind}, width:{self.resx_ind}, cfg scale:{self.conform_ind}, seed:{self.seed_ind}')

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
        
        #log the command
        copy_command = f'/draw prompt:{prompt} negative_prompt:{negative_prompt} steps:{steps} height:{str(height)} width:{width} guidance_scale:{guidance_scale} seed:{seed}'
        print(copy_command)
        
        #formatting bot initial reply
        append_options = ""
        if negative_prompt != '': append_options = append_options + "\nNegative Prompt: ``" + str(negative_prompt) + "``"
        if height != 512: append_options = append_options + "\nChanged height: ``" + str(height) + "``"
        if width != 512: append_options = append_options + "\nChanged width: ``" + str(width) + "``"
        if guidance_scale != 7.0: append_options = append_options + "\nChanged Guidance Scale: ``" + str(guidance_scale) + "``"
        
        #bot's initial reply
        initial_response = f'<@{ctx.author.id}>, {self.wait_message[random.randint(0, message_row_count)]}\nQueue: ``{len(self.queue)}`` - ``{prompt}``\nSteps: ``{steps}`` - Seed: ``{seed}``{append_options}'
        
        #setup the queue
        if self.dream_thread.is_alive():
            user_already_in_queue = False
            for queue_object in self.queue:
                if queue_object.ctx.author.id == ctx.author.id:
                    user_already_in_queue = True
                    break
            if user_already_in_queue:
                await ctx.send_response(content=f'You\'re in queue.', ephemeral=True)
            else:   
                self.queue.append(QueueObject(ctx, prompt, negative_prompt, steps, height, width, guidance_scale, seed))
                await ctx.send_response(initial_response)
        else:
            await self.process_dream(QueueObject(ctx, prompt, negative_prompt, steps, height, width, guidance_scale, seed))
            await ctx.send_response(initial_response)

    async def process_dream(self, queue_object: QueueObject):
        self.dream_thread = Thread(target=self.dream,
                                   args=(self.event_loop, queue_object))
        self.dream_thread.start()

    #generate the image
    def dream(self, event_loop: AbstractEventLoop, queue_object: QueueObject):
        try:
            start_time = time.time()
            #load copy of payload into memory
            f = open('data.json')
            postObj = json.load(f)

            postObj['data'][self.prompt_ind] = queue_object.prompt
            postObj['data'][self.exclude_ind] = queue_object.negative_prompt
            postObj['data'][self.sample_ind] = queue_object.steps
            postObj['data'][self.resy_ind] = queue_object.height
            postObj['data'][self.resx_ind] = queue_object.width
            postObj['data'][self.conform_ind] = queue_object.guidance_scale
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
            embed.set_footer(
                text=f'{queue_object.ctx.author.name}#{queue_object.ctx.author.discriminator}', icon_url=queue_object.ctx.author.avatar.url)
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