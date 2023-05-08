import discord
from asyncio import AbstractEventLoop
from discord import option
from discord.ext import commands
from threading import Thread
from typing import Optional

from core import viewhandler
from core import settings


class BatchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(viewhandler.DeleteView(self))

    @commands.slash_command(name='batch', description='Download images from a batch', guild_only=True)
    @option(
        'batch_id',
        str,
        description='The batch-id to download images from',
        required=True,
    )
    @option(
        'image_id',
        str,
        description='The id of images to be retrieved. Specified as a comma delimited list like 1,2,3 or 1,2-5,6 etc.',
        required=True,
    )
    async def batch_handler(self, ctx: commands.Context, batch_id: str = None, image_id: str = None):
        if not batch_id:
            await ctx.send("Please provide `batch_id`.")
            return

        if not image_id:
            await ctx.send("Please provide `image_id`.")
            return

        # Parse image IDs as a list of integers
        image_ids = []
        for part in image_id.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                image_ids.extend(range(start, end+1))
            else:
                image_ids.append(int(part))

        # Find files corresponding to each image ID
        files = []
        for id_num in image_ids:
            image_path = f'{settings.global_var.dir}/{batch_id}-{id_num}.png'  # adjust file extension as needed
            try:
                file = discord.File(image_path, f'{batch_id}-{id_num}.png')
                files.append(file)
            except FileNotFoundError:
                pass  # Skip over missing files

        # Set up tuple of parameters to pass into the Discord view
        input_tuple = (ctx, batch_id, image_id)
        view = viewhandler.DeleteView(input_tuple)

        # Send the files as attachments
        if files:
            blocks = [files[i:i+10] for i in range(0, len(files), 10)]
            for block in blocks:
                await ctx.respond(f'<@{ctx.author.id}>, Here are the batch files you requested', files=block, view=view)
        else:
            await ctx.respond(f'<@{ctx.author.id}>, The requested image ids were not found.')



def setup(bot):
    bot.add_cog(BatchCog(bot))
