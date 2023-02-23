import discord
from discord import option
from discord.ext import commands
from typing import Optional

from core import settings


class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # pulls from model_names list and makes some sort of dynamic list to bypass Discord 25 choices limit
    # these are used also by stablecog /draw command
    # this also updates list when using /settings "refresh" option
    def model_autocomplete(self: discord.AutocompleteContext):
        return [
            model for model in settings.global_var.model_info
        ]

    # do for any other lists that may exceed 25 values
    def style_autocomplete(self: discord.AutocompleteContext):
        return [
            style for style in settings.global_var.style_names
        ]

    def hyper_autocomplete(self: discord.AutocompleteContext):
        return [
            hyper for hyper in settings.global_var.hyper_names
        ]

    def lora_autocomplete(self: discord.AutocompleteContext):
        return [
            lora for lora in settings.global_var.lora_names
        ]

    def upscaler_autocomplete(self: discord.AutocompleteContext):
        return [
            upscaler for upscaler in settings.global_var.upscaler_names
        ]

    def hires_autocomplete(self: discord.AutocompleteContext):
        return [
            hires for hires in settings.global_var.hires_upscaler_names
        ]

    @commands.slash_command(name='settings', description='Review and change channel defaults', guild_only=True)
    @option(
        'current_settings',
        bool,
        description='Show the current defaults for the channel.',
        required=False,
    )
    @option(
        'n_prompt',
        str,
        description='Set default negative prompt for the channel (put "reset" to return to empty prompt)',
        required=False,
    )
    @option(
        'data_model',
        str,
        description='Set default data model for image generation',
        required=False,
        autocomplete=discord.utils.basic_autocomplete(model_autocomplete),
    )
    @option(
        'steps',
        int,
        description='Set default amount of steps for the channel',
        min_value=1,
        required=False,
    )
    @option(
        'max_steps',
        int,
        description='Set maximum steps for the channel',
        min_value=1,
        required=False,
    )
    @option(
        'width',
        int,
        description='Set default width for the channel',
        required=False,
        choices=[x for x in range(192, 1088, 64)]
    )
    @option(
        'height',
        int,
        description='Set default height for the channel',
        required=False,
        choices=[x for x in range(192, 1088, 64)]
    )
    @option(
        'guidance_scale',
        str,
        description='Set default Classifier-Free Guidance scale for the channel.',
        required=False,
    )
    @option(
        'sampler',
        str,
        description='Set default sampler for the channel',
        required=False,
        choices=settings.global_var.sampler_names,
    )
    @option(
        'style',
        str,
        description='Apply a predefined style to the generation.',
        required=False,
        autocomplete=discord.utils.basic_autocomplete(style_autocomplete),
    )
    @option(
        'facefix',
        str,
        description='Tries to improve faces in images.',
        required=False,
        choices=settings.global_var.facefix_models,
    )
    @option(
        'highres_fix',
        str,
        description='Set default highres fix model for the channel',
        required=False,
        autocomplete=discord.utils.basic_autocomplete(hires_autocomplete),
    )
    @option(
        'clip_skip',
        int,
        description='Set default CLIP skip for the channel',
        required=False,
        choices=[x for x in range(1, 13, 1)]
    )
    @option(
        'hypernet',
        str,
        description='Set default hypernetwork model for the channel',
        required=False,
        autocomplete=discord.utils.basic_autocomplete(hyper_autocomplete),
    )
    @option(
        'lora',
        str,
        description='Set default LoRA for the channel',
        required=False,
        autocomplete=discord.utils.basic_autocomplete(lora_autocomplete),
    )
    @option(
        'strength',
        str,
        description='Set default strength (for init_img) for the channel (0.0 to 1.0).'
    )
    @option(
        'batch',
        str,
        description='Set default batch for the channel (count,size)',
        required=False,
    )
    @option(
        'max_batch',
        str,
        description='Set maximum batch for the channel (count,size)',
        required=False,
    )
    @option(
        'upscaler_1',
        str,
        description='Set default upscaler model for the channel.',
        required=True,
        autocomplete=discord.utils.basic_autocomplete(upscaler_autocomplete),
    )
    @option(
        'refresh',
        bool,
        description='Use to update global lists (models, styles, embeddings, etc.)',
        required=False,
    )
    async def settings_handler(self, ctx,
                               current_settings: Optional[bool] = True,
                               n_prompt: Optional[str] = None,
                               data_model: Optional[str] = None,
                               steps: Optional[int] = None,
                               max_steps: Optional[int] = 1,
                               width: Optional[int] = None, height: Optional[int] = None,
                               guidance_scale: Optional[str] = None,
                               sampler: Optional[str] = None,
                               style: Optional[str] = None,
                               facefix: Optional[str] = None,
                               highres_fix: Optional[str] = None,
                               clip_skip: Optional[int] = None,
                               hypernet: Optional[str] = None,
                               lora: Optional[str] = None,
                               strength: Optional[str] = None,
                               batch: Optional[str] = None,
                               max_batch: Optional[str] = None,
                               upscaler_1: Optional[str] = None,
                               refresh: Optional[bool] = False):
        # get the channel id and check if a settings file exists
        channel = '% s' % ctx.channel.id
        settings.check(channel)
        reviewer = settings.read(channel)
        # create the embed for the reply
        embed = discord.Embed(title="Channel Defaults Summary", description="")
        embed.set_footer(text=f'Channel id: {channel}')
        embed.colour = settings.global_var.embed_color
        current, new, new_n_prompt = '', '', ''
        set_new = False

        if current_settings:
            cur_set = settings.read(channel)
            for key, value in cur_set.items():
                if key == 'negative_prompt':
                    pass
                else:
                    if value == '':
                        value = ' '
                    current += f'\n{key} - ``{value}``'
            embed.add_field(name=f'Current parameters', value=current, inline=True)
            # put negative prompt on new field for hosts who like massive negative prompts
            cur_n_prompt = f'{cur_set["negative_prompt"]}'
            if cur_n_prompt == '':
                cur_n_prompt = ' '
            elif len(cur_n_prompt) > 1024:
                cur_n_prompt = f'{cur_n_prompt[:1010]}....'
            embed.add_field(name=f'Current negative prompt', value=f'``{cur_n_prompt}``', inline=True)

        # run function to update global variables
        if refresh:
            settings.global_var.model_info.clear()
            settings.global_var.sampler_names.clear()
            settings.global_var.facefix_models.clear()
            settings.global_var.style_names.clear()
            settings.global_var.embeddings_1.clear()
            settings.global_var.embeddings_2.clear()
            settings.global_var.hyper_names.clear()
            settings.global_var.lora_names.clear()
            settings.global_var.upscaler_names.clear()
            settings.populate_global_vars()
            embed.add_field(name=f'Refreshed!', value=f'Updated global lists', inline=False)

        # run through each command and update the defaults user selects
        if n_prompt is not None:
            new_n_prompt = f'{n_prompt}'
            if n_prompt == 'reset':
                n_prompt = ''
                new_n_prompt = ' '
            elif len(new_n_prompt) > 1024:
                new_n_prompt = f'{new_n_prompt[:1010]}....'
            settings.update(channel, 'negative_prompt', n_prompt)

        if data_model is not None:
            settings.update(channel, 'data_model', data_model)
            new += f'\nData model: ``"{data_model}"``'
            set_new = True

        if max_steps != 1:
            settings.update(channel, 'max_steps', max_steps)
            new += f'\nMax steps: ``{max_steps}``'
            # automatically lower default steps if max steps goes below it
            if max_steps < reviewer['steps']:
                settings.update(channel, 'steps', max_steps)
                new += f'\nDefault steps is too high! Lowering to ``{max_steps}``.'
            set_new = True

        if width is not None:
            settings.update(channel, 'width', width)
            new += f'\nWidth: ``"{width}"``'
            set_new = True

        if height is not None:
            settings.update(channel, 'height', height)
            new += f'\nHeight: ``"{height}"``'
            set_new = True

        if guidance_scale is not None:
            try:
                float(guidance_scale)
                settings.update(channel, 'guidance_scale', guidance_scale)
                new += f'\nGuidance Scale: ``{guidance_scale}``'
            except(Exception,):
                settings.update(channel, 'guidance_scale', '7.0')
                new += f'\nHad trouble setting Guidance Scale! Setting to default of `7.0`.'
            set_new = True

        if sampler is not None:
            settings.update(channel, 'sampler', sampler)
            new += f'\nSampler: ``"{sampler}"``'
            set_new = True

        if style is not None:
            settings.update(channel, 'style', style)
            new += f'\nStyle: ``"{style}"``'
            set_new = True

        if facefix is not None:
            settings.update(channel, 'facefix', facefix)
            new += f'\nFacefix: ``"{facefix}"``'
            set_new = True

        if highres_fix is not None:
            settings.update(channel, 'highres_fix', highres_fix)
            new += f'\nhighres_fix: ``"{highres_fix}"``'
            set_new = True

        if clip_skip is not None:
            settings.update(channel, 'clip_skip', clip_skip)
            new += f'\nCLIP skip: ``{clip_skip}``'
            set_new = True

        if hypernet is not None:
            settings.update(channel, 'hypernet', hypernet)
            new += f'\nHypernet: ``"{hypernet}"``'
            set_new = True

        if lora is not None:
            settings.update(channel, 'lora', lora)
            new += f'\nLoRA: ``"{lora}"``'
            set_new = True

        if strength is not None:
            settings.update(channel, 'strength', strength)
            new += f'\nStrength: ``"{strength}"``'
            set_new = True

        if upscaler_1 is not None:
            settings.update(channel, 'upscaler_1', upscaler_1)
            new += f'\nUpscaler 1: ``"{upscaler_1}"``'
            set_new = True

        if max_batch is not None:
            batch_check = settings.batch_format(reviewer['batch'])
            max_batch = settings.batch_format(max_batch)

            settings.update(channel, 'max_batch', f'{max_batch[0]},{max_batch[1]}')
            new += f'\nMax batch (count,size): ``{max_batch[0]},{max_batch[1]}``'
            # automatically lower default batch if max batch goes below it
            if max_batch[0] < batch_check[0]:
                settings.update(channel, 'batch', f'{max_batch[0]},{batch_check[1]}')
                new += f'\nDefault batch count is too high! Lowering to ``{max_batch[0]}``.'
            if max_batch[1] < batch_check[1]:
                if max_batch[0] < batch_check[0]:
                    settings.update(channel, 'batch', f'{max_batch[0]},{max_batch[1]}')
                else:
                    settings.update(channel, 'batch', f'{batch_check[0]},{max_batch[1]}')
                new += f'\nDefault batch size is too high! Lowering to ``{max_batch[1]}``.'
            set_new = True

        # review settings again in case user is trying to set steps/counts and max steps/counts simultaneously
        reviewer = settings.read(channel)
        if steps is not None:
            if steps > reviewer['max_steps']:
                new += f"\nMax steps is ``{reviewer['max_steps']}``! You can't go beyond it!"
            else:
                settings.update(channel, 'steps', steps)
                new += f'\nSteps: ``{steps}``'
            set_new = True

        if batch is not None:
            batch = settings.batch_format(batch)
            max_batch_check = settings.batch_format(reviewer['max_batch'])

            if batch[0] > max_batch_check[0]:
                new += f"\nMax batch count is ``{max_batch_check[0]}``! You can't go beyond it!"
            elif batch[1] > max_batch_check[1]:
                new += f"\nMax batch size is ``{max_batch_check[1]}``! You can't go beyond it!"
            else:
                settings.update(channel, 'batch', f'{batch[0]},{batch[1]}')
                new += f'\nbatch (count,size): ``{batch[0]},{batch[1]}``'
            set_new = True

        if set_new:
            embed.add_field(name=f'New defaults', value=new, inline=False)
        if new_n_prompt:
            embed.add_field(name=f'New default negative prompt', value=f'``{new_n_prompt}``', inline=False)

        await ctx.send_response(embed=embed, ephemeral=True)


def setup(bot):
    bot.add_cog(SettingsCog(bot))
