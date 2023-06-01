import os
import discord
import traceback
from asyncio import AbstractEventLoop
from discord import option
from discord.ext import commands
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from transformers import pipeline
from typing import Optional

from core import queuehandler
from core import settings


class GenerateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.model_path = "core/MagicPrompt-SD/"
        tokenizer = GPT2Tokenizer.from_pretrained(self.model_path)
        model = GPT2LMHeadModel.from_pretrained(self.model_path, pad_token_id=tokenizer.eos_token_id)
        self.pipe = pipeline('text-generation', model=model, tokenizer=tokenizer, max_length=100)

    @commands.slash_command(name='generate', description='Generates a prompt from text', guild_only=True)
    @option(
        'Text',
        str,
        description='Your text to produce the prompt.',
        required=True,
    )
    async def generate_handler(self, ctx: discord.ApplicationContext, *,
                            prompt: Optional[str]):

        # set up the queue
        if queuehandler.GlobalQueue.generate_thread.is_alive():
            queuehandler.GlobalQueue.generate_queue.append(queuehandler.GenerateObject(self, ctx, prompt))
        else:
            await queuehandler.process_generate(self, queuehandler.GenerateObject(self, ctx, prompt))

        await ctx.send_response(f"<@{ctx.author.id}>, {settings.messages()}\nQueue: ``{len(queuehandler.GlobalQueue.generate_queue)}`` - Your text: ``{prompt}``")

    def post(self, event_loop: AbstractEventLoop, post_queue_object: queuehandler.PostObject):
        event_loop.create_task(
            post_queue_object.ctx.channel.send(
                content=post_queue_object.content,
                embed=post_queue_object.embed,
                view=None
            )
        )
        if queuehandler.GlobalQueue.post_queue:
            self.post(event_loop, queuehandler.GlobalQueue.post_queue.pop(0))

    def dream(self, event_loop: AbstractEventLoop, queue_object: queuehandler.GenerateObject):
        try:
            # generate the text
            res = self.pipe(queue_object.prompt)
            generated_text = res[0]['generated_text']

            # Create an Embed object
            embed = discord.Embed(title="What about this as Prompt ?!", description=generated_text, color=0x00ff00)

            # post to discord
            queuehandler.process_post(
                self, queuehandler.PostObject(
                    self, queue_object.ctx, content=f'<@{queue_object.ctx.author.id}>', file='', embed=embed, view=None))

        except Exception as e:
            embed = discord.Embed(title='Generation failed', description=f'{e}\n{traceback.print_exc()}', color=0x00ff00)
            event_loop.create_task(queue_object.ctx.channel.send(embed=embed))

        # check each queue for any remaining tasks
        if queuehandler.GlobalQueue.generate_queue:
            event_loop.create_task(queuehandler.process_generate(self, queuehandler.GlobalQueue.generate_queue.pop(0)))


def setup(bot):
    bot.add_cog(GenerateCog(bot))
