import discord
from discord.ext import commands
from discord import Option
from core import settings

class SettingsCog(commands.Cog):
    def __init__(self, bot:commands.Bot):
        self.bot = bot
    
    @commands.slash_command(name = "currentoptions")
    async def currentoptions(self, ctx):
        guild = '% s' % ctx.guild_id
        try:
            await ctx.respond(settings.read(guild)) #output is ugly
        except FileNotFoundError:
            settings.build(guild)
            await ctx.respond('Config file not found, building...')

    @commands.slash_command(name = "changesettings", description = 'Change Server Defaults for /draw')
    async def setdefaultsettings(
        self,
        ctx,
        setsteps: Option(int, "Set Steps", min_value= 1, default=1),
        setnprompt: Option(str, "Set Negative Prompt", default='unset'),
        setmaxsteps: Option(int, "Set Max Steps", min_value= 1, default=1),
        setsampler: Option(str, "Set Sampler", default='unset')
    ):
        guild_id = '% s' % ctx.guild_id
        maxsteps = settings.read(guild_id)
        if setsteps > maxsteps['max_steps']:
            await ctx.respond('default steps cant go beyond max steps')
            await ctx.send_message('CURRENT MAXSTEPS:'+str(maxsteps['max_steps']))
        elif setsteps != 1:
            try:
                settings.update(guild_id, 'default_steps', setsteps)
                await ctx.respond('New default steps value Set')
            except FileNotFoundError:
                settings.build(guild_id)
                await ctx.respond('Config file not found, building...')
        if setnprompt != 'unset':
            try:
                settings.update(guild_id, 'negative_prompt', setnprompt)
                await ctx.respond('New default negative prompts Set')
            except FileNotFoundError:
                settings.build(guild_id)
                await ctx.respond('Config file not found, building...')
        if setmaxsteps != 1:
            try:
                settings.update(guild_id, 'max_steps', setmaxsteps)
                await ctx.respond('New max steps value Set')
            except FileNotFoundError:
                settings.build(guild_id)
                await ctx.respond('Config file not found, building...')
        if setsampler != 'unset':
            #Disclaimer: I know there's a more sophisticated way to do this but pycord hates me so I'm not risking it right now
            samplers = {'Euler a', 'Euler', 'LMS', 'Heun', 'DPM2', 'DPM2 a', 'DPM fast', 'DPM adaptive', 'LMS Karras', 'DPM2 Karras', 'DPM2 a Karras', 'DDIM', 'PLMS'}
            if samplers in samplers:
                try:
                    settings.update(guild_id, 'sampler', setsampler)
                    await ctx.respond('New default sampler Set')
                except FileNotFoundError:
                    settings.build(guild_id)
                    await ctx.respond('Config file not found, building...')
            else:
                await ctx.respond('Please use one of the following options: ' + ' , '.join(samplers) )
        



    # @commands.slash_command(name = "setdefaultnegativeprompt")
    # async def setnegativeprompt(self, ctx, value: str):
    #     guild_id = '% s' % ctx.guild_id
    #     sett = 'negative_prompt'


    # @commands.slash_command(name = "setdefaultsampler")
    # async def defaultsampler(self, ctx, value:str):
    #     guild_id = '% s' % ctx.guild_id
    #     sett = 'sampler'


    # @commands.slash_command(name = "setmaxsteps")
    # async def setmaxsteps(self, ctx, setting):
    #     guild_id = '% s' % ctx.guild_id
    #     value = int(setting)
    #     sett= 'max_steps'
    #     maxsteps = settings.read(guild_id)



def setup(bot:commands.Bot):
    bot.add_cog(SettingsCog(bot))