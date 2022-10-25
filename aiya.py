import asyncio
import os
import sys
from os.path import exists
import discord
import requests
from dotenv import load_dotenv
from core.logging import get_logger


#start up initialization stuff
global URL
self = discord.Bot()
intents = discord.Intents.default()
intents.members = True
load_dotenv()
embed_color = discord.Colour.from_rgb(222, 89, 28)
responsestr = {}
self.logger = get_logger(__name__)

file_exists = exists('resources/stats.txt')
if file_exists is False:
    self.logger.info(f'stats.txt missing. Creating new file.')
    with open('resources/stats.txt', 'w') as f: f.write('0')

if os.environ.get('URL') == '':
    URL = 'http://127.0.0.1:7860'
    print('Using Default URL: http://127.0.0.1:7860')
else:
    URL = os.environ.get('URL')

with requests.Session() as s:
    if os.environ.get('USER'):
        if os.environ.get('PASS') == '':
            raise SystemExit('There is no password set. Please set a password in the .env file.')
        else:
            LogInPayload = {
                'username': os.getenv('USER'),
                'password': os.getenv('PASS')
            }
        print('Logging into the API')
        p = s.post(URL + '/login', data=LogInPayload)
    else:
        print('No Username Set')
        p = s.post(URL + '/login')
    r = s.get(URL + '/config')

self.load_extension('core.stablecog')
self.load_extension('core.tipscog')

#stats slash command
@self.slash_command(name = 'stats', description = 'How many images has the bot generated?')
async def stats(ctx):
    with open('resources/stats.txt', 'r') as f: data = list(map(int, f.readlines()))
    embed = discord.Embed(title='Art generated', description=f'I have created {data[0]} pictures!', color=embed_color)
    await ctx.respond(embed=embed)

@self.event
async def on_ready():
    self.logger.info(f'Logged in as {self.user.name} ({self.user.id})')
    await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='drawing tutorials.'))

#feature to delete generations. give bot 'Add Reactions' permission (or not, to hide the ❌)
@self.event
async def on_message(message):
    if message.author == self.user:
        try:
            if message.embeds[0].fields[0].name == 'command':
                await message.add_reaction('❌')
        except:
            pass

@self.event
async def on_raw_reaction_add(ctx):
    if ctx.emoji.name == '❌':
        message = await self.get_channel(ctx.channel_id).fetch_message(ctx.message_id)
        if message.embeds:
            if message.embeds[0].footer.text == f'{ctx.member.name}#{ctx.member.discriminator}':
                await message.delete()

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