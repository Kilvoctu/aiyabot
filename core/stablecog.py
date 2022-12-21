import base64
import contextlib
import discord
import io
import random
import requests
import time
import traceback
import json
from asyncio import AbstractEventLoop
from PIL import Image, PngImagePlugin
from discord import option
from discord.ext import commands
from typing import Optional

from core import queuehandler
from core import viewhandler
from core import settings
from core import upscalecog
from core import identifycog


class StableCog(commands.Cog, name='Stable Diffusion', description='Create images from natural language.'):
    ctx_parse = discord.ApplicationContext

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(viewhandler.DrawView(self))

    # pulls from model_names list and makes some sort of dynamic list to bypass Discord 25 choices limit
    def model_autocomplete(self: discord.AutocompleteContext):
        return [
            model for model in settings.global_var.model_names
        ]

    # and for styles
    def style_autocomplete(self: discord.AutocompleteContext):
        return [
            style for style in settings.global_var.style_names
        ]

    @commands.slash_command(name='draw', description='Create an image')
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
        autocomplete=discord.utils.basic_autocomplete(model_autocomplete),
    )
    @option(
        'steps',
        int,
        description='The amount of steps to sample the model.',
        min_value=1,
        required=False,
    )
    @option(
        'width',
        int,
        description='Width of the generated image',
        required=False,
        choices=[x for x in range(192, 1088, 64)]
    )
    @option(
        'height',
        int,
        description='Height of the generated image',
        required=False,
        choices=[x for x in range(192, 1088, 64)]
    )
    @option(
        'guidance_scale',
        str,
        description='Classifier-Free Guidance scale',
        required=False,
    )
    @option(
        'sampler',
        str,
        description='The sampler to use for generation',
        required=False,
        choices=settings.global_var.sampler_names,
    )
    @option(
        'seed',
        int,
        description='The seed to use for reproducibility',
        required=False,
    )
    @option(
        'strength',
        str,
        description='The amount in which init_image will be altered (0.0 to 1.0).'
    )
    @option(
        'init_image',
        discord.Attachment,
        description='The starter image for generation. Remember to set strength value!',
        required=False,
    )
    @option(
        'init_url',
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
    @option(
        'style',
        str,
        description='Apply a predefined style to the generation.',
        required=False,
        autocomplete=discord.utils.basic_autocomplete(style_autocomplete),
    )
    @option(
        'facefix',
        str,
        description='Tries to improve faces in images.',
        required=False,
        choices=settings.global_var.facefix_models,
    )
    @option(
        'highres_fix',
        bool,
        description='Tries to fix issues from generating high-res images. Takes longer!',
        required=False,
    )
    @option(
        'clip_skip',
        int,
        description='Number of last layers of CLIP model to skip',
        required=False,
        choices=[x for x in range(1, 13, 1)]
    )
    async def dream_handler(self, ctx: discord.ApplicationContext, *,
                            prompt: str, negative_prompt: str = 'unset',
                            data_model: Optional[str] = None,
                            steps: Optional[int] = -1,
                            width: Optional[int] = 1, height: Optional[int] = 1,
                            guidance_scale: Optional[str] = '7.0',
                            sampler: Optional[str] = 'unset',
                            seed: Optional[int] = -1,
                            strength: Optional[str] = '0.75',
                            init_image: Optional[discord.Attachment] = None,
                            init_url: Optional[str],
                            count: Optional[int] = None,
                            style: Optional[str] = 'None',
                            facefix: Optional[str] = 'None',
                            highres_fix: Optional[bool] = False,
                            clip_skip: Optional[int] = 0):

        settings.global_var.send_model = False
        # update defaults with any new defaults from settingscog
        guild = '% s' % ctx.guild_id
        if negative_prompt == 'unset':
            negative_prompt = settings.read(guild)['negative_prompt']
        if steps == -1:
            steps = settings.read(guild)['default_steps']
        if width == 1:
            width = settings.read(guild)['default_width']
        if height == 1:
            height = settings.read(guild)['default_height']
        if count is None:
            count = settings.read(guild)['default_count']
        if sampler == 'unset':
            sampler = settings.read(guild)['sampler']
        if clip_skip == 0:
            clip_skip = settings.read(guild)['clip_skip']

        # if a model is not selected, do nothing
        model_name = 'Default'
        model_index = 0
        if data_model is None:
            data_model = settings.read(guild)['data_model']
            if data_model != '':
                settings.global_var.send_model = True
        else:
            settings.global_var.send_model = True

        simple_prompt = prompt
        # take selected data_model and get model_name, then update data_model with the full name
        for (key, value), (key2, value2) in zip(settings.global_var.model_names.items(),
                                                settings.global_var.model_tokens.items()):
            if key == data_model:
                model_name = key
                data_model = value
                # look at the model for activator token and prepend prompt with it
                prompt = value2 + " " + prompt
                # if there's no activator token, remove the extra blank space
                prompt = prompt.lstrip(' ')
                break
            # get the index of the selected model for later use
            model_index = model_index + 1

        # if using model "short name" in csv, find its respective title for payload
        for title, name in settings.global_var.simple_model_pairs.items():
            if name == data_model.replace('\\', '_').replace('/', '_'):
                data_model = title

        if not settings.global_var.send_model:
            print(f'Request -- {ctx.author.name}#{ctx.author.discriminator} -- Prompt: {prompt}')
        else:
            print(
                f'Request -- {ctx.author.name}#{ctx.author.discriminator} -- Prompt: {prompt} -- Using model: {data_model}')

        if seed == -1:
            seed = random.randint(0, 0xFFFFFFFF)

        # url *will* override init image for compatibility, can be changed here
        if init_url:
            try:
                init_image = requests.get(init_url)
            except(Exception,):
                await ctx.send_response('URL image not found!\nI will do my best without it!')

        # formatting aiya initial reply
        reply_adds = ''
        # lower step value to the highest setting if user goes over max steps
        if steps > settings.read(guild)['max_steps']:
            steps = settings.read(guild)['max_steps']
            reply_adds = reply_adds + f'\nExceeded maximum of ``{steps}`` steps! This is the best I can do...'
        if model_name != 'Default':
            reply_adds = reply_adds + f'\nModel: ``{model_name}``'
        if negative_prompt != '':
            reply_adds = reply_adds + f'\nNegative Prompt: ``{negative_prompt}``'
        if (width != 512) or (height != 512):
            reply_adds = reply_adds + f'\nSize: ``{width}``x``{height}``'
        if guidance_scale != '7.0':
            reply_adds = reply_adds + f'\nGuidance Scale: ``{guidance_scale}``'
        if sampler != 'Euler a':
            reply_adds = reply_adds + f'\nSampler: ``{sampler}``'
        if init_image:
            reply_adds = reply_adds + f'\nStrength: ``{strength}``'
            reply_adds = reply_adds + f'\nURL Init Image: ``{init_image.url}``'
        if count != 1:
            max_count = settings.read(guild)['max_count']
            if count > max_count:
                count = max_count
                reply_adds = reply_adds + f'\nExceeded maximum of ``{count}`` images! This is the best I can do...'
            reply_adds = reply_adds + f'\nCount: ``{count}``'
        if style != 'None':
            reply_adds = reply_adds + f'\nStyle: ``{style}``'
        if facefix != 'None':
            reply_adds = reply_adds + f'\nFace restoration: ``{facefix}``'
        if clip_skip != 1:
            reply_adds = reply_adds + f'\nCLIP skip: ``{clip_skip}``'

        # set up tuple of parameters to pass into the Discord view
        input_tuple = (
            ctx, prompt, negative_prompt, data_model, steps, width, height, guidance_scale, sampler, seed, strength,
            init_image, count, style, facefix, highres_fix, clip_skip, simple_prompt, model_index)
        view = viewhandler.DrawView(input_tuple)
        # set up tuple of queues to pass into union()
        queues = (queuehandler.GlobalQueue.draw_q, queuehandler.GlobalQueue.upscale_q, queuehandler.GlobalQueue.identify_q)
        # setup the queue
        if queuehandler.GlobalQueue.dream_thread.is_alive():
            user_already_in_queue = False
            for queue_object in queuehandler.union(*queues):
                if queue_object.ctx.author.id == ctx.author.id:
                    user_already_in_queue = True
                    break
            if user_already_in_queue:
                await ctx.send_response(content=f'Please wait! You\'re queued up.', ephemeral=True)
            else:
                queuehandler.GlobalQueue.draw_q.append(queuehandler.DrawObject(*input_tuple, view))
                await ctx.send_response(
                    f'<@{ctx.author.id}>, {settings.messages()}\nQueue: ``{len(queuehandler.union(*queues))}`` - ``{simple_prompt}``\nSteps: ``{steps}`` - Seed: ``{seed}``{reply_adds}')
        else:
            await queuehandler.process_dream(self, queuehandler.DrawObject(*input_tuple, view))
            await ctx.send_response(
                f'<@{ctx.author.id}>, {settings.messages()}\nQueue: ``{len(queuehandler.union(*queues))}`` - ``{simple_prompt}``\nSteps: ``{steps}`` - Seed: ``{seed}``{reply_adds}')

    # generate the image
    def dream(self, event_loop: AbstractEventLoop, queue_object: queuehandler.DrawObject):
        try:
            start_time = time.time()

            # create persistent session since we'll need to do a few API calls
            s = requests.Session()
            if settings.global_var.api_auth:
                s.auth = (settings.global_var.api_user, settings.global_var.api_pass)

            # construct a payload for data model, then the normal payload
            model_payload = {
                "sd_model_checkpoint": queue_object.data_model
            }
            payload = {
                "prompt": queue_object.prompt,
                "negative_prompt": queue_object.negative_prompt,
                "steps": queue_object.steps,
                "width": queue_object.width,
                "height": queue_object.height,
                "cfg_scale": queue_object.guidance_scale,
                "sampler_index": queue_object.sampler,
                "seed": queue_object.seed,
                "seed_resize_from_h": 0,
                "seed_resize_from_w": 0,
                "denoising_strength": None,
                "n_iter": queue_object.batch_count,
                "styles": [
                    queue_object.style
                ]
            }

            # update payload if init_img or init_url is used
            if queue_object.init_image is not None:
                image = base64.b64encode(requests.get(queue_object.init_image.url, stream=True).content).decode('utf-8')
                img_payload = {
                    "init_images": [
                        'data:image/png;base64,' + image
                    ],
                    "denoising_strength": queue_object.strength
                }
                payload.update(img_payload)

            # update payload if high-res fix is used
            if queue_object.highres_fix:
                highres_payload = {
                    "enable_hr": queue_object.highres_fix,
                    "denoising_strength": queue_object.strength
                }
                payload.update(highres_payload)

            # add any options that would go into the override_settings
            override_settings = {"CLIP_stop_at_last_layers": queue_object.clip_skip}
            if queue_object.facefix != 'None':
                override_settings["face_restoration_model"] = queue_object.facefix
                # face restoration needs this extra parameter
                facefix_payload = {
                    "restore_faces": True,
                }
                payload.update(facefix_payload)

            # update payload with override_settings
            override_payload = {
                "override_settings": override_settings
            }
            payload.update(override_payload)

            # send normal payload to webui
            if settings.global_var.gradio_auth:
                login_payload = {
                    'username': settings.global_var.username,
                    'password': settings.global_var.password
                }
                s.post(settings.global_var.url + '/login', data=login_payload)
            else:
                s.post(settings.global_var.url + '/login')

            # only send model payload if one is defined
            print(model_payload, payload)
            if settings.global_var.send_model:
                s.post(url=f'{settings.global_var.url}/sdapi/v1/options', json=model_payload)
            if queue_object.init_image is not None:
                response = s.post(url=f'{settings.global_var.url}/sdapi/v1/img2img', json=payload)
            else:
                response = s.post(url=f'{settings.global_var.url}/sdapi/v1/txt2img', json=payload)
            response_data = response.json()
            end_time = time.time()

            # create safe/sanitized filename
            keep_chars = (' ', '.', '_')
            file_name = "".join(c for c in queue_object.prompt if c.isalnum() or c in keep_chars).rstrip()

            # save local copy of image and prepare PIL images
            pil_images = []
            for i, image_base64 in enumerate(response_data['images']):
                image = Image.open(io.BytesIO(base64.b64decode(image_base64.split(",", 1)[0])))
                pil_images.append(image)

                # grab png info
                png_payload = {
                    "image": "data:image/png;base64," + image_base64
                }
                png_response = s.post(url=f'{settings.global_var.url}/sdapi/v1/png-info', json=png_payload)

                metadata = PngImagePlugin.PngInfo()
                epoch_time = int(time.time())
                metadata.add_text("parameters", png_response.json().get("info"))
                file_path = f'{settings.global_var.dir}/{epoch_time}-{queue_object.seed}-{file_name[0:120]}-{i}.png'
                # save json payload to file
                json_file = file_path.replace(".png", ".json")
                image_copy = file_path.replace(".png", "-watermark.png")
                with open(f'{json_file}', 'w') as f:
                    json.dump(payload, f, indent=4)
                # save png info to file
                image.save(file_path, pnginfo=metadata)
                copy_image(image, image_copy, metadata)
                print(f'Saved image: {file_path}')

            # increment number of images generated
            settings.stats_count(queue_object.batch_count)

            # post to discord
            with contextlib.ExitStack() as stack:
                buffer_handles = [stack.enter_context(io.BytesIO()) for _ in pil_images]

                image_count = len(pil_images)
                noun_descriptor = "drawing" if image_count == 1 else f'{image_count} drawings'

                for (pil_image, buffer) in zip(pil_images, buffer_handles):
                    pil_image.save(buffer, 'PNG')
                    buffer.seek(0)
                draw_time = '{0:.3f}'.format(end_time - start_time)
                message = f'my {noun_descriptor} of ``{queue_object.simple_prompt}`` took me ``{draw_time}`` ' \
                          f'seconds!\n> *{queue_object.ctx.author.name}#{queue_object.ctx.author.discriminator}*'
                files = [discord.File(fp=buffer, filename=f'{queue_object.seed}-{i}.png') for (i, buffer) in
                         enumerate(buffer_handles)]
                event_loop.create_task(
                    queue_object.ctx.channel.send(content=f'<@{queue_object.ctx.author.id}>, {message}', files=files,
                                                  view=queue_object.view))

        except Exception as e:
            embed = discord.Embed(title='txt2img failed', description=f'{e}\n{traceback.print_exc()}',
                                  color=settings.global_var.embed_color)
            event_loop.create_task(queue_object.ctx.channel.send(embed=embed))
        # check each queue for any remaining tasks
        if queuehandler.GlobalQueue.draw_q:
            event_loop.create_task(queuehandler.process_dream(self, queuehandler.GlobalQueue.draw_q.pop(0)))
        if queuehandler.GlobalQueue.upscale_q:
            upscale_dream = upscalecog.UpscaleCog(self)
            event_loop.create_task(queuehandler.process_dream(upscale_dream, queuehandler.GlobalQueue.upscale_q.pop(0)))
        if queuehandler.GlobalQueue.identify_q:
            identify_dream = identifycog.IdentifyCog(self)
            event_loop.create_task(
                queuehandler.process_dream(identify_dream, queuehandler.GlobalQueue.identify_q.pop(0)))
def copy_image(image_old, file_path, metadata):
    image = image_old.copy()

    # Open the watermark image
    watermark = Image.open(f'{settings.global_var.dir}/watermark.png')

    # Calculate the size of the watermark image
    watermark_size = watermark.size

    # Calculate the size of the pattern
    pattern_size = (image.size[0], image.size[1])

    # Create a new image to hold the pattern
    pattern_image = Image.new('RGBA', pattern_size)

    # Paste the watermark image onto the pattern image
    for i in range(0, pattern_size[0], watermark_size[0]):
        for j in range(0, pattern_size[1], watermark_size[1]):
            pattern_image.paste(watermark, (i, j))

    # Convert image to RGBA
    image = image.convert('RGBA')

    # Paste the pattern image onto the input image
    image.alpha_composite(pattern_image)
    image.save(file_path, pnginfo=metadata)

def setup(bot):
    bot.add_cog(StableCog(bot))
