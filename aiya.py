import asyncio
import discord
import os
import sys
from core import ctxmenuhandler
from core import settings
from core.logging import get_logger
from dotenv import load_dotenv

from core import queuehandler


# start up initialization stuff
self = discord.Bot()
intents = discord.Intents.default()
intents.members = True
load_dotenv()
self.logger = get_logger(__name__)

# load extensions
# check files and global variables
settings.startup_check()
settings.files_check()

self.load_extension('core.settingscog')
self.load_extension('core.stablecog')
self.load_extension('core.upscalecog')
self.load_extension('core.identifycog')
self.load_extension('core.infocog')

use_generate = os.getenv("USE_GENERATE", 'True')
enable_generate = use_generate.lower() in ('true', '1', 't')
if enable_generate:
    print(f"/generate command is ENABLED due to USE_GENERATE={use_generate}")
    self.load_extension('core.generatecog')
else:
    print(f"/generate command is DISABLED due to USE_GENERATE={use_generate}")


# stats slash command
@self.slash_command(name='stats', description='How many images have I generated?')
async def stats(ctx):
    with open('resources/stats.txt', 'r') as f:
        data = list(map(int, f.readlines()))
    embed = discord.Embed(title='Art generated', description=f'I have created {data[0]} pictures!',
                          color=settings.global_var.embed_color)
    await ctx.respond(embed=embed)


# queue slash command
@self.slash_command(name='queue', description='Check the size of each queue')
async def queue(ctx):
    queue_sizes = queuehandler.get_queue_sizes()
    description = queue_sizes
    embed = discord.Embed(title='Queue Sizes', description=description, 
                          color=settings.global_var.embed_color)
    await ctx.respond(embed=embed)


# context menu commands
@self.message_command(name="Get Image Info")
async def get_image_info(ctx, message: discord.Message):
    await ctxmenuhandler.get_image_info(ctx, message)


@self.message_command(name=f"Quick Upscale")
async def quick_upscale(ctx, message: discord.Message):
    await ctxmenuhandler.quick_upscale(self, ctx, message)


@self.message_command(name=f"Download Batch")
async def batch_download(ctx, message: discord.Message):
    await ctxmenuhandler.batch_download(ctx, message)


@self.event
async def on_ready():
    self.logger.info(f'Logged in as {self.user.name} ({self.user.id})')
    await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='drawing tutorials.'))
    for guild in self.guilds:
        print(f"I'm active in {guild.id} a.k.a {guild}!")


# fallback feature to delete generations if aiya has been restarted
@self.event
async def on_raw_reaction_add(ctx):
    if ctx.emoji.name == '❌':
        try:
            end_user = f'{ctx.user_id}'
            message = await self.get_channel(ctx.channel_id).fetch_message(ctx.message_id)
            if end_user in message.content and "Queue" not in message.content:
                await message.delete()
            # this is for deleting outputs from /identify
            if message.embeds:
                if message.embeds[0].footer.text == f'{ctx.member.name}#{ctx.member.discriminator}':
                    await message.delete()
        except(Exception,):
            # so console log isn't spammed with errors
            pass


@self.event
async def on_guild_join(guild):
    print(f'Wow, I joined {guild.name}!')


async def shutdown(bot):
    await bot.close()


try:
    self.run(os.getenv('TOKEN'))
except KeyboardInterrupt:
    self.logger.info('Keyboard interrupt received. Exiting.')
    asyncio.run(shutdown(self))
except SystemExit:
    self.logger.info('System exit received. Exiting.')
    asyncio.run(shutdown(self))
except Exception as e:
    self.logger.error(e)
    asyncio.run(shutdown(self))
finally:
    sys.exit(0)
