import discord
import random
from discord.ui import InputText, Modal, View

from core import queuehandler
from core import settings
from core import stablecog

'''
The input_tuple index reference
input_tuple[0] = ctx
[1] = simple_prompt
[2] = prompt
[3] = negative_prompt
[4] = data_model
[5] = steps
[6] = width
[7] = height
[8] = guidance_scale
[9] = sampler
[10] = seed
[11] = strength
[12] = init_image
[13] = count
[14] = style
[15] = facefix
[16] = highres_fix
[17] = clip_skip
[18] = hypernet
[19] = lora
'''
tuple_names = ['ctx', 'simple_prompt', 'prompt', 'negative_prompt', 'data_model', 'steps', 'width', 'height',
               'guidance_scale', 'sampler', 'seed', 'strength', 'init_image', 'batch', 'style', 'facefix',
               'highres_fix', 'clip_skip', 'hypernet', 'lora']


# the modal that is used for the 🖋 button
class DrawModal(Modal):
    def __init__(self, input_tuple) -> None:
        super().__init__(title="Change Prompt!")
        self.input_tuple = input_tuple

        # run through mod function to get clean negative since I don't want to add it to stablecog tuple
        self.clean_negative = input_tuple[3]
        if settings.global_var.negative_prompt_prefix:
            mod_results = settings.prompt_mod(input_tuple[2], input_tuple[3])
            if settings.global_var.negative_prompt_prefix and mod_results[0] == "Mod":
                self.clean_negative = mod_results[3]

        self.add_item(
            InputText(
                label='Input your new prompt',
                value=input_tuple[1],
                style=discord.InputTextStyle.long
            )
        )
        self.add_item(
            InputText(
                label='Input your new negative prompt (optional)',
                style=discord.InputTextStyle.long,
                value=self.clean_negative,
                required=False
            )
        )
        self.add_item(
            InputText(
                label='Keep seed? Delete to randomize',
                style=discord.InputTextStyle.short,
                value=input_tuple[10],
                required=False
            )
        )

        # set up parameters for full edit mode. first get model display name
        display_name = 'Default'
        index_start = 5
        for model in settings.global_var.model_info.items():
            if model[1][0] == input_tuple[4]:
                display_name = model[0]
                break
        # expose each available (supported) option, even if output didn't use them
        ex_params = f'data_model:{display_name}'
        for index, value in enumerate(tuple_names[index_start:], index_start):
            if index == 10 or 12 <= index <= 13 or index == 16:
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
        pen[2] = pen[2].replace(pen[1], self.children[0].value)
        pen[1] = self.children[0].value
        pen[3] = self.children[1].value

        # update the tuple new seed (random if invalid value set)
        try:
            pen[10] = int(self.children[2].value)
        except ValueError:
            pen[10] = random.randint(0, 0xFFFFFFFF)
        if (self.children[2].value == "-1") or (self.children[2].value == ""):
            pen[10] = random.randint(0, 0xFFFFFFFF)

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
                            pen[4] = model[1][0]
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
                    pen[5] = line.split(':', 1)[1]
                else:
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` steps is beyond the boundary!",
                                        value=f"Keep steps between `0` and `{max_steps}`.", inline=False)
            if 'width:' in line:
                try:
                    pen[6] = [x for x in settings.global_var.size_range if x == int(line.split(':', 1)[1])][0]
                except(Exception,):
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` width is no good! These widths I can do.",
                                        value=', '.join(['`%s`' % x for x in settings.global_var.size_range]),
                                        inline=False)
            if 'height:' in line:
                try:
                    pen[7] = [x for x in settings.global_var.size_range if x == int(line.split(':', 1)[1])][0]
                except(Exception,):
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` height is no good! These heights I can do.",
                                        value=', '.join(['`%s`' % x for x in settings.global_var.size_range]),
                                        inline=False)
            if 'guidance_scale:' in line:
                try:
                    pen[8] = float(line.split(':', 1)[1].replace(",", "."))
                except(Exception,):
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` is not valid for the guidance scale!",
                                        value='Make sure you enter a number.', inline=False)
            if 'sampler:' in line:
                if line.split(':', 1)[1] in settings.global_var.sampler_names:
                    pen[9] = line.split(':', 1)[1]
                else:
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` is unrecognized. I know of these samplers!",
                                        value=', '.join(['`%s`' % x for x in settings.global_var.sampler_names]),
                                        inline=False)
            if 'strength:' in line:
                try:
                    pen[11] = float(line.split(':', 1)[1].replace(",", "."))
                except(Exception,):
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` is not valid for strength!.",
                                        value='Make sure you enter a number (preferably between 0.0 and 1.0).',
                                        inline=False)
            if 'style:' in line:
                if line.split(':', 1)[1] in settings.global_var.style_names.keys():
                    pen[14] = line.split(':', 1)[1]
                else:
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` isn't my style. Here's the style list!",
                                        value=', '.join(['`%s`' % x for x in settings.global_var.style_names]),
                                        inline=False)
            if 'facefix:' in line:
                if line.split(':', 1)[1] in settings.global_var.facefix_models:
                    pen[15] = line.split(':', 1)[1]
                else:
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` can't fix faces! I have suggestions.",
                                        value=', '.join(['`%s`' % x for x in settings.global_var.facefix_models]),
                                        inline=False)
            if 'clip_skip:' in line:
                try:
                    pen[17] = [x for x in range(1, 14, 1) if x == int(line.split(':', 1)[1])][0]
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

            if 'lora:' in line:
                if line.split(':', 1)[1] in settings.global_var.lora_names:
                    pen[19] = line.split(':', 1)[1]
                else:
                    invalid_input = True
                    embed_err.add_field(name=f"`{line.split(':', 1)[1]}` can't be found! Try one of these LoRA.",
                                        value=', '.join(['`%s`' % x for x in settings.global_var.lora_names]),
                                        inline=False)

        # stop and give a useful message if any extended edit values aren't recognized
        if invalid_input:
            await interaction.response.send_message(embed=embed_err, ephemeral=True)
        else:
            # run through mod function if any moderation values are set in config
            new_clean_negative = ''
            if settings.global_var.prompt_ban_list or settings.global_var.prompt_ignore_list or settings.global_var.negative_prompt_prefix:
                mod_results = settings.prompt_mod(self.children[0].value, self.children[1].value)
                if settings.global_var.prompt_ban_list and mod_results[0] == "Stop":
                    await interaction.response.send_message(f"I'm not allowed to draw the word {mod_results[1]}!", ephemeral=True)
                    return
                if settings.global_var.prompt_ignore_list or settings.global_var.negative_prompt_prefix and mod_results[0] == "Mod":
                    if settings.global_var.display_ignored_words == "False":
                        pen[1] = mod_results[1]
                    pen[2] = mod_results[1]
                    pen[3] = mod_results[2]
                    new_clean_negative = mod_results[3]

            # update the prompt again if a valid model change is requested
            if model_found:
                pen[2] = new_token + pen[1]
            # if a hypernetwork or lora is added, append it to prompt
            if pen[18] != 'None':
                pen[2] += f' <hypernet:{pen[18]}:0.85>'
            if pen[19] != 'None':
                pen[2] += f' <lora:{pen[19]}:0.85>'

            # the updated tuple to send to queue
            prompt_tuple = tuple(pen)
            draw_dream = stablecog.StableCog(self)

            # message additions if anything was changed
            prompt_output = f'\nNew prompt: ``{pen[1]}``'
            if new_clean_negative != '' and new_clean_negative != self.clean_negative:
                prompt_output += f'\nNew negative prompt: ``{new_clean_negative}``'
            if str(pen[4]) != str(self.input_tuple[4]):
                prompt_output += f'\nNew model: ``{new_model}``'
            index_start = 5
            for index, value in enumerate(tuple_names[index_start:], index_start):
                if index == 17:
                    continue
                if str(pen[index]) != str(self.input_tuple[index]):
                    prompt_output += f'\nNew {value}: ``{pen[index]}``'

            print(f'Redraw -- {interaction.user.name}#{interaction.user.discriminator} -- Prompt: {pen[1]}')

            # check queue again, but now we know user is not in queue
            if queuehandler.GlobalQueue.dream_thread.is_alive():
                queuehandler.GlobalQueue.queue.append(queuehandler.DrawObject(stablecog.StableCog(self), *prompt_tuple, DrawView(prompt_tuple)))
            else:
                await queuehandler.process_dream(draw_dream, queuehandler.DrawObject(stablecog.StableCog(self), *prompt_tuple, DrawView(prompt_tuple)))
            await interaction.response.send_message(f'<@{interaction.user.id}>, {settings.messages()}\nQueue: ``{len(queuehandler.GlobalQueue.queue)}``{prompt_output}')


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
            if interaction.user.id == self.input_tuple[0].author.id:
                # if there's room in the queue, open up the modal
                user_queue_limit = settings.queue_check(interaction.user)
                if queuehandler.GlobalQueue.dream_thread.is_alive():
                    if user_queue_limit == "Stop":
                        await interaction.response.send_message(content=f"Please wait! You're past your queue limit of {settings.global_var.queue_limit}.", ephemeral=True)
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
            if interaction.user.id == self.input_tuple[0].author.id:
                # update the tuple with a new seed
                new_seed = list(self.input_tuple)
                new_seed[10] = random.randint(0, 0xFFFFFFFF)
                seed_tuple = tuple(new_seed)

                print(f'Reroll -- {interaction.user.name}#{interaction.user.discriminator} -- Prompt: {seed_tuple[1]}')

                # set up the draw dream and do queue code again for lack of a more elegant solution
                draw_dream = stablecog.StableCog(self)
                user_queue_limit = settings.queue_check(interaction.user)
                if queuehandler.GlobalQueue.dream_thread.is_alive():
                    if user_queue_limit == "Stop":
                        await interaction.response.send_message(content=f"Please wait! You're past your queue limit of {settings.global_var.queue_limit}.", ephemeral=True)
                    else:
                        queuehandler.GlobalQueue.queue.append(queuehandler.DrawObject(stablecog.StableCog(self), *seed_tuple, DrawView(seed_tuple)))
                else:
                    await queuehandler.process_dream(draw_dream, queuehandler.DrawObject(stablecog.StableCog(self), *seed_tuple, DrawView(seed_tuple)))

                if user_queue_limit != "Stop":
                    await interaction.response.send_message(
                        f'<@{interaction.user.id}>, {settings.messages()}\nQueue: '
                        f'``{len(queuehandler.GlobalQueue.queue)}`` - ``{seed_tuple[1]}``'
                        f'\nNew Seed:``{seed_tuple[10]}``')
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
                if model[1][0] == rev[4] and model[1][0] != "Default":
                    display_name = model[0]
                    model_name = model[1][1]
                    model_hash = model[1][2]
                    if model[1][3]:
                        activator_token = f'\nActivator token - ``{model[1][3]}``'
                    break

            # strip any folders from model name
            model_name = model_name.split('_', 1)[-1]

            # run through mod function to get clean negative since I don't want to add it to stablecog tuple
            clean_negative = rev[3]
            if settings.global_var.negative_prompt_prefix:
                mod_results = settings.prompt_mod(rev[2], rev[3])
                if settings.global_var.negative_prompt_prefix and mod_results[0] == "Mod":
                    clean_negative = mod_results[3]

            # generate the command for copy-pasting, and also add embed fields
            embed = discord.Embed(title="About the image!", description="")
            prompt_field = rev[1]
            if len(prompt_field) > 1024:
                prompt_field = f'{prompt_field[:1010]}....'
            embed.colour = settings.global_var.embed_color
            embed.add_field(name=f'Prompt', value=f'``{prompt_field}``', inline=False)
            embed.add_field(name='Data model', value=f'Display name - ``{display_name}``\nModel name - ``{model_name}``'
                                                     f'\nShorthash - ``{model_hash}``{activator_token}', inline=False)

            copy_command = f'/draw prompt:{rev[1]} data_model:{display_name} steps:{rev[5]} width:{rev[6]} ' \
                           f'height:{rev[7]} guidance_scale:{rev[8]} sampler:{rev[9]} seed:{rev[10]}'
            if rev[3] != '':
                copy_command += f' negative_prompt:{clean_negative}'
                n_prompt_field = clean_negative
                if len(n_prompt_field) > 1024:
                    n_prompt_field = f'{n_prompt_field[:1010]}....'
                embed.add_field(name=f'Negative prompt', value=f'``{n_prompt_field}``', inline=False)

            extra_params = f'Sampling steps: ``{rev[5]}``\nSize: ``{rev[6]}x{rev[7]}``\nClassifier-free guidance ' \
                           f'scale: ``{rev[8]}``\nSampling method: ``{rev[9]}``\nSeed: ``{rev[10]}``'
            if rev[12]:
                # not interested in adding embed fields for strength and init_image
                copy_command += f' strength:{rev[11]} init_url:{rev[12].url}'
            if rev[13][0] != 1 or rev[13][1] != 1:
                bat_string = ','.join(str(x) for x in rev[13])
                bat_copy = settings.batch_format(bat_string)
                copy_command += f' batch:{bat_copy[0]},{bat_copy[1]}'
            if rev[14] != 'None':
                copy_command += f' style:{rev[14]}'
                extra_params += f'\nStyle preset: ``{rev[14]}``'
            if rev[15] != 'None':
                copy_command += f' facefix:{rev[15]}'
                extra_params += f'\nFace restoration model: ``{rev[15]}``'
            if rev[16] != 'Disabled':
                copy_command += f' highres_fix:{rev[16]}'
                extra_params += f'\nHigh-res fix: ``{rev[16]}``'
            if rev[17] != 1:
                copy_command += f' clip_skip:{rev[17]}'
                extra_params += f'\nCLIP skip: ``{rev[17]}``'
            if rev[18] != 'None':
                copy_command += f' hypernet:{rev[18]}'
                extra_params += f'\nHypernetwork model: ``{rev[18]}``'
            if rev[19] != 'None':
                copy_command += f' lora:{rev[19]}'
                extra_params += f'\nLoRA model: ``{rev[19]}``'
            embed.add_field(name=f'Other parameters', value=extra_params, inline=False)
            embed.add_field(name=f'Command for copying', value=f'', inline=False)
            embed.set_footer(text=copy_command)
            if len(copy_command) > 2048:
                button.disabled = True
                await interaction.response.edit_message(view=self)
                await interaction.followup.send("The contents of 📋 exceeded Discord's character limit! Sorry, I can't display it...", ephemeral=True)

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
            if interaction.user.id == self.input_tuple[0].author.id:
                await interaction.message.delete()
            else:
                await interaction.response.send_message("You can't delete other people's images!", ephemeral=True)
        except(Exception,):
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("I may have been restarted. This button no longer works.\n"
                                            "You can react with ❌ to delete the image.", ephemeral=True)

class DeleteView(View):
    def __init__(self, input_tuple):
        super().__init__(timeout=None)
        self.input_tuple = input_tuple

    @discord.ui.button(
        custom_id="button_x_solo",
        emoji="❌")
    async def delete(self, button, interaction):
        try:
            # check if the output is from the person who requested it
            if interaction.user.id == self.input_tuple[0].author.id:
                await interaction.message.delete()
            else:
                await interaction.response.send_message("You can't delete other people's images!", ephemeral=True)
        except(Exception,):
            button.disabled = True
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("I may have been restarted. This button no longer works.\n"
                                            "You can react with ❌ to delete the image.", ephemeral=True)
