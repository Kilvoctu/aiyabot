import discord
from discord.ext import commands
from discord.ui import View

from core import settings


class TipsView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        custom_id="button_tips",
        label="Quick tips")
    async def button_tips(self, button, interaction):

        embed_tips = discord.Embed(title="Quick Tips", description="")
        embed_tips.colour = settings.global_var.embed_color
        embed_tips.add_field(name="Steps",
                             value="This is how many cycles the AI takes to create an image. "
                                   "More steps generally leads to better results, but not always!",
                             inline=False)
        embed_tips.add_field(name="Guidance Scale",
                             value="This represents how much importance is given to your prompt. The AI will give more "
                                   "attention to your prompt with higher values and be more creative with lower values.",
                             inline=False)
        embed_tips.add_field(name="Seed",
                             value="This value is the key used to generate an image. "
                                   "A seed can be used to recreate the same image or variations on it.",
                             inline=False)
        embed_tips.add_field(name="Prompting",
                             value="Word order influences the image. Putting `cat, dog` will lean more towards cat.\nKeep "
                                   "in mind when doing very long prompts, the AI will be more likely to ignore words near "
                                   "the end of the prompt.",
                             inline=False)
        embed_tips.add_field(name="Emphasizing",
                             value="`(word)`-each `()` increases attention to `word` by 1.1x\n`[word]`-each `[]` decreases "
                                   "attention to `word` by 1.1x\n`(word:1.5)`-increases attention to `word` by 1.5x\n`("
                                   "word:0.25)`-decreases attention to `word` by 4x\n`\(word\)`-use literal () characters "
                                   "in prompt.",
                             inline=False)
        embed_tips.add_field(name="Transitioning",
                             value="`[word1:word2:steps]`\nWhen generating an image, the AI will start at `word1`, "
                                   "then after the specified number of `steps`, switches to `word2`. Word order matters.",
                             inline=False)
        embed_tips.add_field(name="Alternating",
                             value="`[word1|word2]`\nWhen generating an image, the AI will alternate between the words for "
                                   "each step. Word order still applies.",
                             inline=True)
        embed_tips.set_footer(text='Also, you can react with ❌ to delete your generated images.')

        await interaction.response.edit_message(embed=embed_tips)

    @discord.ui.button(
        custom_id="button_model",
        label="Models list")
    async def button_model(self, button, interaction):

        model_list = ''
        for model in settings.global_var.model_info.items():
            # strip any folders from model full name
            filename = model[1][0].split('/', 1)[-1].split('\\', 1)[-1]
            model_list += f'\n{model[0]} - ``{filename}``'
        embed_model = discord.Embed(title="Models list", description=model_list)
        embed_model.colour = settings.global_var.embed_color

        await interaction.response.edit_message(embed=embed_model)

    @discord.ui.button(
        custom_id="button_styles",
        label="Styles list")
    async def button_style(self, button, interaction):

        style_list = ''
        for key, value in settings.global_var.style_names.items():
            if value == '':
                value = ' '
            style_list += f'\n{key} - ``{value}``'
        embed_styles = discord.Embed(title="Styles list", description=style_list)
        embed_styles.colour = settings.global_var.embed_color

        await interaction.response.edit_message(embed=embed_styles)

    @discord.ui.button(
        custom_id="button_hyper",
        label="Hypernets list")
    async def button_hyper(self, button, interaction):

        hyper_list = ''
        for value in settings.global_var.hyper_names:
            if value == '':
                value = ' '
            hyper_list += f'\n``{value}``'
        embed_hyper = discord.Embed(title="Hypernets list", description=hyper_list)
        embed_hyper.colour = settings.global_var.embed_color

        await interaction.response.edit_message(embed=embed_hyper)

    @discord.ui.button(
        custom_id="button_lora",
        label="LoRA list")
    async def button_lora(self, button, interaction):

        lora_list = ''
        for value in settings.global_var.lora_names:
            if value == '':
                value = ' '
            lora_list += f'\n``{value}``'
        embed_lora = discord.Embed(title="LoRA list", description=lora_list)
        embed_lora.colour = settings.global_var.embed_color

        await interaction.response.edit_message(embed=embed_lora)

    @discord.ui.button(
        custom_id="button_embed",
        label="Embeddings list")
    async def button_embed(self, button, interaction):

        embed_1_list, embed_2_list = '', ''
        for value in settings.global_var.embeddings_1:
            if value == '':
                value = ' '
            embed_1_list += f'\n``{value}``'
        for value in settings.global_var.embeddings_2:
            if value == '':
                value = ' '
            embed_2_list += f'\n``{value}``'
        embed_embed = discord.Embed(title="Embeddings list")
        embed_embed.colour = settings.global_var.embed_color

        embed_embed.add_field(name="SD 1.X embeddings", value=embed_1_list, inline=True)
        embed_embed.add_field(name="SD 2.X embeddings", value=embed_2_list, inline=True)

        await interaction.response.edit_message(embed=embed_embed)

    @discord.ui.button(
        custom_id="button_about",
        label="About me")
    async def button_about(self, button, interaction):

        url = 'https://github.com/Kilvoctu/aiyabot'
        url2 = 'https://raw.githubusercontent.com/Kilvoctu/kilvoctu.github.io/master/pics/previewthumb.png'
        url3 = 'https://github.com/Kilvoctu/aiyabot/wiki#using-aiya'
        embed_about = discord.Embed(title="About me",
                                    description=f"Hi! I'm open-source Discord bot AIYA, written in Python.\n"
                                                f"[My home is here]({url}) if you'd like to check it out, "
                                                f"and the [wiki]({url3}) has some basic info on usage!\n\n"
                                                f"Feel free to report bugs or leave feedback!")
        embed_about.colour = settings.global_var.embed_color
        embed_about.set_thumbnail(url=url2)
        embed_about.set_footer(text='Have a lovely day!', icon_url=url2)

        await interaction.response.edit_message(embed=embed_about)


class TipsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TipsView())

    @commands.slash_command(name="tips", description="Lots of useful information!")
    async def tips(self, ctx):
        first_embed = discord.Embed(title='Select a button!')
        first_embed.colour = settings.global_var.embed_color

        await ctx.respond(embed=first_embed, view=TipsView(), ephemeral=True)


def setup(bot):
    bot.add_cog(TipsCog(bot))
