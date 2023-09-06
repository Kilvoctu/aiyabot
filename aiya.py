import asyncio
import discord
import os
import sys
from core import ctxmenuhandler, settings
from core.logging import get_logger
from dotenv import load_dotenv
from discord.ext import commands

from core.queuehandler import GlobalQueue
from core.generatecog import GenerateView
from core.metacog import MetaView

# Initialize logging
logger = get_logger(__name__)

# Initialize the bot
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
self = commands.Bot(command_prefix=commands.when_mentioned_or("!"), intents=intents)

# Initialize some startup stuff
load_dotenv()
logger = get_logger(__name__)

# Load extensions
settings.startup_check()
settings.files_check()

self.load_extension('core.settingscog')
self.load_extension('core.stablecog')
self.load_extension('core.upscalecog')
self.load_extension('core.identifycog')
self.load_extension('core.infocog')
self.load_extension('core.generatecog')
self.load_extension('core.metacog')


@self.event
async def on_ready():
    logger.info(f'Logged in as {self.user.name} ({self.user.id})')
    await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='drawing tutorials.'))
    
    # Add persistent views
    self.add_view(GenerateView([], None, None, None, None, "", 1, 75, 0.9, 8, 1.2))
    self.add_view(MetaView(''))

    for guild in self.guilds:
        print(f"I'm active in {guild.id} a.k.a {guild}!")

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
    queue_sizes = GlobalQueue.get_queue_sizes()
    description = '\n'.join([f'{name}: {size}' for name, size in queue_sizes.items()])
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
    logger.info('Keyboard interrupt received. Exiting.')
    asyncio.run(self.close())
except SystemExit:
    logger.info('System exit received. Exiting.')
    asyncio.run(self.close())
except Exception as e:
    logger.error(e)
    asyncio.run(self.close())
finally:
    sys.exit(0)
