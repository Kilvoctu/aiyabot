import base64
import discord
import csv
import io
import random
import requests
import time
import traceback
from asyncio import AbstractEventLoop
from typing import Optional
from discord import option
from discord.ext import commands
from PIL import Image

from core import queuehandler
from core import settings


class UpscaleCog(commands.Cog):
    def __init__(self, bot):
        self.wait_message = []
        self.bot = bot

    @commands.slash_command(name = 'upscale', description = 'Upscale an image')
    @option(
        'resize',
        float,
        description='The amount to upscale the image by (1.0 to 4.0).',
        required=True,
    )
    @option(
        'init_image',
        discord.Attachment,
        description='The starter image to  upscale',
        required=False,
    )
    @option(
        'init_url',
        str,
        description='The starter URL image to upscale. This overrides init_image!',
        required=False,
    )
    @option(
        'upscaler_1',
        str,
        description='The upscaler model to use.',
        required=True,
    )
    async def dream_handler(self, ctx: discord.ApplicationContext, *,
                            resize: float = 2.0,
                            init_image: Optional[discord.Attachment] = None,
                            init_url: Optional[str],
                            upscaler_1: str = "None"):

        #url *will* override init image for compatibility, can be changed here
        if init_url:
            try:
                init_image = requests.get(init_url)
            except(Exception,):
                await ctx.send_response('URL image not found!\nI will do my best without it!')

        #random messages for bot to say
        with open('resources/messages.csv') as csv_file:
            message_data = list(csv.reader(csv_file, delimiter='|'))
            message_row_count = len(message_data) - 1
            for row in message_data:
                self.wait_message.append( row[0] )

        #formatting bot initial reply
        append_options = ''

        #setup the queue
        if queuehandler.GlobalQueue.dream_thread.is_alive():
            user_already_in_queue = False
            for queue_object in queuehandler.GlobalQueue.queue:
                if queue_object.ctx.author.id == ctx.author.id:
                    user_already_in_queue = True
                    break
            if user_already_in_queue:
                await ctx.send_response(content=f'Please wait! You\'re queued up.', ephemeral=True)
            else:
                queuehandler.GlobalQueue.queue.append(queuehandler.UpscaleObject(ctx, resize, init_image, upscaler_1))
                await ctx.send_response(f'<@{ctx.author.id}>, {self.wait_message[random.randint(0, message_row_count)]}\nQueue: ``{len(queuehandler.GlobalQueue.queue)}`` - Resize: ``{resize}``{append_options}')
        else:
            await queuehandler.process_dream(self, queuehandler.UpscaleObject(ctx, resize, init_image, upscaler_1))
            await ctx.send_response(f'<@{ctx.author.id}>, {self.wait_message[random.randint(0, message_row_count)]}\nQueue: ``{len(queuehandler.GlobalQueue.queue)}`` - Resize: ``{resize}``{append_options}')

    #generate the image
    def dream(self, event_loop: AbstractEventLoop, queue_object: queuehandler.UpscaleObject):
        try:
            start_time = time.time()

            #construct a payload
            image = base64.b64encode(requests.get(queue_object.init_image.url, stream=True).content).decode('utf-8')
            payload = {
                "upscaling_resize": queue_object.resize,
                "upscaler_1": queue_object.upscaler_1,
                "image": 'data:image/png;base64,' + image
            }

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

                response = s.post(url=f'{settings.global_var.url}/sdapi/v1/extra-single-image', json=payload)
            response_data = response.json()
            end_time = time.time()

            #create safe/sanitized filename
            #keep_chars = (' ', '.', '_')
            epoch_time = int(time.time())
            #file_name = "".join(c for c in queue_object.init_image if c.isalnum() or c in keep_chars).rstrip()
            file_path = f'{settings.global_var.dir}\{epoch_time}-x{queue_object.resize}-Upscale.png'

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
                embed.add_field(name=f'Upscale by', value=f'``{queue_object.resize}``', inline=False)
                embed.add_field(name='took me', value='``{0:.3f}`` seconds'.format(end_time-start_time), inline=False)

                footer_args = dict(text=f'{queue_object.ctx.author.name}#{queue_object.ctx.author.discriminator}')
                if queue_object.ctx.author.avatar is not None:
                    footer_args['icon_url'] = queue_object.ctx.author.avatar.url
                embed.set_footer(**footer_args)

                event_loop.create_task(queue_object.ctx.channel.send(content=f'<@{queue_object.ctx.author.id}>', embed=embed,
                                                  file=discord.File(fp=buffer, filename=f'Upscale.png')))

        except Exception as e:
            embed = discord.Embed(title='txt2img failed', description=f'{e}\n{traceback.print_exc()}',
                                  color=settings.global_var.embed_color)
            event_loop.create_task(queue_object.ctx.channel.send(embed=embed))
        if queuehandler.GlobalQueue.queue:
            event_loop.create_task(queuehandler.process_dream(self, queuehandler.GlobalQueue.queue.pop(0)))

def setup(bot):
    bot.add_cog(UpscaleCog(bot))
