import os
from os.path import exists
import sys
import discord
import asyncio
from dotenv import load_dotenv
from core.logging import get_logger
from core import PayloadFormatter

embed_color = discord.Colour.from_rgb(222, 89, 28)
    
load_dotenv()
self = discord.Bot()
intents = discord.Intents.all()
intents.members = True
self.logger = get_logger(__name__)

file_exists = exists('resources/stats.txt')
if file_exists is False:
    self.logger.info(f'stats.txt missing. Creating new file.')
    with open('resources/stats.txt', 'w') as f: f.write('0')

self.load_extension('core.stablecog')
self.load_extension('core.tipscog')

@self.event
async def on_ready():
    PayloadFormatter.setup()
    self.logger.info(f'Logged in as {self.user.name} ({self.user.id})')
    await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='drawing tutorials.'))

@self.slash_command(name = "stats", description = "How many images has the bot generated?")
async def stats(ctx):
    with open("resources/stats.txt", 'r') as f: data = list(map(int, f.readlines()))
    embed = discord.Embed(title='Art generated', description=f'I have created {data[0]} pictures!', color=embed_color)
    await ctx.respond(embed=embed)

async def shutdown(bot):
    await bot.close()

try:
    self.run(os.getenv('TOKEN'))
except KeyboardInterrupt:
    logger.info('Keyboard interrupt received. Exiting.')
    asyncio.run(shutdown(self))
except SystemExit:
    logger.info('System exit received. Exiting.')
    asyncio.run(shutdown(self))
except Exception as e:
    logger.error(e)
    asyncio.run(shutdown(self))
finally:
    sys.exit(0)