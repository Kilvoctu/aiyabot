import base64
import contextlib
import csv
import io
import random
import time
import traceback
from asyncio import AbstractEventLoop
from typing import Optional
import discord
import requests
from PIL import Image, PngImagePlugin
from discord import option
from discord.ext import commands
from discord.ui import View

from core import queuehandler
from core import settings
from core import upscalecog
from core import identifycog

async def test_button():
    print("Buttons!")
class MyView(discord.ui.View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user

    @discord.ui.button(
        custom_id="button_reroll",
        emoji="🎲")
    async def button_callback(self, button, interaction):
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await test_button()

    @discord.ui.button(
        custom_id="button_x",
        emoji="❌")
    async def delete(self, button, interaction):
        print(interaction.user.id)
        print(self.user)
        if interaction.user.id == self.user:
            await interaction.message.delete()
        else:
            await interaction.response.send_message("You can't delete other people's images!", ephemeral=True)

class StableCog(commands.Cog, name='Stable Diffusion', description='Create images from natural language.'):
    ctx_parse = discord.ApplicationContext
    def __init__(self, bot):
        self.wait_message = []
        self.bot = bot
        self.send_model = False

    #pulls from model_names list and makes some sort of dynamic list to bypass Discord 25 choices limit
    def model_autocomplete(self: discord.AutocompleteContext):
        return [
            model for model in settings.global_var.model_names
        ]
    #and for styles
    def style_autocomplete(self: discord.AutocompleteContext):
        return [
            style for style in settings.global_var.style_names
        ]

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
        description='Tries to improve faces in pictures.',
        required=False,
        choices=settings.global_var.facefix_models,
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
                            init_url: Optional[str],
                            count: Optional[int] = None,
                            style: Optional[str] = 'None',
                            facefix: Optional[str] = 'None'):

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

        #if a model is not selected, do nothing
        model_name = 'Default'
        if data_model is None:
            data_model = settings.read(guild)['data_model']
            if data_model != '':
                self.send_model = True
        else:
            self.send_model = True

        simple_prompt = prompt
        #take selected data_model and get model_name, then update data_model with the full name
        with open('resources/models.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='|')
            for row in reader:
                if row['display_name'] == data_model:
                    model_name = row['display_name']
                    data_model = row['model_full_name']
                    #look at the model for activator token and prepend prompt with it
                    prompt = row['activator_token'] + " " + prompt
                    #if there's no activator token, remove the extra blank space
                    prompt = prompt.lstrip(' ')

        if not self.send_model:
            print(f'Request -- {ctx.author.name}#{ctx.author.discriminator} -- Prompt: {prompt}')
        else:
            print(f'Request -- {ctx.author.name}#{ctx.author.discriminator} -- Prompt: {prompt} -- Using model: {data_model}')

        if seed == -1: seed = random.randint(0, 0xFFFFFFFF)

        #url *will* override init image for compatibility, can be changed here
        if init_url:
            try:
                init_image = requests.get(init_url)
            except(Exception,):
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
            append_options = append_options + '\nURL Init Image: ``' + str(init_image.url) + '``'
        if count != 1:
            max_count = settings.read(guild)['max_count']
            if count > max_count:
                count = max_count
                append_options = append_options + '\nExceeded maximum of ``' + str(count) + '`` images! This is the best I can do...'
            append_options = append_options + '\nCount: ``' + str(count) + '``'
        if style != 'None':
            append_options = append_options + '\nStyle: ``' + str(style) + '``'
        if facefix != 'None':
            append_options = append_options + '\nFace restoration: ``' + str(facefix) + '``'

        #log the command
        copy_command = f'/draw prompt:{simple_prompt} steps:{steps} height:{str(height)} width:{width} guidance_scale:{guidance_scale} sampler:{sampler} seed:{seed} count:{count}'
        if negative_prompt != '':
            copy_command = copy_command + f' negative_prompt:{negative_prompt}'
        if data_model:
            copy_command = copy_command + f' data_model:{model_name}'
        if init_image:
            copy_command = copy_command + f' strength:{strength} init_url:{init_image.url}'
        if style != 'None':
            copy_command = copy_command + f' style:{style}'
        if facefix != 'None':
            copy_command = copy_command + f' facefix:{facefix}'
        print(copy_command)

        #setup the queue
        if queuehandler.GlobalQueue.dream_thread.is_alive():
            user_already_in_queue = False
            for queue_object in queuehandler.union(queuehandler.GlobalQueue.draw_q, queuehandler.GlobalQueue.upscale_q, queuehandler.GlobalQueue.identify_q):
                if queue_object.ctx.author.id == ctx.author.id:
                    user_already_in_queue = True
                    break
            if user_already_in_queue:
                await ctx.send_response(content=f'Please wait! You\'re queued up.', ephemeral=True)
            else:
                queuehandler.GlobalQueue.draw_q.append(queuehandler.DrawObject(ctx, prompt, negative_prompt, data_model, steps, height, width, guidance_scale, sampler, seed, strength, init_image, copy_command, count, style, facefix, simple_prompt), MyView())
                await ctx.send_response(f'<@{ctx.author.id}>, {self.wait_message[random.randint(0, message_row_count)]}\nQueue: ``{len(queuehandler.union(queuehandler.GlobalQueue.draw_q, queuehandler.GlobalQueue.upscale_q, queuehandler.GlobalQueue.identify_q))}`` - ``{simple_prompt}``\nSteps: ``{steps}`` - Seed: ``{seed}``{append_options}')
        else:
            await queuehandler.process_dream(self, queuehandler.DrawObject(ctx, prompt, negative_prompt, data_model, steps, height, width, guidance_scale, sampler, seed, strength, init_image, copy_command, count, style, facefix, simple_prompt), MyView())
            await ctx.send_response(f'<@{ctx.author.id}>, {self.wait_message[random.randint(0, message_row_count)]}\nQueue: ``{len(queuehandler.union(queuehandler.GlobalQueue.draw_q, queuehandler.GlobalQueue.upscale_q, queuehandler.GlobalQueue.identify_q))}`` - ``{simple_prompt}``\nSteps: ``{steps}`` - Seed: ``{seed}``{append_options}')

    #generate the image
    def dream(self, event_loop: AbstractEventLoop, queue_object: queuehandler.DrawObject, my_view: View):
        try:
            start_time = time.time()

            #construct a payload for data model, then the normal payload
            model_payload = {
                "fn_index": settings.global_var.model_fn_index,
                "data": [
                    queue_object.data_model
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
                "n_iter": queue_object.batch_count,
                "styles": [
                    queue_object.style
                ]
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
            if queue_object.facefix != 'None':
                facefix_payload = {
                    "restore_faces": True,
                    "override_settings": {
                        "face_restoration_model": queue_object.facefix
                    }
                }
                payload.update(facefix_payload)

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

                #only send model payload if one is defined
                if self.send_model:
                    s.post(url=f'{settings.global_var.url}/api/predict', json=model_payload)
                if queue_object.init_image is not None:
                    response = s.post(url=f'{settings.global_var.url}/sdapi/v1/img2img', json=payload)
                else:
                    response = s.post(url=f'{settings.global_var.url}/sdapi/v1/txt2img', json=payload)
            response_data = response.json()
            end_time = time.time()

            #create safe/sanitized filename
            keep_chars = (' ', '.', '_')
            file_name = "".join(c for c in queue_object.prompt if c.isalnum() or c in keep_chars).rstrip()

            # save local copy of image and prepare PIL images
            pil_images = []
            for i, image_base64 in enumerate(response_data['images']):
                image = Image.open(io.BytesIO(base64.b64decode(image_base64.split(",",1)[0])))
                pil_images.append(image)

                #grab png info
                png_payload = {
                    "image": "data:image/png;base64," + image_base64
                }
                png_response = requests.post(url=f'{settings.global_var.url}/sdapi/v1/png-info', json=png_payload)

                metadata = PngImagePlugin.PngInfo()
                epoch_time = int(time.time())
                metadata.add_text("parameters", png_response.json().get("info"))
                file_path = f'{settings.global_var.dir}/{epoch_time}-{queue_object.seed}-{file_name[0:120]}-{i}.png'
                image.save(file_path, pnginfo=metadata)
                print(f'Saved image: {file_path}')

            # post to discord
            with contextlib.ExitStack() as stack:
                buffer_handles = [stack.enter_context(io.BytesIO()) for _ in pil_images]

                embed = discord.Embed()
                embed.colour = settings.global_var.embed_color

                image_count = len(pil_images)
                noun_descriptor = "drawing" if image_count == 1 else f'{image_count} drawings'
                value = queue_object.copy_command if settings.global_var.copy_command else queue_object.simple_prompt
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

                event_loop.create_task(queue_object.ctx.channel.send(content=f'<@{queue_object.ctx.author.id}>', embed=embed, files=files, view=my_view))

        except Exception as e:
            embed = discord.Embed(title='txt2img failed', description=f'{e}\n{traceback.print_exc()}',
                                  color=settings.global_var.embed_color)
            event_loop.create_task(queue_object.ctx.channel.send(embed=embed))
        #check each queue for any remaining tasks
        if queuehandler.GlobalQueue.draw_q:
            event_loop.create_task(queuehandler.process_dream(self, queuehandler.GlobalQueue.draw_q.pop(0), my_view))
        if queuehandler.GlobalQueue.upscale_q:
            upscale_dream = upscalecog.UpscaleCog(self)
            event_loop.create_task(queuehandler.process_dream(upscale_dream, queuehandler.GlobalQueue.upscale_q.pop(0)))
        if queuehandler.GlobalQueue.identify_q:
            identify_dream = identifycog.IdentifyCog(self)
            event_loop.create_task(queuehandler.process_dream(identify_dream, queuehandler.GlobalQueue.identify_q.pop(0)))

def setup(bot):
    bot.add_cog(StableCog(bot))
