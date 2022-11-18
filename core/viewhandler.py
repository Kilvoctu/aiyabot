import csv
import discord
import random

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
[15] = simple_prompt
'''

#creating the view that holds the buttons for /draw output
class DrawView(discord.ui.View):
    def __init__(self, input_tuple):
        super().__init__(timeout=None)
        self.input_tuple = input_tuple

    #the 🎲 button will take the same parameters for the image, change the seed, and add a task to the queue
    @discord.ui.button(
        custom_id="button_re-roll",
        emoji="🎲")
    async def button_roll(self, button, interaction):
        try:
            #check if the /draw output is from the person who requested it
            if self.message.embeds[0].footer.text == f'{interaction.user.name}#{interaction.user.discriminator}':
                #update the tuple with a new seed
                new_seed = list(self.input_tuple)
                new_seed[9] = random.randint(0, 0xFFFFFFFF)
                seed_tuple = tuple(new_seed)

                #set up the draw dream and do queue code again for lack of a more elegant solution
                draw_dream = stablecog.StableCog(self)
                if queuehandler.GlobalQueue.dream_thread.is_alive():
                    user_already_in_queue = False
                    for queue_object in queuehandler.union(queuehandler.GlobalQueue.draw_q,
                                                           queuehandler.GlobalQueue.upscale_q,
                                                           queuehandler.GlobalQueue.identify_q):
                        if queue_object.ctx.author.id == interaction.user.id:
                            user_already_in_queue = True
                            break
                    if user_already_in_queue:
                        await interaction.response.send_message(content=f"Please wait! You're queued up.", ephemeral=True)
                    else:
                        button.disabled = True
                        await interaction.response.edit_message(view=self)
                        queuehandler.GlobalQueue.draw_q.append(queuehandler.DrawObject(*seed_tuple, DrawView(seed_tuple)))
                        await interaction.followup.send(
                            f'<@{interaction.user.id}>, redrawing the image!\nQueue: ``{len(queuehandler.union(queuehandler.GlobalQueue.draw_q, queuehandler.GlobalQueue.upscale_q, queuehandler.GlobalQueue.identify_q))}`` - ``{seed_tuple[15]}``\nNew seed:``{seed_tuple[9]}``')
                else:
                    button.disabled = True
                    await interaction.response.edit_message(view=self)
                    await queuehandler.process_dream(draw_dream, queuehandler.DrawObject(*seed_tuple, DrawView(seed_tuple)))
                    await interaction.followup.send(
                        f'<@{interaction.user.id}>, redrawing the image!\nQueue: ``{len(queuehandler.union(queuehandler.GlobalQueue.draw_q, queuehandler.GlobalQueue.upscale_q, queuehandler.GlobalQueue.identify_q))}`` - ``{seed_tuple[15]}``\nNew Seed:``{seed_tuple[9]}``')
            else:
                await interaction.response.send_message("You can't use other people's buttons!", ephemeral=True)
        except(Exception,):
            #if interaction fails, assume it's because aiya restarted (breaks buttons)
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("I may have been restarted. This button no longer works.", ephemeral=True)

    # the 📋 button will let you review the parameters of the generation
    @discord.ui.button(
        custom_id="button_review",
        emoji="📋")
    async def button_review(self, button, interaction):
        #simpler variable name
        rev = self.input_tuple
        try:
            #the tuple will show the model_full_name. Get the associated display_name and activator_token from it.
            with open('resources/models.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='|')
                for row in reader:
                    if row['model_full_name'] == rev[3]:
                        model_name = row['display_name']
                        activator_token = row['activator_token']

            #generate the command for copy-pasting, and also add embed fields
            embed = discord.Embed(title="About the image!", description="")
            embed.colour = settings.global_var.embed_color
            embed.add_field(name=f'Prompt', value=f'``{rev[15]}``', inline=False)
            copy_command = f'/draw prompt:{rev[15]} data_model:{model_name} steps:{rev[4]} height:{str(rev[5])} width:{rev[6]} guidance_scale:{rev[7]} sampler:{rev[8]} seed:{rev[9]} count:{rev[12]}'
            if rev[2] != '':
                copy_command = copy_command + f' negative_prompt:{rev[2]}'
                embed.add_field(name=f'Negative prompt', value=f'``{rev[2]}``', inline=False)
            if activator_token:
                embed.add_field(name=f'Data model', value=f'Display name - ``{model_name}``\nFull name - ``{rev[3]}``\nActivator token - ``{activator_token}``', inline=False)
            else:
                embed.add_field(name=f'Data model', value=f'Display name - ``{model_name}``\nFull name - ``{rev[3]}``', inline=False)
            embed.add_field(name=f'Sampling steps', value=f'``{rev[4]}``', inline=False)
            embed.add_field(name=f'Size', value=f'``{rev[5]}x{rev[6]}``', inline=False)
            embed.add_field(name=f'Classifier-free guidance scale', value=f'``{rev[7]}``', inline=False)
            embed.add_field(name=f'Sampling method', value=f'``{rev[8]}``', inline=False)
            embed.add_field(name=f'Seed', value=f'``{rev[9]}``', inline=False)
            if rev[11]:
                #not interested in adding embed fields for strength and init_image
                copy_command = copy_command + f' strength:{rev[10]} init_url:{rev[11]}'
            if rev[13] != 'None':
                copy_command = copy_command + f' style:{rev[13]}'
                embed.add_field(name=f'Style preset', value=f'``{rev[13]}``', inline=False)
            if rev[14] != 'None':
                copy_command = copy_command + f' facefix:{rev[14]}'
                embed.add_field(name=f'Face restoration model', value=f'``{rev[14]}``', inline=False)
            embed.add_field(name=f'Command for copying', value=f'``{copy_command}``', inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except(Exception,):
            # if interaction fails, assume it's because aiya restarted (breaks buttons)
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("I may have been restarted. This button no longer works.", ephemeral=True)

    #the button to delete generated images
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
                await interaction.followup.send("I may have been restarted. This button no longer works.", ephemeral=True)


#creating the view that holds the buttons for /identify output
class DeleteView(discord.ui.View):
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