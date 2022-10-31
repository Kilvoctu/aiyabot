import asyncio
import os
import sys
import discord
from dotenv import load_dotenv
from core.logging import get_logger
from core import settings


#start up initialization stuff
self = discord.Bot()
intents = discord.Intents.default()
intents.members = True
load_dotenv()
self.logger = get_logger(__name__)

#load extensions
self.load_extension('core.stablecog')
self.load_extension('core.settingscog')
self.load_extension('core.tipscog')

#stats slash command
@self.slash_command(name = 'stats', description = 'How many images has the bot generated?')
async def stats(ctx):
    with open('resources/stats.txt', 'r') as f:
        data = list(map(int, f.readlines()))
    embed = discord.Embed(title='Art generated', description=f'I have created {data[0]} pictures!', color=settings.global_var.embed_color)
    await ctx.respond(embed=embed)

@self.event
async def on_ready():
    self.logger.info(f'Logged in as {self.user.name} ({self.user.id})')
    await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='drawing tutorials.'))
    #check files and global variables
    settings.files_check(self)

#feature to delete generations. give bot 'Add Reactions' permission (or not, to hide the ❌)
@self.event
async def on_message(message):
    if message.author == self.user:
        try:
            if message.embeds[0].fields[1].name == 'took me':
                await message.add_reaction('❌')
        except:
            pass

@self.event
async def on_raw_reaction_add(ctx):
    if ctx.emoji.name == '❌':
        try:
            message = await self.get_channel(ctx.channel_id).fetch_message(ctx.message_id)
            if message.embeds:
                if message.embeds[0].footer.text == f'{ctx.member.name}#{ctx.member.discriminator}':
                    await message.delete()
        # this is for deleting generations in DMs
        except:
            channel = await self.fetch_user(ctx.user_id)
            message = await channel.fetch_message(ctx.message_id)
            if message.embeds:
                await message.delete()

@self.event
async def on_guild_join(guild):
    print(f'Wow, I joined {guild.name}! Refreshing settings.')
    settings.files_check(self)

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