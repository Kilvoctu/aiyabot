import base64
import discord
import traceback
import requests
from asyncio import AbstractEventLoop
from discord import option
from discord.ext import commands
from typing import Optional

from core import queuehandler
from core import viewhandler
from core import settings
from core import stablecog
from core import upscalecog


class IdentifyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name='identify', description='Describe an image')
    @option(
        'init_image',
        discord.Attachment,
        description='The image to identify',
        required=False,
    )
    @option(
        'init_url',
        str,
        description='The URL image to identify. This overrides init_image!',
        required=False,
    )
    async def dream_handler(self, ctx: discord.ApplicationContext, *,
                            init_image: Optional[discord.Attachment] = None,
                            init_url: Optional[str]):

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
                await ctx.send_response('I need an image to identify!', ephemeral=True)
                has_image = False

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
                    queuehandler.GlobalQueue.identify_q.append(queuehandler.IdentifyObject(ctx, init_image, view))
                    await ctx.send_response(
                        f"<@{ctx.author.id}>, I'm identifying the image!\nQueue: ``{len(queuehandler.union(*queues))}``",
                        delete_after=45.0)
            else:
                await queuehandler.process_dream(self, queuehandler.IdentifyObject(ctx, init_image, view))
                await ctx.send_response(
                    f"<@{ctx.author.id}>, I'm identifying the image!\nQueue: ``{len(queuehandler.union(*queues))}``",
                    delete_after=45.0)

    def dream(self, event_loop: AbstractEventLoop, queue_object: queuehandler.IdentifyObject):
        try:
            # construct a payload
            image = base64.b64encode(requests.get(queue_object.init_image.url, stream=True).content).decode('utf-8')
            payload = {
                "image": 'data:image/png;base64,' + image
            }

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

                response = s.post(url=f'{settings.global_var.url}/sdapi/v1/interrogate', json=payload)
            response_data = response.json()

            # post to discord
            embed = discord.Embed()
            embed.set_image(url=queue_object.init_image.url)
            embed.colour = settings.global_var.embed_color
            embed.add_field(name=f'I think this is', value=f'``{response_data.get("caption")}``', inline=False)

            footer_args = dict(text=f'{queue_object.ctx.author.name}#{queue_object.ctx.author.discriminator}')
            if queue_object.ctx.author.avatar is not None:
                footer_args['icon_url'] = queue_object.ctx.author.avatar.url
            embed.set_footer(**footer_args)

            event_loop.create_task(
                queue_object.ctx.channel.send(content=f'<@{queue_object.ctx.author.id}>', embed=embed,
                                              view=queue_object.view))

        except Exception as e:
            embed = discord.Embed(title='identify failed', description=f'{e}\n{traceback.print_exc()}',
                                  color=settings.global_var.embed_color)
            event_loop.create_task(queue_object.ctx.channel.send(embed=embed))
        # check each queue for any remaining tasks
        if queuehandler.GlobalQueue.draw_q:
            draw_dream = stablecog.StableCog(self)
            event_loop.create_task(queuehandler.process_dream(draw_dream, queuehandler.GlobalQueue.draw_q.pop(0)))
        if queuehandler.GlobalQueue.upscale_q:
            upscale_dream = upscalecog.UpscaleCog(self)
            event_loop.create_task(queuehandler.process_dream(upscale_dream, queuehandler.GlobalQueue.upscale_q.pop(0)))
        if queuehandler.GlobalQueue.identify_q:
            event_loop.create_task(queuehandler.process_dream(self, queuehandler.GlobalQueue.identify_q.pop(0)))


def setup(bot):
    bot.add_cog(IdentifyCog(bot))
