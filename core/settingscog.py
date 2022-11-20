import discord
from discord import option
from discord.ext import commands
from typing import Optional

from core import settings


class SettingsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # pulls from model_names list and makes some sort of dynamic list to bypass Discord 25 choices limit
    def model_autocomplete(self: discord.AutocompleteContext):
        return [
            model for model in settings.global_var.model_names
        ]

    @commands.slash_command(name='settings', description='Review and change server defaults')
    @option(
        'current_settings',
        bool,
        description='Show the current defaults for the server.',
        required=False,
    )
    @option(
        'set_n_prompt',
        str,
        description='Set default negative prompt for the server',
        required=False,
    )
    @option(
        'set_model',
        str,
        description='Set default data model for image generation',
        required=False,
        autocomplete=discord.utils.basic_autocomplete(model_autocomplete),
    )
    @option(
        'set_steps',
        int,
        description='Set default amount of steps for the server',
        min_value=1,
        required=False,
    )
    @option(
        'set_max_steps',
        int,
        description='Set default maximum steps for the server',
        min_value=1,
        required=False,
    )
    @option(
        'set_sampler',
        str,
        description='Set default sampler for the server',
        required=False,
        choices=settings.global_var.sampler_names,
    )
    @option(
        'set_count',
        int,
        description='Set default count for the server',
        min_value=1,
        required=False,
    )
    @option(
        'set_max_count',
        int,
        description='Set default maximum count for the server',
        min_value=1,
        required=False,
    )
    @option(
        'set_clip_skip',
        int,
        description='Set default CLIP skip for the server',
        required=False,
        choices=[x for x in range(1, 13, 1)]
    )
    async def settings_handler(self, ctx,
                               current_settings: Optional[bool] = True,
                               set_n_prompt: Optional[str] = 'unset',
                               set_model: Optional[str] = None,
                               set_steps: Optional[int] = 1,
                               set_max_steps: Optional[int] = 1,
                               set_sampler: Optional[str] = 'unset',
                               set_count: Optional[int] = None,
                               set_max_count: Optional[int] = None,
                               set_clip_skip: Optional[int] = 0):
        guild = '% s' % ctx.guild_id
        reviewer = settings.read(guild)
        # create the embed for the reply
        embed = discord.Embed(title="Summary", description="")
        embed.colour = settings.global_var.embed_color
        current = ''
        new = ''
        set_new = False

        if current_settings:
            cur_set = settings.read(guild)
            for key, value in cur_set.items():
                if value == '':
                    value = ' '
                current = current + f'\n{key} - ``{value}``'
            embed.add_field(name=f'Current defaults', value=current, inline=False)

        # run through each command and update the defaults user selects
        if set_n_prompt != 'unset':
            settings.update(guild, 'negative_prompt', set_n_prompt)
            new = new + f'\nNegative prompts: ``"{set_n_prompt}"``'
            set_new = True

        if set_model is not None:
            settings.update(guild, 'data_model', set_model)
            new = new + f'\nData model: ``"{set_model}"``'
            set_new = True

        if set_max_steps != 1:
            settings.update(guild, 'max_steps', set_max_steps)
            new = new + f'\nMax steps: ``{set_max_steps}``'
            # automatically lower default steps if max steps goes below it
            if set_max_steps < reviewer['default_steps']:
                settings.update(guild, 'default_steps', set_max_steps)
                new = new + f'\nDefault steps is too high! Lowering to ``{set_max_steps}``.'
            set_new = True

        if set_sampler != 'unset':
            settings.update(guild, 'sampler', set_sampler)
            new = new + f'\nSampler: ``"{set_sampler}"``'
            set_new = True

        if set_max_count is not None:
            settings.update(guild, 'max_count', set_max_count)
            new = new + f'\nMax count: ``{set_max_count}``'
            # automatically lower default count if max count goes below it
            if set_max_count < reviewer['default_count']:
                settings.update(guild, 'default_count', set_max_count)
                new = new + f'\nDefault count is too high! Lowering to ``{set_max_count}``.'
            set_new = True

        if set_clip_skip != 0:
            settings.update(guild, 'clip_skip', set_clip_skip)
            new = new + f'\nCLIP skip: ``{set_clip_skip}``'
            set_new = True

        # review settings again in case user is trying to set steps/counts and max steps/counts simultaneously
        reviewer = settings.read(guild)
        if set_steps != 1:
            if set_steps > reviewer['max_steps']:
                new = new + f"\nMax steps is ``{reviewer['max_steps']}``! You can't go beyond it!"
            else:
                settings.update(guild, 'default_steps', set_steps)
                new = new + f'\nSteps: ``{set_steps}``'
            set_new = True

        if set_count is not None:
            if set_count > reviewer['max_count']:
                new = new + f"\nMax count is ``{reviewer['max_count']}``! You can't go beyond it!"
            else:
                settings.update(guild, 'default_count', set_count)
                new = new + f'\nCount: ``{set_count}``'
            set_new = True

        if set_new:
            embed.add_field(name=f'New defaults', value=new, inline=False)

        await ctx.send_response(embed=embed)


def setup(bot):
    bot.add_cog(SettingsCog(bot))
