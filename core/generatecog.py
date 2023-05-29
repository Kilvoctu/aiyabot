import os
import discord
from discord import option
from core import viewhandler
from core import settings
from discord.ext import commands
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from transformers import pipeline

class GenerateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.model_path = "core/MagicPrompt-SD/model/"
        tokenizer = GPT2Tokenizer.from_pretrained(self.model_path)
        model = GPT2LMHeadModel.from_pretrained(self.model_path, pad_token_id=tokenizer.eos_token_id)
        self.pipe = pipeline('text-generation', model=model, tokenizer=tokenizer, max_length=100)

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(viewhandler.DeleteView(self))

    @commands.slash_command(name='generate', description='Generates a prompt from text', guild_only=True)
    @option(
        'Text',
        discord.Attachment,
        description='Your text to produce the prompt.',
        required=True,
    )
    async def generate(self, ctx, *, prompt: str):
        # send the formatted message immediately
        await ctx.send_response(f'<@{ctx.author.id}>, {settings.messages()}\nYour text: ``{prompt}``')

        # generate the text
        res = self.pipe(prompt)
        generated_text = res[0]['generated_text']

        # Create an Embed object
        embed = discord.Embed(title="What about this as Prompt ?!", description=generated_text, color=0x00ff00)

        # send the message with the Embed
        await ctx.send(embed=embed)

def setup(bot):
    bot.add_cog(GenerateCog(bot))
