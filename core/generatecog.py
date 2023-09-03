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
        super().__init__(label=label, custom_id=f"prompt_{prompt_index}", emoji="🎨")
        self.parent_view = parent_view

    async def callback(self, interaction):
        try:
            await interaction.response.defer()  # Différer la réponse
            prompt_index = int(self.custom_id.split("_")[1])
            prompt = self.parent_view.prompts[prompt_index]
            await self.parent_view.stable_cog.dream_handler(self.parent_view.ctx, prompt=prompt, called_from_button=True)
            await interaction.edit_original_response(view=self.parent_view)  # Éditer le message original
        except Exception as e:
            print(f'The draw button broke: {str(e)}')
            self.disabled = True
            await interaction.edit_original_response(view=self.parent_view)
            await interaction.followup.send("I may have been restarted. This button no longer works.", ephemeral=True)


class RerollButton(Button):
    def __init__(self, parent_view):
        super().__init__(label="Reroll", custom_id="reroll", emoji="🔁")
        self.parent_view = parent_view

    async def callback(self, interaction):
        try:
            await interaction.response.defer()  # Différer la réponse
            await self.parent_view.generate_cog.generate_handler(
                self.parent_view.ctx, 
                prompt=self.parent_view.prompt,
                num_prompts=self.parent_view.num_prompts,
                max_length=self.parent_view.max_length,
                called_from_reroll=True
            )
            await interaction.edit_original_response(view=self.parent_view)  # Éditer le message original
        except Exception as e:
            print(f'Reroll button broke: {str(e)}')
            self.disabled = True
            await interaction.edit_original_response(view=self.parent_view)
            await interaction.followup.send("I may have been restarted. This button no longer works.", ephemeral=True)


class DeleteButton(Button):
    def __init__(self, parent_view):
        super().__init__(label="Delete", custom_id="delete", emoji="❌")
        self.parent_view = parent_view

    async def callback(self, interaction):
        try:
            await self.parent_view.message.delete()
        except Exception as e:
            print(f'The delete button broke: {str(e)}')
            self.disabled = True
            await interaction.response.edit_message(view=self.parent_view)
            await interaction.followup.send("I may have been restarted. This button no longer works.", ephemeral=True)


class GenerateView(View):
    def __init__(self, prompts, stable_cog, generate_cog, ctx, message, prompt, num_prompts, max_length):
        super().__init__(timeout=None)
        self.stable_cog = stable_cog
        self.generate_cog = generate_cog
        self.ctx = ctx
        self.prompts = prompts
        self.message = message
        self.prompt = prompt
        self.num_prompts = num_prompts
        self.max_length = max_length
        for i, prompt in enumerate(prompts):
            button = PromptButton(label=f"Draw n°{i+1}", prompt_index=i, parent_view=self)
            self.add_item(button)
        reroll_button = RerollButton(parent_view=self)
        self.add_item(reroll_button)
        delete_button = DeleteButton(parent_view=self)
        self.add_item(delete_button)

    async def interaction_check(self, interaction):
        return True


class GenerateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.model_path = "core/DistilGPT2-Stable-Diffusion-V2/"
        tokenizer = AutoTokenizer.from_pretrained(self.model_path)
        model = AutoModelForCausalLM.from_pretrained(self.model_path)
        self.pipe = pipeline('text-generation', model=model, tokenizer=tokenizer, max_length=75)

    @commands.slash_command(name='generate', description='Generates a prompt from text', guild_only=True)
    @option(
        'Text',
        str,
        description='Your text to produce the prompt.',
        required=True,
    )
    @option(
        'Number of prompts',
        str,
        description='The number of prompts to produce. (1-5)',
        required=False,
    )
    @option(
        'Max length',
        str,
        description='The max length for the generated prompts. (15-150)',
        required=False,
    )
    async def generate_handler(self, ctx: discord.ApplicationContext, *,
                            prompt: Optional[str],
                            num_prompts: Optional[int]=1,
                            max_length: Optional[int]=75,
                            called_from_reroll: Optional[bool]=False):

        print(f"/Generate request for {num_prompts} prompt(s) of {max_length} tokens. Text: {prompt}")
        
        # sanity check
        if not 1 <= num_prompts <= 5:
            await ctx.send("The number of prompts must be between 1 and 5.")
            return
            
        if not 15 <= max_length <= 150:
            await ctx.send("The maximum length must be between 15 and 150.")
            return
            
        # set up the queue
        if queuehandler.GlobalQueue.generate_thread.is_alive():
            queuehandler.GlobalQueue.generate_queue.append(queuehandler.GenerateObject(self, ctx, prompt, num_prompts, max_length))
        else:
            await queuehandler.process_generate(self, queuehandler.GenerateObject(self, ctx, prompt, num_prompts, max_length))

        if called_from_reroll:
            await ctx.send_followup(f"<@{ctx.author.id}>, {settings.messages()}\nQueue: ``{len(queuehandler.GlobalQueue.generate_queue)}`` - Your text: ``{prompt}``\nNumber of prompts: ``{num_prompts}`` - Max length: ``{max_length}``")
        else:
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

            # schedule the task to create the view and send the message
            event_loop.create_task(self.send_with_view(prompts, queue_object.ctx, queue_object.prompt, num_prompts, max_length))

        except Exception as e:
            embed = discord.Embed(title='Generation failed', description=f'{e}\n{traceback.print_exc()}', color=0x00ff00)
            event_loop.create_task(queue_object.ctx.channel.send(embed=embed))

        # check each queue for any remaining tasks
        if queuehandler.GlobalQueue.generate_queue:
            event_loop.create_task(queuehandler.process_generate(self, queuehandler.GlobalQueue.generate_queue.pop(0)))
    
    async def send_with_view(self, prompts, ctx, prompt, num_prompts, max_length):
        stable_cog = self.bot.get_cog('Stable Diffusion')
        
        # create embed
        title = "What about this as Prompt?!" if len(prompts) == 1 else "What about these as Prompts?!"
        numbered_prompts = [f"**Prompt {i+1}:**\n{prompt}" for i, prompt in enumerate(prompts)]
        embed = discord.Embed(title=title, description="\n\n".join(numbered_prompts), color=0x00ff00)

        # post to discord
        message = await ctx.send(content=f'<@{ctx.author.id}>', embed=embed)

        # create view
        view = GenerateView(prompts, stable_cog, self, ctx, message, prompt, num_prompts, max_length)
        await message.edit(view=view)


def setup(bot):
    bot.add_cog(GenerateCog(bot))