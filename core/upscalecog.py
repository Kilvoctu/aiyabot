import base64
import discord
import io
import requests
import time
import traceback
from asyncio import AbstractEventLoop
from discord import option
from discord.ext import commands
from os.path import splitext, basename
from PIL import Image
from threading import Thread
from typing import Optional
from urllib.parse import urlparse

from core import queuehandler
from core import viewhandler
from core import settings
from core import settingscog


class UpscaleCog(commands.Cog):
    def __init__(self, bot):
        self.wait_message = []
        self.bot = bot
        self.file_name = ''

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(viewhandler.DeleteView(self))

    @commands.slash_command(name='upscale', description='Upscale an image', guild_only=True)
    @option(
        'init_image',
        discord.Attachment,
        description='The starter image to upscale',
        required=False,
    )
    @option(
        'init_url',
        str,
        description='The starter URL image to upscale. This overrides init_image!',
        required=False,
    )
    @option(
        'resize',
        str,
        description='The amount to upscale the image by (1.0 to 4.0).',
        required=True
    )
    @option(
        'upscaler_1',
        str,
        description='The upscaler model to use.',
        required=True,
        autocomplete=discord.utils.basic_autocomplete(settingscog.SettingsCog.upscaler_autocomplete),
    )
    @option(
        'upscaler_2',
        str,
        description='The 2nd upscaler model to use.',
        required=False,
        autocomplete=discord.utils.basic_autocomplete(settingscog.SettingsCog.upscaler_autocomplete),
    )
    @option(
        'upscaler_2_strength',
        str,
        description='The visibility of the 2nd upscaler model. (0.0 to 1.0)',
        required=False,
    )
    @option(
        'gfpgan',
        str,
        description='The visibility of the GFPGAN face restoration model. (0.0 to 1.0)',
        required=False,
    )
    @option(
        'codeformer',
        str,
        description='The visibility of the codeformer face restoration model. (0.0 to 1.0)',
        required=False,
    )
    @option(
        'upscale_first',
        bool,
        description='Do the upscale before restoring faces. Default: False',
        required=False,
    )
    async def dream_handler(self, ctx: discord.ApplicationContext, *,
                            init_image: Optional[discord.Attachment] = None,
                            init_url: Optional[str],
                            resize: str = '2.0',
                            upscaler_1: str = None,
                            upscaler_2: Optional[str] = "None",
                            upscaler_2_strength: Optional[str] = '0.5',
                            gfpgan: Optional[str] = '0.0',
                            codeformer: Optional[str] = '0.0',
                            upscale_first: Optional[bool] = False):

        # update defaults with any new defaults from settingscog
        channel = '% s' % ctx.channel.id
        settings.check(channel)
        if upscaler_1 is None:
            upscaler_1 = settings.read(channel)['upscaler_1']

        has_image = True
        # url *will* override init image for compatibility, can be changed here
        if init_url:
            try:
                init_image = requests.get(init_url)
            except(Exception,):
                await ctx.send_response('URL image not found!\nI have nothing to work with...', ephemeral=True)
                has_image = False

        # fail if no image is provided
        if init_url is None:
            if init_image is None:
                await ctx.send_response('I need an image to upscale!', ephemeral=True)
                has_image = False

        # pull the name from the image
        disassembled = urlparse(init_image.url)
        filename, file_ext = splitext(basename(disassembled.path))
        self.file_name = filename

        # formatting aiya initial reply
        reply_adds = ''
        if upscaler_2:
            reply_adds += f'\nUpscaler 2: ``{upscaler_2}``'
            reply_adds += f' - Strength: ``{upscaler_2_strength}``'

        # check if resize is within limits
        if float(resize) < 1.0:
            resize = 1.0
            reply_adds += f"\nResize can't go below 1.0x! Setting it to ``{resize}``."
        if float(resize) > 4.0:
            resize = 4.0
            reply_adds += f"\nResize can't go above 4.0x! Setting it to ``{resize}``."

        # set up tuple of parameters
        input_tuple = (ctx, resize, init_image, upscaler_1, upscaler_2, upscaler_2_strength, gfpgan, codeformer, upscale_first)
        view = viewhandler.DeleteView(input_tuple)
        # set up the queue if an image was found
        user_queue_limit = settings.queue_check(ctx.author)
        if has_image:
            if queuehandler.GlobalQueue.dream_thread.is_alive():
                if user_queue_limit == "Stop":
                    await ctx.send_response(content=f"Please wait! You're past your queue limit of {settings.global_var.queue_limit}.", ephemeral=True)
                else:
                    queuehandler.GlobalQueue.queue.append(queuehandler.UpscaleObject(self, *input_tuple, view))
            else:
                await queuehandler.process_dream(self, queuehandler.UpscaleObject(self, *input_tuple, view))
            if user_queue_limit != "Stop":
                await ctx.send_response(f'<@{ctx.author.id}>, {settings.messages()}\nQueue: ``{len(queuehandler.GlobalQueue.queue)}`` - Scale: ``{resize}``x - Upscaler: ``{upscaler_1}``{reply_adds}')

    # the function to queue Discord posts
    def post(self, event_loop: AbstractEventLoop, post_queue_object: queuehandler.PostObject):
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
    def dream(self, event_loop: AbstractEventLoop, queue_object: queuehandler.UpscaleObject):
        try:
            start_time = time.time()

            # construct a payload
            image = base64.b64encode(requests.get(queue_object.init_image.url, stream=True).content).decode('utf-8')
            payload = {
                "upscaling_resize": queue_object.resize,
                "upscaler_1": queue_object.upscaler_1,
                "image": 'data:image/png;base64,' + image,
                "gfpgan_visibility": queue_object.gfpgan,
                "codeformer_visibility": queue_object.codeformer,
                "upscale_first": queue_object.upscale_first
            }
            if queue_object.upscaler_2 is not None:
                up2_payload = {
                    "upscaler_2": queue_object.upscaler_2,
                    "extras_upscaler_2_visibility": queue_object.upscaler_2_strength
                }
                payload.update(up2_payload)

            # send normal payload to webui
            with requests.Session() as s:
                if settings.global_var.api_auth:
                    s.auth = (settings.global_var.api_user, settings.global_var.api_pass)

                if settings.global_var.gradio_auth:
                    login_payload = {
                        'username': settings.global_var.username,
                        'password': settings.global_var.password
                    }
                    s.post(settings.global_var.url + '/login', data=login_payload)
                else:
                    s.post(settings.global_var.url + '/login')

                response = s.post(url=f'{settings.global_var.url}/sdapi/v1/extra-single-image', json=payload)
            response_data = response.json()
            end_time = time.time()

            # create safe/sanitized filename
            epoch_time = int(time.time())
            file_path = f'{settings.global_var.dir}/{epoch_time}-x{queue_object.resize}-{self.file_name[0:120]}.png'

            # save local copy of image
            image_data = response_data['image']
            if settings.global_var.save_outputs == 'True':
                with open(file_path, "wb") as fh:
                    fh.write(base64.b64decode(image_data))
                print(f'Saved image: {file_path}')

            # post to discord
            def post_dream():
                with io.BytesIO() as buffer:
                    image = Image.open(io.BytesIO(base64.b64decode(image_data)))
                    image.save(buffer, 'PNG')
                    buffer.seek(0)

                    draw_time = '{0:.3f}'.format(end_time - start_time)
                    message = f'my upscale of ``{queue_object.resize}``x took me ``{draw_time}`` seconds!'
                    file = discord.File(fp=buffer, filename=file_path)

                    queuehandler.process_post(
                        self, queuehandler.PostObject(
                            self, queue_object.ctx, content=f'<@{queue_object.ctx.author.id}>, {message}', file=file, files='', embed='', view=queue_object.view))
            Thread(target=post_dream, daemon=True).start()

        except Exception as e:
            embed = discord.Embed(title='txt2img failed', description=f'{e}\n{traceback.print_exc()}',
                                  color=settings.global_var.embed_color)
            event_loop.create_task(queue_object.ctx.channel.send(embed=embed))
        # check each queue for any remaining tasks
        queuehandler.process_queue()


def setup(bot):
    bot.add_cog(UpscaleCog(bot))
