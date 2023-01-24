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
[18] = hypernet
'''
tuple_names = ['ctx', 'prompt', 'negative_prompt', 'data_model', 'steps', 'width', 'height', 'guidance_scale',
               'sampler', 'seed', 'strength', 'init_image', 'batch_count', 'style', 'facefix', 'highres_fix',
               'clip_skip', 'simple_prompt', 'hypernet']


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
                label='Keep seed? Delete to randomize',
                style=discord.InputTextStyle.short,
                value=input_tuple[9],
                required=False
            )
        )

        # set up parameters for full edit mode. first get model display name
        display_name = 'Default'
        index_start = 4
        for model in settings.global_var.model_info.items():
            if model[1][0] == input_tuple[3]:
                display_name = model[0]
                break
        # expose each available (supported) option, even if output didn't use them
        ex_params = f'data_model:{display_name}'
        for index, value in enumerate(tuple_names[index_start:], index_start):
            if index == 9 or 11 <= index <= 12 or index == 15 or index == 17:
                continue
            ex_params += f'\n{value}:{input_tuple[index]}'

        self.add_item(
            InputText(
                label='Extended edit (for advanced user!)',
                style=discord.InputTextStyle.long,
                value=ex_params,
                required=False
            )
        )

    async def callback(self, interaction: discord.Interaction):
        # update the tuple with new prompts
        pen = list(self.input_tuple)
        pen[1] = pen[1].replace(pen[17], self.children[0].value)
        pen[17] = self.children[0].value
        pen[2] = self.children[1].value

        # update the tuple new seed (random if invalid value set)
        try:
            pen[9] = int(self.children[2].value)
        except ValueError:
            pen[9] = random.randint(0, 0xFFFFFFFF)
        if (self.children[2].value == "-1") or (self.children[2].value == ""):
            pen[9] = random.randint(0, 0xFFFFFFFF)

        # prepare a validity checker
        new_model, new_token, bad_input = '', '', ''
        model_found = False
        invalid_input = False
        embed_err = discord.Embed(title="I can't redraw this!", description="")

        # iterate through extended edit for any changes
        for line in self.children[3].value.split('\n'):
            if 'data_model:' in line:
                new_model = line.split(':', 1)[1]
                # if keeping the "Default" model, don't attempt a model swap
                if new_model == 'Default':
                    pass
                else:
                    for model in settings.global_var.model_info.items():
                        if model[0] == new_model:
                            pen[3] = model[1][0]
                            model_found = True
                            # grab the new activator token
                            new_token = f'{model[1][3]} '.lstrip(' ')
                            break
                    if not model_found:
                        invalid_input = True
                        embed_err.add_field(name=f"`{line.split(':', 1)[1]}` is not found. Try one of these models!",
                                            value=', '.join(['`%s`' % x for x in settings.global_var.model_info]),
                                            inline=False)

            if 'steps:' in line:
                max_steps = settings.read('% s' % pen[0].channel.id)['max_steps']
                if 0 < int(line.split(':', 1)[1]) <= max_steps:
                    pen[4] = line.split(':', 1)[1]
                else:
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` steps is beyond the boundary!",
                                        value=f"Keep steps between `0` and `{max_steps}`.", inline=False)
            if 'width:' in line:
                try:
                    pen[5] = [x for x in settings.global_var.size_range if x == int(line.split(':', 1)[1])][0]
                except(Exception,):
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` width is no good! These widths I can do.",
                                        value=', '.join(['`%s`' % x for x in settings.global_var.size_range]),
                                        inline=False)
            if 'height:' in line:
                try:
                    pen[6] = [x for x in settings.global_var.size_range if x == int(line.split(':', 1)[1])][0]
                except(Exception,):
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` height is no good! These heights I can do.",
                                        value=', '.join(['`%s`' % x for x in settings.global_var.size_range]),
                                        inline=False)
            if 'guidance_scale:' in line:
                try:
                    pen[7] = float(line.split(':', 1)[1])
                except(Exception,):
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` is not valid for the guidance scale!",
                                        value='Make sure you enter a number.', inline=False)
            if 'sampler:' in line:
                if line.split(':', 1)[1] in settings.global_var.sampler_names:
                    pen[8] = line.split(':', 1)[1]
                else:
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` is unrecognized. I know of these samplers!",
                                        value=', '.join(['`%s`' % x for x in settings.global_var.sampler_names]),
                                        inline=False)
            if 'strength:' in line:
                try:
                    pen[10] = float(line.split(':', 1)[1])
                except(Exception,):
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` is not valid for strength!.",
                                        value='Make sure you enter a number (preferably between 0.0 and 1.0).',
                                        inline=False)
            if 'style:' in line:
                if line.split(':', 1)[1] in settings.global_var.style_names.keys():
                    pen[13] = line.split(':', 1)[1]
                else:
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` isn't my style. Here's the style list!",
                                        value=', '.join(['`%s`' % x for x in settings.global_var.style_names]),
                                        inline=False)
            if 'facefix:' in line:
                if line.split(':', 1)[1] in settings.global_var.facefix_models:
                    pen[14] = line.split(':', 1)[1]
                else:
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` can't fix faces! I have suggestions.",
                                        value=', '.join(['`%s`' % x for x in settings.global_var.facefix_models]),
                                        inline=False)
            if 'clip_skip:' in line:
                try:
                    pen[16] = [x for x in range(1, 13, 1) if x == int(line.split(':', 1)[1])][0]
                except(Exception,):
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` is too much CLIP to skip!",
                                        value='The range is from `1` to `12`.', inline=False)
            if 'hypernet:' in line:
                if line.split(':', 1)[1] in settings.global_var.hyper_names:
                    pen[18] = line.split(':', 1)[1]
                else:
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` isn't one of these hypernetworks!",
                                        value=', '.join(['`%s`' % x for x in settings.global_var.hyper_names]),
                                        inline=False)

        # stop and give a useful message if any extended edit values aren't recognized
        if invalid_input:
            await interaction.response.send_message(embed=embed_err, ephemeral=True)
        else:
            # update the prompt again if a valid model change is requested
            if model_found:
                pen[1] = new_token + pen[17]
            # if a hypernetwork is added, append it to prompt
            if pen[18] != 'None':
                pen[1] += f' <hypernet:{pen[18]}:1>'

            # the updated tuple to send to queue
            prompt_tuple = tuple(pen)
            draw_dream = stablecog.StableCog(self)

            # message additions if anything was changed
            prompt_output = f'\nNew prompt: ``{pen[17]}``'
            if pen[2] != '' and pen[2] != self.input_tuple[2]:
                prompt_output += f'\nNew negative prompt: ``{pen[2]}``'
            if str(pen[3]) != str(self.input_tuple[3]):
                prompt_output += f'\nNew model: ``{new_model}``'
            index_start = 4
            for index, value in enumerate(tuple_names[index_start:], index_start):
                if index == 17:
                    continue
                if str(pen[index]) != str(self.input_tuple[index]):
                    prompt_output += f'\nNew {value}: ``{pen[index]}``'

            # check queue again, but now we know user is not in queue
            settings.global_var.send_model = False
            if queuehandler.GlobalQueue.dream_thread.is_alive():
                if prompt_tuple[3] != '' and self.input_tuple[3] != prompt_tuple[3]:
                    settings.global_var.send_model = True
                queuehandler.GlobalQueue.queue.append(queuehandler.DrawObject(stablecog.StableCog(self), *prompt_tuple, DrawView(prompt_tuple)))
                await interaction.response.send_message(
                    f'<@{interaction.user.id}>, {settings.messages()}\nQueue: ``{len(queuehandler.GlobalQueue.queue)}``{prompt_output}')
            else:
                if prompt_tuple[3] != '' and self.input_tuple[3] != prompt_tuple[3]:
                    settings.global_var.send_model = True
                await queuehandler.process_dream(draw_dream, queuehandler.DrawObject(stablecog.StableCog(self), *prompt_tuple, DrawView(prompt_tuple)))
                await interaction.response.send_message(
                    f'<@{interaction.user.id}>, {settings.messages()}\nQueue: ``{len(queuehandler.GlobalQueue.queue)}``{prompt_output}')


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
            # check if the output is from the person who requested it
            end_user = f'{interaction.user.name}#{interaction.user.discriminator}'
            if end_user in self.message.content:
                # if there's room in the queue, open up the modal
                if queuehandler.GlobalQueue.dream_thread.is_alive():
                    user_already_in_queue = False
                    for queue_object in queuehandler.GlobalQueue.queue:
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
        except Exception as e:
            print('The pen button broke: ' + str(e))
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
            # check if the output is from the person who requested it
            end_user = f'{interaction.user.name}#{interaction.user.discriminator}'
            if end_user in self.message.content:
                # update the tuple with a new seed
                new_seed = list(self.input_tuple)
                new_seed[9] = random.randint(0, 0xFFFFFFFF)
                seed_tuple = tuple(new_seed)

                # set up the draw dream and do queue code again for lack of a more elegant solution
                draw_dream = stablecog.StableCog(self)
                if queuehandler.GlobalQueue.dream_thread.is_alive():
                    user_already_in_queue = False
                    for queue_object in queuehandler.GlobalQueue.queue:
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

                        queuehandler.GlobalQueue.queue.append(queuehandler.DrawObject(stablecog.StableCog(self), *seed_tuple, DrawView(seed_tuple)))
                        await interaction.followup.send(
                            f'<@{interaction.user.id}>, {settings.messages()}\nQueue: '
                            f'``{len(queuehandler.GlobalQueue.queue)}`` - ``{seed_tuple[17]}``'
                            f'\nNew seed:``{seed_tuple[9]}``')
                else:
                    button.disabled = True
                    await interaction.response.edit_message(view=self)

                    if self.input_tuple[3] != '':
                        settings.global_var.send_model = True

                    await queuehandler.process_dream(draw_dream, queuehandler.DrawObject(stablecog.StableCog(self), *seed_tuple, DrawView(seed_tuple)))
                    await interaction.followup.send(
                        f'<@{interaction.user.id}>, {settings.messages()}\nQueue: '
                        f'``{len(queuehandler.GlobalQueue.queue)}`` - ``{seed_tuple[17]}``'
                        f'\nNew Seed:``{seed_tuple[9]}``')
            else:
                await interaction.response.send_message("You can't use other people's 🎲!", ephemeral=True)
        except Exception as e:
            print('The dice roll button broke: ' + str(e))
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
        # initial dummy data for a default models.csv
        display_name = 'Default'
        model_name, model_hash = 'Unknown', 'Unknown'
        activator_token = ''
        try:
            # get the remaining model information we want from the data_model ("title") in the tuple
            for model in settings.global_var.model_info.items():
                if model[1][0] == rev[3]:
                    display_name = model[0]
                    model_name = model[1][1]
                    model_hash = model[1][2]
                    if model[1][3]:
                        activator_token = f'\nActivator token - ``{model[1][3]}``'
                    break

            # strip any folders from model name
            model_name = model_name.split('_', 1)[-1]

            # generate the command for copy-pasting, and also add embed fields
            embed = discord.Embed(title="About the image!", description="")
            embed.colour = settings.global_var.embed_color
            embed.add_field(name=f'Prompt', value=f'``{rev[17]}``', inline=False)
            embed.add_field(name='Data model', value=f'Display name - ``{display_name}``\nModel name - ``{model_name}``'
                                                     f'\nShorthash - ``{model_hash}``{activator_token}', inline=False)

            copy_command = f'/draw prompt:{rev[17]} data_model:{display_name} steps:{rev[4]} width:{rev[5]} ' \
                           f'height:{rev[6]} guidance_scale:{rev[7]} sampler:{rev[8]} seed:{rev[9]}'
            if rev[2] != '':
                copy_command += f' negative_prompt:{rev[2]}'
                embed.add_field(name=f'Negative prompt', value=f'``{rev[2]}``', inline=False)

            extra_params = f'Sampling steps: ``{rev[4]}``\nSize: ``{rev[5]}x{rev[6]}``\nClassifier-free guidance ' \
                           f'scale: ``{rev[7]}``\nSampling method: ``{rev[8]}``\nSeed: ``{rev[9]}``'
            if rev[11]:
                # not interested in adding embed fields for strength and init_image
                copy_command += f' strength:{rev[10]} init_url:{rev[11].url}'
            if rev[12] != 1:
                copy_command += f' count:{rev[12]}'
            if rev[13] != 'None':
                copy_command += f' style:{rev[13]}'
                extra_params += f'\nStyle preset: ``{rev[13]}``'
            if rev[14] != 'None':
                copy_command += f' facefix:{rev[14]}'
                extra_params += f'\nFace restoration model: ``{rev[14]}``'
            if rev[15] != 'Disabled':
                copy_command += f' highres_fix:{rev[15]}'
                extra_params += f'\nHigh-res fix: ``{rev[15]}``'
            if rev[16] != 1:
                copy_command += f' clip_skip:{rev[16]}'
                extra_params += f'\nCLIP skip: ``{rev[16]}``'
            if rev[18] != 'None':
                copy_command += f' hypernet:{rev[18]}'
                extra_params += f'\nHypernetwork model: ``{rev[18]}``'
            embed.add_field(name=f'Other parameters', value=extra_params, inline=False)
            embed.add_field(name=f'Command for copying', value=f'{copy_command}', inline=False)

            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            print('The clipboard button broke: ' + str(e))
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
            # check if the output is from the person who requested it
            end_user = f'{interaction.user.name}#{interaction.user.discriminator}'
            if end_user in self.message.content:
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
        # check if the output is from the person who requested it
        if interaction.user.id == self.user:
            button.disabled = True
            await interaction.message.delete()
        else:
            await interaction.response.send_message("You can't delete other people's images!", ephemeral=True)
