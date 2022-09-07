import os
import discord
from discord.ext import commands
from src.core.logging import get_logger

class Shanghai(commands.Bot):
    def __init__(self, args):
        super().__init__(command_prefix=args.prefix)
        self.args = args
        self.logger = get_logger(__name__)
        self.load_extension('src.bot.stablecog')

    async def on_ready(self):
        self.logger.info(f'Logged in as {self.user.name} ({self.user.id})')
        await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='you over the seven seas.'))
    
    async def close(self):
        await self._bot.close()