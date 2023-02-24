import discord
import math
import os
from discord.ext import commands
from discord.ui import View

from core import settings


class InfoView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.page = 0
        self.contents = []

    def disable_nav_buttons(self):
        button_back = [x for x in self.children if x.custom_id == 'button_back'][0]
        button_back.disabled = True
        button_forward = [x for x in self.children if x.custom_id == 'button_forward'][0]
        button_forward.disabled = True

    def enable_nav_buttons(self):
        button_back = [x for x in self.children if x.custom_id == 'button_back'][0]
        button_back.disabled = False
        button_forward = [x for x in self.children if x.custom_id == 'button_forward'][0]
        button_forward.disabled = False

    @discord.ui.button(
        custom_id="button_model",
        label="Models", row=0)
    async def button_model(self, _button, interaction):
        # initialize settings for each button
        length = len(settings.global_var.model_info)
        batch = 10
        self.page = 0
        self.contents = []

        # enable navigation buttons only when needed
        if length > batch:
            self.enable_nav_buttons()
        else:
            self.disable_nav_buttons()

        # create a subscript-able object for use later
        models = []
        for key in settings.global_var.model_info:
            models.append(key)

        # create each page and place into "contents" list
        for i in range(0, length, batch):
            model_list = ''
            embed_page = discord.Embed(title="Models list", colour=settings.global_var.embed_color)
            for key in models[i:i + batch]:
                for keyB, value in settings.global_var.model_info.items():
                    if key == keyB:
                        # strip any folders from model full name
                        filename = value[0].split(os.sep)[-1]
                        model_list += f'\n**{keyB}**\n``{filename}``'
                        break
            embed_page.add_field(name="", value=model_list, inline=True)
            if length > batch:
                embed_page.set_footer(text=f'Page {self.page + 1} of {math.ceil(length / batch)} - {length} total')
            self.contents.append(embed_page)
            self.page += 1
        self.page = 0

        await interaction.response.edit_message(view=self, embed=self.contents[0])

    @discord.ui.button(
        custom_id="button_styles",
        label="Styles", row=0)
    async def button_style(self, _button, interaction):
        length = len(settings.global_var.style_names)
        batch = 8
        self.page = 0
        self.contents = []
        desc = 'The **style names** are bundled with ``words`` for faster prompting.'

        if length > batch:
            self.enable_nav_buttons()
        else:
            self.disable_nav_buttons()

        styles = []
        for key in settings.global_var.style_names:
            styles.append(key)

        for i in range(0, length, batch):
            embed_page = discord.Embed(title="Styles list", description=desc, colour=settings.global_var.embed_color)
            for key in styles[i:i + batch]:
                for keyB, value in settings.global_var.style_names.items():
                    if key == keyB:
                        if value == '':
                            value = ' '
                        elif len(value) > 1024:
                            value = f'{value[:1000]}....'
                        embed_page.add_field(name=f"**{key}**", value=f"``{value}``", inline=False)
                        break
            if length > batch:
                embed_page.set_footer(text=f'Page {self.page + 1} of {math.ceil(length / batch)} - {length} total')
            self.contents.append(embed_page)
            self.page += 1
        self.page = 0

        await interaction.response.edit_message(view=self, embed=self.contents[0])

    @discord.ui.button(
        custom_id="button_hyper",
        label="Hypernets", row=0)
    async def button_hyper(self, _button, interaction):
        length = len(settings.global_var.hyper_names)
        batch = 16
        self.page = 0
        self.contents = []
        desc = 'To add manually to prompt, use <hypernet:``name``:``#``>\n``#`` = The effect strength (0.0 - 1.0)'

        if length > batch * 2:
            self.enable_nav_buttons()
        else:
            self.disable_nav_buttons()

        for i in range(0, length, batch * 2):
            hyper_column_a, hyper_column_b = '', ''
            embed_page = discord.Embed(title="Hypernets list", description=desc, colour=settings.global_var.embed_color)
            for value in settings.global_var.hyper_names[i:i + batch]:
                hyper_column_a += f'\n``{value}``'
            embed_page.add_field(name="", value=hyper_column_a, inline=True)
            i += batch
            for value in settings.global_var.hyper_names[i:i + batch]:
                hyper_column_b += f'\n``{value}``'
            embed_page.add_field(name="", value=hyper_column_b, inline=True)
            if length > batch * 2:
                embed_page.set_footer(text=f'Page {self.page + 1} of {math.ceil(length / (batch * 2))} - {length} total')
            self.contents.append(embed_page)
            self.page += 1
        self.page = 0

        await interaction.response.edit_message(view=self, embed=self.contents[0])

    @discord.ui.button(
        custom_id="button_lora",
        label="LoRAs", row=0)
    async def button_lora(self, _button, interaction):
        length = len(settings.global_var.lora_names)
        batch = 16
        self.page = 0
        self.contents = []
        desc = 'To add manually to prompt, use <lora:``name``:``#``>\n``#`` = The effect strength (0.0 - 1.0)'

        if length > batch * 2:
            self.enable_nav_buttons()
        else:
            self.disable_nav_buttons()

        for i in range(0, length, batch * 2):
            lora_column_a, lora_column_b = '', ''
            embed_page = discord.Embed(title="LoRA list", description=desc, colour=settings.global_var.embed_color)
            for value in settings.global_var.lora_names[i:i+batch]:
                lora_column_a += f'\n``{value}``'
            embed_page.add_field(name="", value=lora_column_a, inline=True)
            i += batch
            for value in settings.global_var.lora_names[i:i+batch]:
                lora_column_b += f'\n``{value}``'
            embed_page.add_field(name="", value=lora_column_b, inline=True)
            if length > batch*2:
                embed_page.set_footer(text=f'Page {self.page + 1} of {math.ceil(length / (batch * 2))} - {length} total')
            self.contents.append(embed_page)
            self.page += 1
        self.page = 0

        await interaction.response.edit_message(view=self, embed=self.contents[0])

    @discord.ui.button(
        custom_id="button_embed",
        label="TIs", row=0)
    async def button_embed(self, _button, interaction):
        sd1_length = len(settings.global_var.embeddings_1)
        sd2_length = len(settings.global_var.embeddings_2)
        total_length = sd1_length + sd2_length
        batch = 16
        self.page = 0
        self.contents = []
        total_pages = math.ceil(sd1_length / (batch * 2)) + math.ceil(sd2_length / (batch * 2))
        desc = 'To use, simply add the name to your prompt.'

        if total_length > batch * 2:
            self.enable_nav_buttons()
        else:
            self.disable_nav_buttons()

        for i in range(0, sd1_length, batch * 2):
            embed_column_a, embed_column_b = '', ''
            embed_page = discord.Embed(title="Textual Inversion embeddings list",
                                       description=f"{desc}\nThese embeddings are for **SD 1.X** models.",
                                       colour=settings.global_var.embed_color)
            for value in settings.global_var.embeddings_1[i:i + batch]:
                embed_column_a += f'\n``{value}``'
            embed_page.add_field(name='', value=embed_column_a, inline=True)
            i += batch
            for value in settings.global_var.embeddings_1[i:i + batch]:
                embed_column_b += f'\n``{value}``'
            embed_page.add_field(name='', value=embed_column_b, inline=True)
            if total_length > batch * 2:
                embed_page.set_footer(text=f'Page {self.page + 1} of {total_pages} - {total_length} total')
            self.contents.append(embed_page)
            self.page += 1

        for i in range(0, sd2_length, batch * 2):
            embed_column_a, embed_column_b = '', ''
            embed_page = discord.Embed(title="Textual Inversion embeddings list",
                                       description=f"{desc}\nThese embeddings are for **SD 2.X** models.",
                                       colour=settings.global_var.embed_color)
            for value in settings.global_var.embeddings_2[i:i + batch]:
                embed_column_a += f'\n``{value}``'
            embed_page.add_field(name='', value=embed_column_a, inline=True)
            i += batch
            for value in settings.global_var.embeddings_2[i:i + batch]:
                embed_column_b += f'\n``{value}``'
            embed_page.add_field(name='', value=embed_column_b, inline=True)
            if total_length > batch * 2:
                embed_page.set_footer(text=f'Page {self.page + 1} of {total_pages} - {total_length} total')
            self.contents.append(embed_page)
            self.page += 1

        self.page = 0

        await interaction.response.edit_message(view=self, embed=self.contents[0])

    @discord.ui.button(
        custom_id="button_tips",
        label="Documentation", row=1)
    async def button_tips(self, _button, interaction):
        self.enable_nav_buttons()
        self.page = 0

        embed_tips1 = discord.Embed(title="Documentation", description="Welcome to the documentation! Basic usage and prompting tips is explained here.",
                                    colour=settings.global_var.embed_color)
        embed_tips1.add_field(name="/draw command", value="Simply fill in the prompt and hit send!"
                                                          "\nThere are many additional options, but they are automatically set filled with presets. They aren't required unless you want to tweak your prompts.")
        embed_tips1.add_field(name="image-to-image", value="Use the /draw command for this, **init_img** option for an attachment or **init_url** for a link."
                                                           "\nNote that **strength** interacts with img2img. The range is 0.0 to 1.0, with higher values having more effect on the image.")
        embed_tips1.add_field(name="\u200B", value="\u200B")
        embed_tips1.add_field(name="/identify command", value="This command makes a caption for your image. A standard caption is generated with normal **phrasing**, or tags can be used to generate a list of keywords.")
        embed_tips1.add_field(name="/upscale command", value="A simple command to upscale your image! You can upscale up to 4x at a time.")
        embed_tips1.add_field(name="\u200B", value="\u200B")

        embed_tips2 = discord.Embed(title="Basic Prompting Tips", colour=settings.global_var.embed_color)
        embed_tips2.add_field(name="Prompting",
                              value="Word order influences the image. Putting `cat, dog` will lean more towards cat."
                                   "\nKeep this in mind when doing very long prompts.",)
        embed_tips2.add_field(name="Steps",
                              value="This is how many cycles the AI takes to create an image. More steps generally leads to better results, but not always!",)
        embed_tips2.add_field(name="\u200B", value="\u200B")
        embed_tips2.add_field(name="Guidance Scale",
                              value="This represents how much importance is given to your prompt. The AI will give more attention to your prompt with higher values and be more creative with lower values.",)
        embed_tips2.add_field(name="Seed",
                              value="This value is the key used to generate an image. A seed can be used to recreate the same image or variations on it.",)
        embed_tips2.add_field(name="\u200B", value="\u200B")

        embed_tips3 = discord.Embed(title="Basic Prompting Tips", description="This is some of the syntax that can be used with your prompts.",
                                    colour=settings.global_var.embed_color)
        embed_tips3.add_field(name="Emphasizing",
                              value="`(word)`-each `()` increases attention to `word` by 1.1x"
                                   "\n`[word]`-each `[]` decreases attention to `word` by 1.1x"
                                   "\n`(word:1.5)`-increases attention to `word` by 1.5x"
                                   "\n`(word:0.25)`-decreases attention to `word` by 4x"
                                   "\n`\\(word\\)`-use literal () characters in prompt.",
                              inline=False)
        embed_tips3.add_field(name="Transitioning",
                              value="`[word1:word2:steps]`"
                                   "\nWhen generating an image, the AI will start at `word1`, then after the specified number of `steps`, switches to `word2`. Word order matters.",
                              inline=False)
        embed_tips3.add_field(name="Alternating",
                              value="`[word1|word2]`"
                                   "\nWhen generating an image, the AI will alternate between the words for each step. Word order still applies.",
                              inline=False)

        embed_tips4 = discord.Embed(title="Buttons", description="Generated images contain some neat, convenient buttons!",
                                    colour=settings.global_var.embed_color)
        embed_tips4.add_field(name="🖋️",
                              value="This button opens a popup allowing you to adjust several options of your output, then will generate a new one based on the changes.")
        embed_tips4.add_field(name="🎲",
                              value="Use this when you simply want to create a new image with the same options.")
        embed_tips4.add_field(name="\u200B", value="\u200B")
        embed_tips4.add_field(name="📋",
                              value="The clipboard provides the information used to make the image, and even provides the command for copying!")
        embed_tips4.add_field(name="❌",
                              value="The button used to delete any unwanted outputs. If this button isn't working, you can add a ❌ reaction instead.")
        embed_tips4.add_field(name="\u200B", value="\u200B")
        # For those who fork AIYA, feel free to edit or add to this per your needs,
        # but please don't just delete me from credits and claim my work as yours.
        url = 'https://github.com/Kilvoctu/aiyabot'
        thumb = 'https://raw.githubusercontent.com/Kilvoctu/kilvoctu.github.io/master/pics/previewthumb.png'
        wiki = 'https://github.com/Kilvoctu/aiyabot/wiki#using-aiya'
        embed_tips5 = discord.Embed(title="Extra Information",
                                    description=f"For more detailed documentation, check out the [wiki]({wiki}) in my [home]({url})!\n\n"
                                                f"Also, feel free to report bugs or leave feedback! I'm open-source Python Discord bot AIYA, developed by *Kilvoctu#1238*, maintained with care."
                                                f"\n\nPlease enjoy making AI art with me~!",
                                    colour=settings.global_var.embed_color)
        embed_tips5.set_thumbnail(url=thumb)
        embed_tips5.set_footer(text='Have a lovely day!', icon_url=thumb)

        self.page = 0
        self.contents = [
            embed_tips1,
            embed_tips2,
            embed_tips3,
            embed_tips4,
            embed_tips5
        ]

        await interaction.response.edit_message(view=self, embed=self.contents[0])

    @discord.ui.button(
        custom_id="button_back", label="◀️", row=1, disabled=True)
    async def button_back(self, _button, interaction):
        try:
            self.page -= 1
            await interaction.response.edit_message(view=self, embed=self.contents[self.page])
        except(Exception,):
            self.page = len(self.contents)-1
            await interaction.response.edit_message(view=self, embed=self.contents[self.page])

    @discord.ui.button(
        custom_id="button_forward", label="▶️", row=1, disabled=True)
    async def button_forward(self, _button, interaction):
        try:
            self.page += 1
            await interaction.response.edit_message(view=self, embed=self.contents[self.page])
        except(Exception,):
            self.page = 0
            await interaction.response.edit_message(view=self, embed=self.contents[self.page])


class InfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(InfoView())

    @commands.slash_command(name="info", description="Lots of useful information!")
    async def info(self, ctx):
        first_embed = discord.Embed(title='Select a button!',
                                    description='You can check lists of any extra content I have loaded!'
                                                '\nAlso check documentation for usage information!',
                                    colour=settings.global_var.embed_color)
        first_embed.set_footer(text='Use ◀️ and ▶️ to change pages when available')

        await ctx.respond(embed=first_embed, view=InfoView(), ephemeral=True)


def setup(bot):
    bot.add_cog(InfoCog(bot))
