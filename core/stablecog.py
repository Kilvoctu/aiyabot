import base64
import discord
import io
import math
import random
import requests
import time
import traceback
from PIL import Image, PngImagePlugin
from discord import option
from discord.ext import commands
from typing import Optional

from core import queuehandler
from core import viewhandler
from core import settings
from core import settingscog


class StableCog(commands.Cog, name='Stable Diffusion', description='Create images from natural language.'):
    ctx_parse = discord.ApplicationContext

    def __init__(self, bot):
        self.bot = bot

    if len(settings.global_var.size_range) == 0:
        size_auto = discord.utils.basic_autocomplete(settingscog.SettingsCog.size_autocomplete)
    else:
        size_auto = None

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(viewhandler.DrawView(self))

    @commands.slash_command(name='draw', description='Create an image', guild_only=True)
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
        description='Select the data model for image generation.',
        required=False,
        autocomplete=discord.utils.basic_autocomplete(settingscog.SettingsCog.model_autocomplete),
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
        description='Width of the generated image.',
        required=False,
        autocomplete=size_auto,
        choices=settings.global_var.size_range
    )
    @option(
        'height',
        int,
        description='Height of the generated image.',
        required=False,
        autocomplete=size_auto,
        choices=settings.global_var.size_range
    )
    @option(
        'guidance_scale',
        str,
        description='Classifier-Free Guidance scale.',
        required=False,
    )
    @option(
        'sampler',
        str,
        description='The sampler to use for generation.',
        required=False,
        choices=settings.global_var.sampler_names,
    )
    @option(
        'seed',
        int,
        description='The seed to use for reproducibility.',
        required=False,
    )
    @option(
        'styles',
        str,
        description='Apply a predefined style to the generation.',
        required=False,
        autocomplete=discord.utils.basic_autocomplete(settingscog.SettingsCog.style_autocomplete),
    )
    @option(
        'extra_net',
        str,
        description='Apply an extra network to influence the output. To set multiplier, add :# (# = 0.0 - 1.0)',
        required=False,
        autocomplete=discord.utils.basic_autocomplete(settingscog.SettingsCog.extra_net_autocomplete),
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
        str,
        description='Tries to fix issues from generating high-res images. Recommended: Latent (nearest).',
        required=False,
        autocomplete=discord.utils.basic_autocomplete(settingscog.SettingsCog.hires_autocomplete),
    )
    @option(
        'clip_skip',
        int,
        description='Number of last layers of CLIP model to skip.',
        required=False,
        choices=[x for x in range(1, 13, 1)]
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
        'batch',
        str,
        description='The number of images to generate. Batch format: count,size',
        required=False,
    )
    async def dream_handler(self, ctx: discord.ApplicationContext, *,
                            prompt: str, negative_prompt: str = None,
                            data_model: Optional[str] = None,
                            steps: Optional[int] = None,
                            width: Optional[int] = None, height: Optional[int] = None,
                            guidance_scale: Optional[str] = None,
                            sampler: Optional[str] = None,
                            seed: Optional[int] = -1,
                            styles: Optional[str] = None,
                            extra_net: Optional[str] = None,
                            facefix: Optional[str] = None,
                            highres_fix: Optional[str] = None,
                            clip_skip: Optional[int] = None,
                            strength: Optional[str] = None,
                            init_image: Optional[discord.Attachment] = None,
                            init_url: Optional[str],
                            batch: Optional[str] = None):

        # update defaults with any new defaults from settingscog
        channel = '% s' % ctx.channel.id
        settings.check(channel)
        if negative_prompt is None:
            negative_prompt = settings.read(channel)['negative_prompt']
        if steps is None:
            steps = settings.read(channel)['steps']
        if width is None:
            width = settings.read(channel)['width']
        if height is None:
            height = settings.read(channel)['height']
        if guidance_scale is None:
            guidance_scale = settings.read(channel)['guidance_scale']
        if sampler is None:
            sampler = settings.read(channel)['sampler']
        if styles is None:
            styles = settings.read(channel)['style']
        if facefix is None:
            facefix = settings.read(channel)['facefix']
        if highres_fix is None:
            highres_fix = settings.read(channel)['highres_fix']
        if clip_skip is None:
            clip_skip = settings.read(channel)['clip_skip']
        if strength is None:
            strength = settings.read(channel)['strength']
        if batch is None:
            batch = settings.read(channel)['batch']

        # if a model is not selected, do nothing
        model_name = 'Default'
        if data_model is None:
            data_model = settings.read(channel)['data_model']

        simple_prompt = prompt
        # run through mod function if any moderation values are set in config
        clean_negative = negative_prompt
        if settings.global_var.prompt_ban_list or settings.global_var.prompt_ignore_list or settings.global_var.negative_prompt_prefix:
            mod_results = settings.prompt_mod(simple_prompt, negative_prompt)
            if mod_results[0] == "Stop":
                await ctx.respond(f"I'm not allowed to draw the word {mod_results[1]}!", ephemeral=True)
                return
            if mod_results[0] == "Mod":
                if settings.global_var.display_ignored_words == "False":
                    simple_prompt = mod_results[1]
                prompt = mod_results[1]
                negative_prompt = mod_results[2]
                clean_negative = mod_results[3]

        # take selected data_model and get model_name, then update data_model with the full name
        for model in settings.global_var.model_info.items():
            if model[0] == data_model:
                model_name = model[0]
                data_model = model[1][0]
                # look at the model for activator token and prepend prompt with it
                if model[1][3]:
                    prompt = model[1][3] + " " + prompt
                break

        net_multi = 0.85
        if extra_net is not None:
            prompt, extra_net, net_multi = settings.extra_net_check(prompt, extra_net, net_multi)
        prompt = settings.extra_net_defaults(prompt, channel)

        if data_model != '':
            print(f'Request -- {ctx.author.name}#{ctx.author.discriminator} -- Prompt: {prompt}')
        else:
            print(f'Request -- {ctx.author.name}#{ctx.author.discriminator} -- Prompt: {prompt} -- Using model: {data_model}')

        if seed == -1:
            seed = random.randint(0, 0xFFFFFFFF)

        # url *will* override init image for compatibility, can be changed here
        if init_url:
            try:
                init_image = requests.get(init_url)
            except(Exception,):
                await ctx.send_response('URL image not found!\nI will do my best without it!')

        # verify values and format aiya initial reply
        reply_adds = ''
        if (width != 512) or (height != 512):
            reply_adds += f' - Size: ``{width}``x``{height}``'
        reply_adds += f' - Seed: ``{seed}``'

        # lower step value to the highest setting if user goes over max steps
        if steps > settings.read(channel)['max_steps']:
            steps = settings.read(channel)['max_steps']
            reply_adds += f'\nExceeded maximum of ``{steps}`` steps! This is the best I can do...'
        if model_name != 'Default':
            reply_adds += f'\nModel: ``{model_name}``'
        if clean_negative != settings.read(channel)['negative_prompt']:
            reply_adds += f'\nNegative Prompt: ``{clean_negative}``'
        if guidance_scale != settings.read(channel)['guidance_scale']:
            # try to convert string to Web UI-friendly float
            try:
                guidance_scale = guidance_scale.replace(",", ".")
                float(guidance_scale)
                reply_adds += f'\nGuidance Scale: ``{guidance_scale}``'
            except(Exception,):
                reply_adds += f"\nGuidance Scale can't be ``{guidance_scale}``! Setting to default of `7.0`."
                guidance_scale = 7.0
        if sampler != settings.read(channel)['sampler']:
            reply_adds += f'\nSampler: ``{sampler}``'
        if init_image:
            # try to convert string to Web UI-friendly float
            try:
                strength = strength.replace(",", ".")
                float(strength)
                reply_adds += f'\nStrength: ``{strength}``'
            except(Exception,):
                reply_adds += f"\nStrength can't be ``{strength}``! Setting to default of `0.75`."
                strength = 0.75
            reply_adds += f'\nURL Init Image: ``{init_image.url}``'
        # try to convert batch to usable format
        batch_check = settings.batch_format(batch)
        batch = list(batch_check)
        if batch[0] != 1 or batch[1] != 1:
            max_batch = settings.batch_format(settings.read(channel)['max_batch'])
            # if only one number is provided, try to generate the requested amount, prioritizing batch size
            if batch[2] == 1:
                # if over the limits, cut the number in half and let AIYA scale down
                total = max_batch[0] * max_batch[1]
                if batch[0] > total:
                    batch[0] = math.ceil(batch[0] / 2)
                    batch[1] = math.ceil(batch[0] / 2)
                else:
                    # do... math
                    difference = math.ceil(batch[0] / max_batch[1])
                    multiple = int(batch[0] / difference)
                    new_total = difference * multiple
                    requested = batch[0]
                    batch[0], batch[1] = difference, multiple
                    if requested % difference != 0:
                        reply_adds += f"\nI can't draw exactly ``{requested}`` pictures! Settling for ``{new_total}``."
            # check batch values against the maximum limits
            if batch[0] > max_batch[0]:
                reply_adds += f"\nThe max batch count I'm allowed here is ``{max_batch[0]}``!"
                batch[0] = max_batch[0]
            if batch[1] > max_batch[1]:
                reply_adds += f"\nThe max batch size I'm allowed here is ``{max_batch[1]}``!"
                batch[1] = max_batch[1]
            reply_adds += f'\nBatch count: ``{batch[0]}`` - Batch size: ``{batch[1]}``'
        if styles != settings.read(channel)['style']:
            reply_adds += f'\nStyle: ``{styles}``'
        if extra_net is not None and extra_net != 'None':
            reply_adds += f'\nExtra network: ``{extra_net}``'
            if net_multi != 0.85:
                reply_adds += f' (multiplier: ``{net_multi}``)'
        if facefix != settings.read(channel)['facefix']:
            reply_adds += f'\nFace restoration: ``{facefix}``'
        if clip_skip != settings.read(channel)['clip_skip']:
            reply_adds += f'\nCLIP skip: ``{clip_skip}``'
            
        epoch_time = int(time.time())

        # set up tuple of parameters to pass into the Discord view
        input_tuple = (
            ctx, simple_prompt, prompt, negative_prompt, data_model, steps, width, height, guidance_scale, sampler, seed, strength,
            init_image, batch, styles, facefix, highres_fix, clip_skip, extra_net, epoch_time)
        
        view = viewhandler.DrawView(input_tuple)
        # setup the queue
        user_queue_limit = settings.queue_check(ctx.author)
        if queuehandler.GlobalQueue.dream_thread.is_alive():
            if user_queue_limit == "Stop":
                await ctx.send_response(content=f"Please wait! You're past your queue limit of {settings.global_var.queue_limit}.", ephemeral=True)
            else:
                queuehandler.GlobalQueue.queue.append(queuehandler.DrawObject(self, *input_tuple, view))
        else:
            await queuehandler.process_dream(self, queuehandler.DrawObject(self, *input_tuple, view))
        if user_queue_limit != "Stop":
            await ctx.send_response(f'<@{ctx.author.id}>, {settings.messages()}\nQueue: ``{len(queuehandler.GlobalQueue.queue)}`` - ``{simple_prompt}``\nSteps: ``{steps}``{reply_adds}')

    # the function to queue Discord posts
    def post(self, event_loop: queuehandler.GlobalQueue.post_event_loop, post_queue_object: queuehandler.PostObject):
        event_loop.create_task(
            post_queue_object.ctx.channel.send(
                content=post_queue_object.content,
                file=post_queue_object.file,
                view=post_queue_object.view
            )
        )
        if queuehandler.GlobalQueue.post_queue:
            self.post(self.event_loop, self.queue.pop(0))

    # generate the image
    def dream(self, event_loop: queuehandler.GlobalQueue.event_loop, queue_object: queuehandler.DrawObject):
        try:
            start_time = time.time()

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
                "seed_resize_from_h": -1,
                "seed_resize_from_w": -1,
                "denoising_strength": None,
                "n_iter": queue_object.batch[0],
                "batch_size": queue_object.batch[1],
                "styles": [
                    queue_object.styles
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
            if queue_object.highres_fix != 'Disabled':
                highres_payload = {
                    "enable_hr": True,
                    "hr_upscaler": queue_object.highres_fix,
                    "hr_scale": 1,
                    "hr_second_pass_steps": int(queue_object.steps)/2,
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

            # send normal payload to webui and only send model payload if one is defined
            s = settings.authenticate_user()

            if queue_object.data_model != '':
                s.post(url=f'{settings.global_var.url}/sdapi/v1/options', json=model_payload)
            if queue_object.init_image is not None:
                response = s.post(url=f'{settings.global_var.url}/sdapi/v1/img2img', json=payload)
            else:
                response = s.post(url=f'{settings.global_var.url}/sdapi/v1/txt2img', json=payload)
            response_data = response.json()
            end_time = time.time()

            # create safe/sanitized filename
            keep_chars = (' ', '.', '_')
            file_name = "".join(c for c in queue_object.simple_prompt if c.isalnum() or c in keep_chars).rstrip()
            epoch_time = queue_object.epoch_time

            # save local copy of image and prepare PIL images
            image_data = response_data['images']
            count = 0
            image_count = len(image_data)
            batch = False

            # setup batch params
            if queue_object.batch[0] > 1 or queue_object.batch[1] > 1:
                batch = True
                grids = []
                images = []
                aspect_ratio = queue_object.width / queue_object.height
                num_grids = math.ceil(image_count / 25)
                grid_count = 25 if num_grids > 1 else image_count
                last_grid_count = image_count % 25
                if num_grids > 1 and image_count % 25 == 0:
                    last_grid_count = 25

                if aspect_ratio <= 1:
                    grid_cols = int(math.ceil(math.sqrt(grid_count)))
                    grid_rows = math.ceil(grid_count / grid_cols)
                    if last_grid_count > 0:
                        last_grid_cols = int(math.ceil(math.sqrt(last_grid_count)))
                        last_grid_rows = math.ceil(last_grid_count / last_grid_cols)
                else:
                    grid_rows = int(math.ceil(math.sqrt(grid_count)))
                    grid_cols = math.ceil(grid_count / grid_rows)
                    if last_grid_count > 0:
                        last_grid_rows = int(math.ceil(math.sqrt(last_grid_count)))
                        last_grid_cols = math.ceil(last_grid_count / last_grid_rows)

                for i in range(num_grids):
                    if i == num_grids:
                        continue
                    
                    if i < num_grids - 1 or last_grid_count == 0:
                        width = grid_cols * queue_object.width
                        height = grid_rows * queue_object.height
                    else: 
                        width = last_grid_cols * queue_object.width
                        height = last_grid_rows * queue_object.height
                    image = Image.new('RGB', (width, height))
                    grids.append(image)

            for i in image_data:
                count += 1
                image = Image.open(io.BytesIO(base64.b64decode(i)))

                # grab png info
                png_payload = {
                    "image": "data:image/png;base64," + i
                }
                png_response = s.post(url=f'{settings.global_var.url}/sdapi/v1/png-info', json=png_payload)

                metadata = PngImagePlugin.PngInfo()
                metadata.add_text("parameters", png_response.json().get("info"))
                str_parameters = png_response.json().get("info")

                file_path = f'{settings.global_var.dir}/{epoch_time}-{queue_object.seed}-{count}.png'

                # if we are using a batch we need to save the files to disk
                if settings.global_var.save_outputs == 'True' or batch == True:
                    image.save(file_path, pnginfo=metadata)
                    print(f'Saved image: {file_path}')

                if batch == True:
                    image_data = (image, file_path, str_parameters)
                    images.append(image_data)
                    
                settings.stats_count(1)

                # increment seed for view when using batch
                if count != len(image_data):
                    batch_seed = list(queue_object.view.input_tuple)
                    batch_seed[10] += 1
                    new_tuple = tuple(batch_seed)
                    queue_object.view.input_tuple = new_tuple

            # set up discord message
            content = f'> for {queue_object.ctx.author.name}'
            noun_descriptor = "drawing" if image_count == 1 else f'{image_count} drawings'
            draw_time = '{0:.3f}'.format(end_time - start_time)
            message = f'my {noun_descriptor} of ``{queue_object.simple_prompt}`` took me ``{draw_time}`` seconds!'

            view = queue_object.view

            if batch == True:
                current_grid = 0
                grid_index = 0
                for grid_image in images:
                    if grid_index >= grid_count:
                        grid_index = 0
                        current_grid += 1

                    if current_grid < num_grids - 1 or last_grid_count == 0:
                        grid_y, grid_x = divmod(grid_index, grid_cols)
                        grid_x *= queue_object.width
                        grid_y *= queue_object.height
                    else:
                        grid_y, grid_x = divmod(grid_index, last_grid_cols)
                        grid_x *= queue_object.width
                        grid_y *= queue_object.height

                    grids[current_grid].paste(grid_image[0], (grid_x, grid_y))
                    grid_index += 1

                
                current_grid = 0
                for grid in grids:
                    if current_grid < num_grids -1 or last_grid_count == 0:
                        id_start = current_grid * grid_count + 1
                        id_end = id_start + grid_count - 1
                    else:
                        id_start = current_grid * grid_count + 1
                        id_end = id_start + last_grid_count - 1
                    filename=f'{queue_object.seed}-{current_grid}.png'
                    file = add_metadata_to_image(grid,images[current_grid * 25][2], filename)
                    if current_grid == 0:
                        content = f'<@{queue_object.ctx.author.id}>, {message}\n Batch ID: {epoch_time}-{queue_object.seed}\n Image IDs: {id_start}-{id_end}'
                    else:
                        content = f'> for {queue_object.ctx.author.name}, use /info or context menu to retrieve.\n Batch ID: {epoch_time}-{queue_object.seed}\n Image IDs: {id_start}-{id_end}'
                        view = None
                        
                    current_grid += 1
                    # post discord message
                    queuehandler.process_post(
                        self, queuehandler.PostObject(
                            self, queue_object.ctx, content=content, file=file, embed='', view=view))
            
            else:
                content = f'<@{queue_object.ctx.author.id}>, {message}'
                filename=f'{queue_object.seed}-{count}.png'
                file = add_metadata_to_image(image,str_parameters, filename)
                queuehandler.process_post(
                    self, queuehandler.PostObject(
                        self, queue_object.ctx, content=content, file=file, embed='', view=view))

        except KeyError as e:
            embed = discord.Embed(title='txt2img failed', description=f'An invalid parameter was found!\n{e}',
                                  color=settings.global_var.embed_color)
            event_loop.create_task(queue_object.ctx.channel.send(embed=embed))
        except Exception as e:
            embed = discord.Embed(title='txt2img failed', description=f'{e}\n{traceback.print_exc()}',
                                  color=settings.global_var.embed_color)
            event_loop.create_task(queue_object.ctx.channel.send(embed=embed))
        # check each queue for any remaining tasks
        queuehandler.process_queue()


def setup(bot):
    bot.add_cog(StableCog(bot))

def add_metadata_to_image(image, str_parameters, filename):
    with io.BytesIO() as buffer:
        # setup metadata
        metadata = PngImagePlugin.PngInfo()
        metadata.add_text("parameters", str_parameters)
        # save image to buffer
        image.save(buffer, 'PNG', pnginfo=metadata)

        # reset buffer to beginning and return as bytes
        buffer.seek(0)
        file = discord.File(fp=buffer, filename=filename)

    return file
