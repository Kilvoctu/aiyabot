import asyncio
import os
from abc import ABC

import discord
from discord.ext import commands
from src.core.logging import get_logger


class Shanghai(commands.Bot, ABC):
    def __init__(self, args):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix=args.prefix, intents=intents)
        self.args = args
        self.logger = get_logger(__name__)
        self.load_extension('src.bot.stablecog')

    async def on_ready(self):
        self.logger.info(f'Logged in as {self.user.name} ({self.user.id})')
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.watching, name='you over the seven seas.'))

    async def on_message(self, message):
        if message.author == self.user:
            try:
                # Check if the message from Shanghai was actually a generation
                if message.embeds[0].fields[0].name == 'command':
                    await message.add_reaction('❌')
            except:
                pass

    async def on_raw_reaction_add(self, ctx):
        if ctx.emoji.name == '❌':
            message = await self.get_channel(ctx.channel_id).fetch_message(ctx.message_id)
            if message.embeds:
                # look at the message footer to see if the generation was by the user who reacted
                if message.embeds[0].footer.text == f'{ctx.member.name}#{ctx.member.discriminator}':
                    await message.delete()
