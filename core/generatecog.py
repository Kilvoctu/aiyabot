import os
import discord
import traceback
from asyncio import AbstractEventLoop, get_event_loop
from discord import option
from discord.ui import Button, View
from discord.ext import commands
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers import pipeline
from typing import Optional

from core import queuehandler
from core import settings


class PromptButton(Button):
    def __init__(self, label, prompt_index, parent_view):
        super().__init__(label=label, custom_id=f"prompt_{prompt_index}")
        self.parent_view = parent_view

    async def callback(self, interaction):
        prompt_index = int(self.custom_id.split("_")[1])
        prompt = self.parent_view.prompts[prompt_index]
        await interaction.response.defer()
        await self.parent_view.stable_cog.dream_handler(self.parent_view.ctx, prompt=prompt, called_from_button=True)


class GenerateView(View):
    def __init__(self, prompts, stable_cog, ctx):
        super().__init__()
        self.stable_cog = stable_cog
        self.ctx = ctx
        self.prompts = prompts
        for i, prompt in enumerate(prompts):
            button = PromptButton(label=f"Draw n°{i+1}", prompt_index=i, parent_view=self)
            self.add_item(button)

    async def interaction_check(self, interaction):
        return True


class GenerateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.model_path = "core/DistilGPT2-Stable-Diffusion-V2/"
        tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        model = AutoModelForCausalLM.from_pretrained(self.model_path)
        self.pipe = pipeline('text-generation', model=model, tokenizer=tokenizer, max_length=100)

    @commands.slash_command(name='generate', description='Generates a prompt from text', guild_only=True)
    @option(
        'Text',
        str,
        description='Your text to produce the prompt.',
        required=True,
    )
    async def generate_handler(self, ctx: discord.ApplicationContext, *,
                            prompt: Optional[str],
                            num_prompts: Optional[int]=1,
                            max_length: Optional[int]=100):

        # console log
        print(f"/Generate request for {num_prompts} prompt(s) of {max_length} tokens. Text: {prompt}")
        
        # set up the queue
        if queuehandler.GlobalQueue.generate_thread.is_alive():
            queuehandler.GlobalQueue.generate_queue.append(queuehandler.GenerateObject(self, ctx, prompt, num_prompts, max_length))
        else:
            await queuehandler.process_generate(self, queuehandler.GenerateObject(self, ctx, prompt, num_prompts, max_length))

        await ctx.send_response(f"<@{ctx.author.id}>, {settings.messages()}\nQueue: ``{len(queuehandler.GlobalQueue.generate_queue)}`` - Your text: ``{prompt}``\nNumber of prompts: ``{num_prompts}`` - Max length: ``{max_length}``")

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

    def dream(self, event_loop: AbstractEventLoop, queue_object: queuehandler.GenerateObject, num_prompts: int, max_length: int):
        try:
            # generate the text
            prompts = []
            for _ in range(num_prompts):
                res = self.pipe(queue_object.prompt, max_length=max_length)
                generated_text = res[0]['generated_text']
                prompts.append(generated_text)

            # Schedule the task to create the view and send the message
            event_loop.create_task(self.send_with_view(prompts, queue_object.ctx))

        except Exception as e:
            embed = discord.Embed(title='Generation failed', description=f'{e}\n{traceback.print_exc()}', color=0x00ff00)
            event_loop.create_task(queue_object.ctx.channel.send(embed=embed))

        # check each queue for any remaining tasks
        if queuehandler.GlobalQueue.generate_queue:
            event_loop.create_task(queuehandler.process_generate(self, queuehandler.GlobalQueue.generate_queue.pop(0)))
    
    async def send_with_view(self, prompts, ctx):
        stable_cog = self.bot.get_cog('Stable Diffusion')
        view = GenerateView(prompts, stable_cog, ctx)

        # Create an Embed object
        title = "What about this as Prompt?!" if len(prompts) == 1 else "What about these as Prompts?!"
        numbered_prompts = [f"**Prompt {i+1}:**\n{prompt}" for i, prompt in enumerate(prompts)]
        embed = discord.Embed(title=title, description="\n\n".join(numbered_prompts), color=0x00ff00)

        # post to discord
        await ctx.send(content=f'<@{ctx.author.id}>', embed=embed, view=view)


def setup(bot):
    bot.add_cog(GenerateCog(bot))