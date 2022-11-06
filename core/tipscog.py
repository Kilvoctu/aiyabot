import discord
from discord.ext import commands
from discord.ui import View

from core import settings


class view(View):
    @discord.ui.button(label="View the styles list", style=discord.ButtonStyle.primary)
    async def button_callback(self, button, interaction):
        button.disabled = True
        style_list = ''
        for i, j in settings.global_var.style_names.items():
            style_list = style_list + str(i) + ' - ``' + str(j) + ' ``\n'
        embed2 = discord.Embed(title="Style list", description=style_list)
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("Here you go!", embed=embed2, ephemeral=True)

class TipsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.slash_command(name = "tips", description = "Some quick tips for generating images!")
    async def tips(self, ctx):

        embed=discord.Embed(title="Quick Tips", description="")
        embed.add_field(name="Steps", value="This is how many cycles the AI takes to create an image. More steps generally leads to better results, but not always!", inline=False)
        embed.add_field(name="Guidance Scale", value="This represents how much importance is given to your prompt. The AI will give more attention to your prompt with higher values and be more creative with lower values.", inline=False)
        embed.add_field(name="Seed", value="This value is the key used to generate an image. A seed can be used to recreate the same image or variations on it.", inline=False)
        embed.add_field(name="Prompting", value="Word order influences the image. Putting `cat, dog` will lean more towards cat.\nKeep in mind when doing very long prompts, the AI will be more likely to ignore words near the end of the prompt.", inline=False)
        embed.add_field(name="Emphasizing", value="`(word)`-each `()` increases attention to `word` by 1.1x\n`[word]`-each `[]` decreases attention to `word` by 1.1x\n`(word:1.5)`-increases attention to `word` by 1.5x\n`(word:0.25)`-decreases attention to `word` by 4x\n`\(word\)`-use literal () characters in prompt.", inline=False)
        embed.add_field(name="Transitioning", value="`[word1:word2:steps]`\nWhen generating an image, the AI will start at `word1`, then after the specified number of `steps`, switches to `word2`. Word order matters.", inline=False)
        embed.add_field(name="Alternating", value="`[word1|word2]`\nWhen generating an image, the AI will alternate between the words for each step. Word order still applies.", inline=True)
        embed.set_footer(text='Also, you can react with ❌ to delete your generated images.')

        await ctx.respond(embed=embed, view=view(), ephemeral=True)

def setup(bot):
    bot.add_cog(TipsCog(bot))
    
    