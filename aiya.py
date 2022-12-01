import asyncio
import discord
import os
import sys
from core import settings
from core.logging import get_logger
from dotenv import load_dotenv

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
self.load_extension('core.tipscog')


# stats slash command
@self.slash_command(name='stats', description='How many images have I generated?')
async def stats(ctx):
    with open('resources/stats.txt', 'r') as f:
        data = list(map(int, f.readlines()))
    embed = discord.Embed(title='Art generated', description=f'I have created {data[0]} pictures!',
                          color=settings.global_var.embed_color)
    await ctx.respond(embed=embed)


@self.event
async def on_ready():
    self.logger.info(f'Logged in as {self.user.name} ({self.user.id})')
    await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='drawing tutorials.'))
    # because guilds are only known when on_ready, run files check for guilds
    settings.guilds_check(self)


# fallback feature to delete generations if aiya has been restarted
@self.event
async def on_raw_reaction_add(ctx):
    if ctx.emoji.name == '❌':
        try:
            end_user = f'{ctx.member.name}#{ctx.member.discriminator}'
            message = await self.get_channel(ctx.channel_id).fetch_message(ctx.message_id)
            if end_user in message.content:
                await message.delete()
            # this is for deleting outputs from /identify
            if message.embeds:
                if message.embeds[0].footer.text == f'{ctx.member.name}#{ctx.member.discriminator}':
                    await message.delete()
        # this is for deleting generations in DMs. It can indiscriminately delete anything
        except(Exception,):
            channel = await self.fetch_user(ctx.user_id)
            message = await channel.fetch_message(ctx.message_id)
            if ctx.guild_id is None:
                await message.delete()


@self.event
async def on_guild_join(guild):
    print(f'Wow, I joined {guild.name}! Refreshing settings.')
    settings.guilds_check(self)


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
