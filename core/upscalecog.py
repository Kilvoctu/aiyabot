import base64
import csv
import discord
import io
import random
import requests
import time
import traceback
from asyncio import AbstractEventLoop
from discord import option
from discord.ext import commands
from os.path import splitext, basename
from PIL import Image
from typing import Optional
from urllib.parse import urlparse

from core import queuehandler
from core import viewhandler
from core import settings
from core import stablecog
from core import identifycog


class UpscaleCog(commands.Cog):
    def __init__(self, bot):
        self.wait_message = []
        self.bot = bot
        self.file_name = ''

    @commands.slash_command(name='upscale', description='Upscale an image')
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
        float,
        description='The amount to upscale the image by (1.0 to 4.0).',
        min_value=1,
        max_value=4,
        required=True,
    )
    @option(
        'upscaler_1',
        str,
        description='The upscaler model to use.',
        required=True,
        choices=['None', 'Lanczos', 'Nearest', 'LDSR', 'ESRGAN_4x', 'ScuNET GAN', 'ScuNET PSNR', 'SwinIR_4x'],
    )
    @option(
        'upscaler_2',
        str,
        description='The 2nd upscaler model to use.',
        required=False,
        choices=['None', 'Lanczos', 'Nearest', 'LDSR', 'ESRGAN_4x', 'ScuNET GAN', 'ScuNET PSNR', 'SwinIR_4x'],
    )
    @option(
        'upscaler_2_strength',
        float,
        description='The visibility of the 2nd upscaler model. (0.0 to 1.0)',
        required=False,
    )
    async def dream_handler(self, ctx: discord.ApplicationContext, *,
                            init_image: Optional[discord.Attachment] = None,
                            init_url: Optional[str],
                            resize: float = 2.0,
                            upscaler_1: str = "None",
                            upscaler_2: Optional[str] = "None",
                            upscaler_2_strength: Optional[float] = 0.5):

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

        # random messages for aiya to say
        with open('resources/messages.csv') as csv_file:
            message_data = list(csv.reader(csv_file, delimiter='|'))
            message_row_count = len(message_data) - 1
            for row in message_data:
                self.wait_message.append(row[0])

        # formatting aiya initial reply
        reply_adds = ''
        if upscaler_2:
            reply_adds = reply_adds + f'\nUpscaler 2: ``{upscaler_2}``'
            reply_adds = reply_adds + f' - Strength: ``{upscaler_2_strength}``'

        view = viewhandler.DeleteView(ctx.author.id)
        # set up tuple of queues to pass into union()
        queues = (queuehandler.GlobalQueue.draw_q, queuehandler.GlobalQueue.upscale_q, queuehandler.GlobalQueue.identify_q)
        # set up the queue if an image was found
        if has_image:
            if queuehandler.GlobalQueue.dream_thread.is_alive():
                user_already_in_queue = False
                for queue_object in queuehandler.union(*queues):
                    if queue_object.ctx.author.id == ctx.author.id:
                        user_already_in_queue = True
                        break
                if user_already_in_queue:
                    await ctx.send_response(content=f'Please wait! You\'re queued up.', ephemeral=True)
                else:
                    queuehandler.GlobalQueue.upscale_q.append(
                        queuehandler.UpscaleObject(ctx, resize, init_image, upscaler_1, upscaler_2, upscaler_2_strength,
                                                   view))
                    await ctx.send_response(
                        f'<@{ctx.author.id}>, {self.wait_message[random.randint(0, message_row_count)]}\nQueue: ``{len(queuehandler.union(*queues))}`` - Scale: ``{resize}``x - Upscaler: ``{upscaler_1}``{reply_adds}')
            else:
                await queuehandler.process_dream(self, queuehandler.UpscaleObject(ctx, resize, init_image, upscaler_1,
                                                                                  upscaler_2, upscaler_2_strength,
                                                                                  view))
                await ctx.send_response(
                    f'<@{ctx.author.id}>, {self.wait_message[random.randint(0, message_row_count)]}\nQueue: ``{len(queuehandler.union(*queues))}`` - Scale: ``{resize}``x - Upscaler: ``{upscaler_1}``{reply_adds}')

    # generate the image
    def dream(self, event_loop: AbstractEventLoop, queue_object: queuehandler.UpscaleObject):
        try:
            start_time = time.time()

            # construct a payload
            image = base64.b64encode(requests.get(queue_object.init_image.url, stream=True).content).decode('utf-8')
            payload = {
                "upscaling_resize": queue_object.resize,
                "upscaler_1": queue_object.upscaler_1,
                "image": 'data:image/png;base64,' + image
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
            with open(file_path, "wb") as fh:
                fh.write(base64.b64decode(image_data))
            print(f'Saved image: {file_path}')

            # post to discord
            with io.BytesIO() as buffer:
                image = Image.open(io.BytesIO(base64.b64decode(image_data)))
                image.save(buffer, 'PNG')
                buffer.seek(0)
                embed = discord.Embed()

                embed.colour = settings.global_var.embed_color
                embed.add_field(name=f'My upscale of', value=f'``{queue_object.resize}``x', inline=False)
                embed.add_field(name='took me', value='``{0:.3f}`` seconds'.format(end_time - start_time), inline=False)

                footer_args = dict(text=f'{queue_object.ctx.author.name}#{queue_object.ctx.author.discriminator}')
                if queue_object.ctx.author.avatar is not None:
                    footer_args['icon_url'] = queue_object.ctx.author.avatar.url
                embed.set_footer(**footer_args)

                event_loop.create_task(
                    queue_object.ctx.channel.send(content=f'<@{queue_object.ctx.author.id}>', embed=embed,
                                                  file=discord.File(fp=buffer, filename=file_path),
                                                  view=queue_object.view))

        except Exception as e:
            embed = discord.Embed(title='txt2img failed', description=f'{e}\n{traceback.print_exc()}',
                                  color=settings.global_var.embed_color)
            event_loop.create_task(queue_object.ctx.channel.send(embed=embed))
        # check each queue for any remaining tasks
        if queuehandler.GlobalQueue.draw_q:
            draw_dream = stablecog.StableCog(self)
            event_loop.create_task(queuehandler.process_dream(draw_dream, queuehandler.GlobalQueue.draw_q.pop(0)))
        if queuehandler.GlobalQueue.upscale_q:
            event_loop.create_task(queuehandler.process_dream(self, queuehandler.GlobalQueue.upscale_q.pop(0)))
        if queuehandler.GlobalQueue.identify_q:
            identify_dream = identifycog.IdentifyCog(self)
            event_loop.create_task(
                queuehandler.process_dream(identify_dream, queuehandler.GlobalQueue.identify_q.pop(0)))


def setup(bot):
    bot.add_cog(UpscaleCog(bot))
