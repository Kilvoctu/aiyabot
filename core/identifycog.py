import base64
import traceback
import discord
import requests
from discord import option
from discord.ext import commands
from typing import Optional

from core import settings


class IdentifyCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.slash_command(name = 'identify', description = 'Describe an image')
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
        #url *will* override init image for compatibility, can be changed here
        if init_url:
            try:
                init_image = requests.get(init_url)
            except(Exception,):
                await ctx.send_response('URL image not found!\nI have nothing to work with...', ephemeral=True)
                has_image = False

        #fail if no image is provided
        if init_url is None:
            if init_image is None:
                await ctx.send_response('I need an image to identify!', ephemeral=True)
                has_image = False

        if has_image:
            try:
                first_embed = discord.Embed(title='Identifying')
                first_embed.colour = settings.global_var.embed_color
                await ctx.send_response(embed=first_embed)
                #construct a payload
                image = base64.b64encode(requests.get(init_image.url, stream=True).content).decode('utf-8')
                payload = {
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

                    response = s.post(url=f'{settings.global_var.url}/sdapi/v1/interrogate', json=payload)
                response_data = response.json()

                # post to discord
                new_embed = discord.Embed()
                new_embed.set_image(url=init_image.url)
                new_embed.colour = settings.global_var.embed_color
                new_embed.add_field(name=f'I think this is', value=f'``{response_data.get("caption")}``', inline=False)
                await ctx.edit(embed=new_embed)

            except Exception as e:
                embed = discord.Embed(title='identify failed', description=f'{e}\n{traceback.print_exc()}',
                                      color=settings.global_var.embed_color)
                await ctx.channel.send(embed=embed)

def setup(bot):
    bot.add_cog(IdentifyCog(bot))
