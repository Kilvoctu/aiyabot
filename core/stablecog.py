import asyncio
import base64
import contextlib
import csv
import io
import json
import random
import time
import traceback
import contextlib
from io import BytesIO
from asyncio import AbstractEventLoop
from threading import Thread
from typing import Optional
import discord
import requests
from PIL import Image, PngImagePlugin
from discord import option
from discord.commands import OptionChoice
from discord.ext import commands

from core import settings


class QueueObject:
    def __init__(self, ctx, prompt, negative_prompt, steps, height, width, guidance_scale, sampler, seed,
                 strength, init_image, copy_command, batch_count):
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
        self.batch_count = batch_count

class StableCog(commands.Cog, name='Stable Diffusion', description='Create images from natural language.'):
    def __init__(self, bot):
        self.dream_thread = Thread()
        self.event_loop = asyncio.get_event_loop()
        self.queue = []
        self.wait_message = []
        self.bot = bot
        self.post_model = ""
        self.send_model = False

    with open('resources/models.csv', encoding='utf-8') as csv_file:
        model_data = list(csv.reader(csv_file, delimiter='|'))

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
        'data_model',
        str,
        description='Select the data model for image generation',
        required=False,
        choices=[OptionChoice(name=row[0], value=row[1]) for row in model_data[1:]]
    )
    @option(
        'steps',
        int,
        description='The amount of steps to sample the model.',
        min_value=1,
        required=False,
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
    @option(
        'url_image',
        str,
        description='The starter URL image for generation. This overrides init_image!',
        required=False,
    )
    @option(
        'count',
        int,
        description='The number of images to generate. This is "Batch count", not "Batch size".',
        required=False,
    )
    async def dream_handler(self, ctx: discord.ApplicationContext, *,
                            prompt: str, negative_prompt: str = 'unset',
                            data_model: Optional[str] = None,
                            steps: Optional[int] = -1,
                            height: Optional[int] = 512, width: Optional[int] = 512,
                            guidance_scale: Optional[float] = 7.0,
                            sampler: Optional[str] = 'unset',
                            seed: Optional[int] = -1,
                            strength: Optional[float] = 0.75,
                            init_image: Optional[discord.Attachment] = None,
                            url_image: Optional[str],
                            count: Optional[int] = None):
        print(f'Request -- {ctx.author.name}#{ctx.author.discriminator} -- Prompt: {prompt}')

        #update defaults with any new defaults from settingscog
        guild = '% s' % ctx.guild_id
        if negative_prompt == 'unset':
            negative_prompt = settings.read(guild)['negative_prompt']
        if steps == -1:
            steps = settings.read(guild)['default_steps']
        if count is None:
            count = settings.read(guild)['default_count']
        if sampler == 'unset':
            sampler = settings.read(guild)['sampler']
        # if a model is not selected, do nothing
        model_name = 'Default'
        if data_model is None:
            data_model = settings.read(guild)['data_model']
        else:
            self.post_model = data_model
            self.send_model = True
        # get the selected model's display name
        with open('resources/models.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='|')
            for row in reader:
                if row['model_full_name'] == data_model:
                    model_name = row['display_name']

        if seed == -1: seed = random.randint(0, 0xFFFFFFFF)

        #url *will* override init image for compatibility, can be changed here
        if(url_image):
            try: 
                init_image = requests.get(url_image)
            except:
                await ctx.send_response('URL image not found!\nI will do my best without it!')

        #increment number of times command is used
        with open('resources/stats.txt', 'r') as f:
            data = list(map(int, f.readlines()))
        data[0] = data[0] + 1
        with open('resources/stats.txt', 'w') as f:
            f.write('\n'.join(str(x) for x in data))

        #random messages for bot to say
        with open('resources/messages.csv') as csv_file:
            message_data = list(csv.reader(csv_file, delimiter='|'))
            message_row_count = len(message_data) - 1
            for row in message_data:
                self.wait_message.append( row[0] )

        #formatting bot initial reply
        append_options = ''
        #lower step value to the highest setting if user goes over max steps
        if steps > settings.read(guild)['max_steps']:
            steps = settings.read(guild)['max_steps']
            append_options = append_options + '\nExceeded maximum of ``' + str(steps) + '`` steps! This is the best I can do...'
        if model_name != 'Default':
            append_options = append_options + '\nModel: ``' + str(model_name) + '``'
        if negative_prompt != '':
            append_options = append_options + '\nNegative Prompt: ``' + str(negative_prompt) + '``'
        if height != 512:
            append_options = append_options + '\nHeight: ``' + str(height) + '``'
        if width != 512:
            append_options = append_options + '\nWidth: ``' + str(width) + '``'
        if guidance_scale != 7.0:
            append_options = append_options + '\nGuidance Scale: ``' + str(guidance_scale) + '``'
        if sampler != 'Euler a':
            append_options = append_options + '\nSampler: ``' + str(sampler) + '``'
        if init_image:
            append_options = append_options + '\nStrength: ``' + str(strength) + '``'
        if count != 1:
            max_count = settings.read(guild)['max_count']
            if count > max_count:
                count = max_count
                append_options = append_options + '\nExceeded maximum of ``' + str(count) + '`` images! This is the best I can do...'
            append_options = append_options + '\nCount: ``' + str(count) + '``'

        #log the command
        copy_command = f'/draw prompt:{prompt} steps:{steps} height:{str(height)} width:{width} guidance_scale:{guidance_scale} sampler:{sampler} seed:{seed} count:{count}'
        if negative_prompt != '':
            copy_command = copy_command + f' negative_prompt:{negative_prompt}'
        if data_model:
            copy_command = copy_command + f' data_model:{model_name}'
        if init_image:
            copy_command = copy_command + f' strength:{strength}'
        print(copy_command)

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
                self.queue.append(QueueObject(ctx, prompt, negative_prompt, steps, height, width, guidance_scale, sampler, seed, strength, init_image, copy_command, count))
                await ctx.send_response(f'<@{ctx.author.id}>, {self.wait_message[random.randint(0, message_row_count)]}\nQueue: ``{len(self.queue)}`` - ``{prompt}``\nSteps: ``{steps}`` - Seed: ``{seed}``{append_options}')
        else:
            await self.process_dream(QueueObject(ctx, prompt, negative_prompt, steps, height, width, guidance_scale, sampler, seed, strength, init_image, copy_command, count))
            await ctx.send_response(f'<@{ctx.author.id}>, {self.wait_message[random.randint(0, message_row_count)]}\nQueue: ``{len(self.queue)}`` - ``{prompt}``\nSteps: ``{steps}`` - Seed: ``{seed}``{append_options}')

    async def process_dream(self, queue_object: QueueObject):
        self.dream_thread = Thread(target=self.dream,
                                   args=(self.event_loop, queue_object))
        self.dream_thread.start()

    #generate the image
    def dream(self, event_loop: AbstractEventLoop, queue_object: QueueObject):
        try:
            start_time = time.time()

            #construct a payload for data model, then the normal payload
            model_payload = {
                "fn_index": settings.global_var.model_fn_index,
                "data": [
                    self.post_model
                ]
            }
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
                "denoising_strength": None,
                "n_iter": queue_object.batch_count
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

            #only send model payload if one is defined
            if self.send_model:
                requests.post(url=f'{settings.global_var.url}/api/predict', json=model_payload)
            #send normal payload to webui
            with requests.Session() as s:
                if settings.global_var.username is not None:
                    login_payload = {
                    'username': settings.global_var.username,
                    'password': settings.global_var.password
                    }
                    s.post(settings.global_var.url + '/login', data=login_payload)
                else:
                    s.post(settings.global_var.url + '/login')
                if queue_object.init_image is not None:
                    response = requests.post(url=f'{settings.global_var.url}/sdapi/v1/img2img', json=payload)
                else:
                    response = requests.post(url=f'{settings.global_var.url}/sdapi/v1/txt2img', json=payload)
            response_data = response.json()
            end_time = time.time()

            #grab png info
            load_r = json.loads(response_data['info'])
            meta = load_r["infotexts"][0]
            #create safe/sanitized filename
            keep_chars = (' ', '.', '_')
            file_name = "".join(c for c in queue_object.prompt if c.isalnum() or c in keep_chars).rstrip()

            # save local copy of image and prepare PIL images
            pil_images = []
            for i, image_base64 in enumerate(response_data['images']):
                image = Image.open(io.BytesIO(base64.b64decode(image_base64.split(",",1)[0])))
                pil_images.append(image)

                metadata = PngImagePlugin.PngInfo()
                epoch_time = int(time.time())
                metadata.add_text("parameters", meta)
                file_path = f'{settings.global_var.dir}\{epoch_time}-{queue_object.seed}-{file_name[0:120]}-{i}.png'
                image.save(file_path, pnginfo=metadata)
                print(f'Saved image: {file_path}')

            # post to discord
            with contextlib.ExitStack() as stack:
                buffer_handles = [stack.enter_context(io.BytesIO()) for _ in pil_images]

                embed = discord.Embed()
                embed.colour = settings.global_var.embed_color

                image_count = len(pil_images)
                noun_descriptor = "drawing" if image_count == 1 else f'{image_count} drawings'
                value = queue_object.copy_command if settings.global_var.copy_command else queue_object.prompt
                embed.add_field(name=f'My {noun_descriptor} of', value=f'``{value}``', inline=False)

                embed.add_field(name='took me', value='``{0:.3f}`` seconds'.format(end_time-start_time), inline=False)

                footer_args = dict(text=f'{queue_object.ctx.author.name}#{queue_object.ctx.author.discriminator}')
                if queue_object.ctx.author.avatar is not None:
                    footer_args['icon_url'] = queue_object.ctx.author.avatar.url
                embed.set_footer(**footer_args)

                for (pil_image, buffer) in zip(pil_images, buffer_handles):
                    pil_image.save(buffer, 'PNG')
                    buffer.seek(0)

                files = [discord.File(fp=buffer, filename=f'{queue_object.seed}-{i}.png') for (i, buffer) in enumerate(buffer_handles)]
                event_loop.create_task(queue_object.ctx.channel.send(content=f'<@{queue_object.ctx.author.id}>', embed=embed, files=files))

        except Exception as e:
            embed = discord.Embed(title='txt2img failed', description=f'{e}\n{traceback.print_exc()}',
                                  color=settings.global_var.embed_color)
            event_loop.create_task(queue_object.ctx.channel.send(embed=embed))
        if self.queue:
            event_loop.create_task(self.process_dream(self.queue.pop(0)))

def setup(bot):
    bot.add_cog(StableCog(bot))
