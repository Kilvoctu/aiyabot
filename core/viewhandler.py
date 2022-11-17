import discord
import random

from core import queuehandler
from core import stablecog

#creating the view that holds the buttons for /draw output
class DrawView(discord.ui.View):
    def __init__(self, input_tuple):
        super().__init__(timeout=None)
        self.input_tuple = input_tuple

    @discord.ui.button(
        custom_id="button_reroll", emoji="🎲")
    async def button_callback(self, button, interaction):
        try:
            #check if the /draw output is from the person who requested it
            if self.message.embeds[0].footer.text == f'{interaction.user.name}#{interaction.user.discriminator}':
                #update the tuple with a new seed
                new_seed = list(self.input_tuple)
                new_seed[9] = random.randint(0, 0xFFFFFFFF)
                self.input_tuple = tuple(new_seed)

                #set up the draw dream and do queue code again for lack of a more elegant solution
                draw_dream = stablecog.StableCog(self)
                if queuehandler.GlobalQueue.dream_thread.is_alive():
                    user_already_in_queue = False
                    for queue_object in queuehandler.union(queuehandler.GlobalQueue.draw_q, queuehandler.GlobalQueue.upscale_q, queuehandler.GlobalQueue.identify_q):
                        if queue_object.ctx.author.id == interaction.user.id:
                            user_already_in_queue = True
                            break
                    if user_already_in_queue:
                        await interaction.response.send_message(content=f"Please wait! You're queued up.", ephemeral=True)
                    else:
                        button.disabled = True
                        await interaction.response.edit_message(view=self)
                        queuehandler.GlobalQueue.draw_q.append(queuehandler.DrawObject(*self.input_tuple, DrawView(self.input_tuple)))
                        await interaction.followup.send(f'<@{interaction.user.id}>, redrawing the image!\nQueue: ``{len(queuehandler.union(queuehandler.GlobalQueue.draw_q, queuehandler.GlobalQueue.upscale_q, queuehandler.GlobalQueue.identify_q))}`` - ``{new_seed[16]}``\nNew seed:``{new_seed[9]}``')
                else:
                    button.disabled = True
                    await interaction.response.edit_message(view=self)
                    await queuehandler.process_dream(draw_dream, queuehandler.DrawObject(*self.input_tuple, DrawView(self.input_tuple)))
                    await interaction.followup.send(f'<@{interaction.user.id}>, redrawing the image!\nQueue: ``{len(queuehandler.union(queuehandler.GlobalQueue.draw_q, queuehandler.GlobalQueue.upscale_q, queuehandler.GlobalQueue.identify_q))}`` - ``{new_seed[16]}``\nNew Seed:``{new_seed[9]}``')
            else:
                await interaction.response.send_message("You can't use other people's buttons!", ephemeral=True)
        except:
            #if interaction fails, assume it's because aiya restarted (breaks buttons)
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
        except:
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
            await interaction.message.delete()
        else:
            await interaction.response.send_message("You can't delete other people's images!", ephemeral=True)