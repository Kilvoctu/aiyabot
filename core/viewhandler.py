import csv
import discord
import random
from discord.ui import InputText, Modal, View

from core import queuehandler
from core import settings
from core import stablecog

'''
The input_tuple index reference
input_tuple[0] = ctx
[1] = prompt
[2] = negative_prompt
[3] = data_model
[4] = steps
[5] = width
[6] = height
[7] = guidance_scale
[8] = sampler
[9] = seed
[10] = strength
[11] = init_image
[12] = count
[13] = style
[14] = facefix
[15] = highres_fix
[16] = clip_skip
[17] = simple_prompt
[18] = simple_model
'''

# set up tuple of queues to pass into union()
queues = (queuehandler.GlobalQueue.draw_q, queuehandler.GlobalQueue.upscale_q, queuehandler.GlobalQueue.identify_q)


# the modal that is used for the 🖋 button
class DrawModal(Modal):
    def __init__(self, input_tuple) -> None:
        super().__init__(title="Change Prompt!")
        self.input_tuple = input_tuple
        self.add_item(
            InputText(
                label='Input your new prompt',
                value=input_tuple[17],
                style=discord.InputTextStyle.long
            )
        )
        self.add_item(
            InputText(
                label='Input your new negative prompt (optional)',
                style=discord.InputTextStyle.long,
                value=input_tuple[2],
                required=False
            )
        )
        self.add_item(
            InputText(
                label='Keep seed? Delete or set to -1 to randomize',
                style=discord.InputTextStyle.short,
                value=input_tuple[9],
                required=False
            )
        )

    async def callback(self, interaction: discord.Interaction):
        # update the tuple with new prompts
        new_prompt = list(self.input_tuple)
        new_prompt[1] = new_prompt[1].replace(new_prompt[17], self.children[0].value)
        new_prompt[17] = self.children[0].value
        new_prompt[2] = self.children[1].value

        # update the tuple new seed (random if set to -1)
        new_prompt[9] = self.children[2].value
        if (self.children[2].value == "-1") or (self.children[2].value == ""):
            new_prompt[9] = random.randint(0, 0xFFFFFFFF)

        prompt_tuple = tuple(new_prompt)

        draw_dream = stablecog.StableCog(self)
        prompt_output = f'\nNew prompt: ``{new_prompt[17]}``'
        if new_prompt[2] != '':
            prompt_output = prompt_output + f'\nNew negative prompt: ``{new_prompt[2]}``'
        if str(new_prompt[9]) != str(self.input_tuple[9]):
            prompt_output = prompt_output + f'\nNew seed: ``{new_prompt[9]}``'

        # check queue again, but now we know user is not in queue
        if queuehandler.GlobalQueue.dream_thread.is_alive():
            if self.input_tuple[3] != '':
                settings.global_var.send_model = True
            queuehandler.GlobalQueue.draw_q.append(queuehandler.DrawObject(*prompt_tuple, DrawView(prompt_tuple)))
            await interaction.response.send_message(
                f'<@{interaction.user.id}>, redrawing the image!\nQueue: ``{len(queuehandler.union(*queues))}``{prompt_output}')
        else:
            if self.input_tuple[3] != '':
                settings.global_var.send_model = True
            await queuehandler.process_dream(draw_dream, queuehandler.DrawObject(*prompt_tuple, DrawView(prompt_tuple)))
            await interaction.response.send_message(
                f'<@{interaction.user.id}>, redrawing the image!\nQueue: ``{len(queuehandler.union(*queues))}``{prompt_output}')


# creating the view that holds the buttons for /draw output
class DrawView(View):
    def __init__(self, input_tuple):
        super().__init__(timeout=None)
        self.input_tuple = input_tuple

    # the 🖋 button will allow a new prompt and keep same parameters for everything else
    @discord.ui.button(
        custom_id="button_re-prompt",
        emoji="🖋")
    async def button_draw(self, button, interaction):
        try:
            # check if the /draw output is from the person who requested it
            if self.message.embeds[0].footer.text == f'{interaction.user.name}#{interaction.user.discriminator}':
                # if there's room in the queue, open up the modal
                if queuehandler.GlobalQueue.dream_thread.is_alive():
                    user_already_in_queue = False
                    for queue_object in queuehandler.union(*queues):
                        if queue_object.ctx.author.id == interaction.user.id:
                            user_already_in_queue = True
                            break
                    if user_already_in_queue:
                        await interaction.response.send_message(content=f"Please wait! You're queued up.",
                                                                ephemeral=True)
                    else:
                        await interaction.response.send_modal(DrawModal(self.input_tuple))
                else:
                    await interaction.response.send_modal(DrawModal(self.input_tuple))
            else:
                await interaction.response.send_message("You can't use other people's 🖋!", ephemeral=True)
        except(Exception,):
            # if interaction fails, assume it's because aiya restarted (breaks buttons)
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("I may have been restarted. This button no longer works.", ephemeral=True)

    # the 🎲 button will take the same parameters for the image, change the seed, and add a task to the queue
    @discord.ui.button(
        custom_id="button_re-roll",
        emoji="🎲")
    async def button_roll(self, button, interaction):
        try:
            # check if the /draw output is from the person who requested it
            if self.message.embeds[0].footer.text == f'{interaction.user.name}#{interaction.user.discriminator}':
                # update the tuple with a new seed
                new_seed = list(self.input_tuple)
                new_seed[9] = random.randint(0, 0xFFFFFFFF)
                seed_tuple = tuple(new_seed)

                # set up the draw dream and do queue code again for lack of a more elegant solution
                draw_dream = stablecog.StableCog(self)
                if queuehandler.GlobalQueue.dream_thread.is_alive():
                    user_already_in_queue = False
                    for queue_object in queuehandler.union(*queues):
                        if queue_object.ctx.author.id == interaction.user.id:
                            user_already_in_queue = True
                            break
                    if user_already_in_queue:
                        await interaction.response.send_message(content=f"Please wait! You're queued up.",
                                                                ephemeral=True)
                    else:
                        button.disabled = True
                        await interaction.response.edit_message(view=self)

                        if self.input_tuple[3] != '':
                            settings.global_var.send_model = True

                        queuehandler.GlobalQueue.draw_q.append(
                            queuehandler.DrawObject(*seed_tuple, DrawView(seed_tuple)))
                        await interaction.followup.send(
                            f'<@{interaction.user.id}>, redrawing the image!\nQueue: ``{len(queuehandler.union(*queues))}`` - ``{seed_tuple[17]}``\nNew seed:``{seed_tuple[9]}``')
                else:
                    button.disabled = True
                    await interaction.response.edit_message(view=self)

                    if self.input_tuple[3] != '':
                        settings.global_var.send_model = True

                    await queuehandler.process_dream(draw_dream,
                                                     queuehandler.DrawObject(*seed_tuple, DrawView(seed_tuple)))
                    await interaction.followup.send(
                        f'<@{interaction.user.id}>, redrawing the image!\nQueue: ``{len(queuehandler.union(*queues))}`` - ``{seed_tuple[17]}``\nNew Seed:``{seed_tuple[9]}``')
            else:
                await interaction.response.send_message("You can't use other people's 🎲!", ephemeral=True)
        except(Exception,):
            # if interaction fails, assume it's because aiya restarted (breaks buttons)
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("I may have been restarted. This button no longer works.", ephemeral=True)

    # the 📋 button will let you review the parameters of the generation
    @discord.ui.button(
        custom_id="button_review",
        emoji="📋")
    async def button_review(self, button, interaction):
        # simpler variable name
        rev = self.input_tuple
        print(rev[3])
        print(rev[18])
        try:
            # the tuple will show the model_full_name. Get the associated display_name and activator_token from it.
            with open('resources/models.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='|')
                for row in reader:
                    if (row['model_full_name'] == rev[3]) or (row['model_full_name'] == rev[18]):
                        model_name = row['display_name']
                        activator_token = row['activator_token']

            # generate the command for copy-pasting, and also add embed fields
            embed = discord.Embed(title="About the image!", description="")
            embed.colour = settings.global_var.embed_color
            embed.add_field(name=f'Prompt', value=f'``{rev[17]}``', inline=False)
            copy_command = f'/draw prompt:{rev[17]} data_model:{model_name} steps:{rev[4]} width:{rev[5]} height:{rev[6]} guidance_scale:{rev[7]} sampler:{rev[8]} seed:{rev[9]}'
            if rev[2] != '':
                copy_command = copy_command + f' negative_prompt:{rev[2]}'
                embed.add_field(name=f'Negative prompt', value=f'``{rev[2]}``', inline=False)
            if activator_token:
                embed.add_field(name=f'Data model',
                                value=f'Display name - ``{model_name}``\nFull name - ``{rev[3]}``\nActivator token - ``{activator_token}``',
                                inline=False)
            else:
                embed.add_field(name=f'Data model', value=f'Display name - ``{model_name}``\nFull name - ``{rev[3]}``',
                                inline=False)
            extra_params = f'Sampling steps: ``{rev[4]}``\nSize: ``{rev[5]}x{rev[6]}``\nClassifier-free guidance scale: ``{rev[7]}``\nSampling method: ``{rev[8]}``\nSeed: ``{rev[9]}``'
            if rev[11]:
                # not interested in adding embed fields for strength and init_image
                copy_command = copy_command + f' strength:{rev[10]} init_url:{rev[11]}'
            if rev[12] != 1:
                copy_command = copy_command + f' count:{rev[13]}'
            if rev[13] != 'None':
                copy_command = copy_command + f' style:{rev[13]}'
                extra_params = extra_params + f'\nStyle preset: ``{rev[13]}``'
            if rev[14] != 'None':
                copy_command = copy_command + f' facefix:{rev[14]}'
                extra_params = extra_params + f'\nFace restoration model: ``{rev[14]}``'
            if rev[15]:
                copy_command = copy_command + f' enable_hr:{rev[15]}'
                extra_params = extra_params + f'\nHigh-res fix: ``{rev[15]}``'
            if rev[16] != 1:
                copy_command = copy_command + f' clip_skip:{rev[16]}'
                extra_params = extra_params + f'\nCLIP skip: ``{rev[16]}``'
            embed.add_field(name=f'Other parameters', value=extra_params, inline=False)
            embed.add_field(name=f'Command for copying', value=f'``{copy_command}``', inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print('The clipboard button broke:' + str(e))
            # if interaction fails, assume it's because aiya restarted (breaks buttons)
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("I may have been restarted. This button no longer works.", ephemeral=True)

    # the button to delete generated images
    @discord.ui.button(
        custom_id="button_x",
        emoji="❌")
    async def delete(self, button, interaction):
        try:
            if self.message.embeds[0].footer.text == f'{interaction.user.name}#{interaction.user.discriminator}':
                await interaction.message.delete()
            else:
                await interaction.response.send_message("You can't delete other people's images!", ephemeral=True)
        except(Exception,):
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("I may have been restarted. This button no longer works.\n"
                                            "You can react with ❌ to delete the image.", ephemeral=True)


# creating the view that holds a button to delete output
class DeleteView(View):
    def __init__(self, user):
        super().__init__(timeout=None)
        self.user = user

    @discord.ui.button(
        custom_id="button_x",
        emoji="❌")
    async def delete(self, button, interaction):
        if interaction.user.id == self.user:
            button.disabled = True
            await interaction.message.delete()
        else:
            await interaction.response.send_message("You can't delete other people's images!", ephemeral=True)
