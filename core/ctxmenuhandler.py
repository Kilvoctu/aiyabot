import base64
import discord
import requests

from core import settings


async def account_creation_date(ctx, member: discord.Member):  # user commands return the member
    await ctx.respond(f"{member.name}'s account was created on {member.created_at}")


async def get_message_id(ctx, message: discord.Message):  # message commands return the message
    await ctx.respond(f"Message ID: `{message.id}`")


async def get_image_info(ctx, message: discord.Message):
    image_url = ''
    for i in message.attachments:
        image_url = i

    # construct a payload
    image = base64.b64encode(requests.get(image_url, stream=True).content).decode('utf-8')
    payload = {
        "image": 'data:image/png;base64,' + image
    }
    # send normal payload to webui
    s = settings.authenticate_user()

    png_response = s.post(url=f'{settings.global_var.url}/sdapi/v1/png-info', json=payload)
    png_data = png_response.json().get("info")
    png_data_list = png_data.split("\n")
    negative_prompt = str(png_data_list[1]).split("Negative prompt: ", 1)[1]

    print(f"this is the remaining params: {png_data_list[2]}")

    # give best effort in trying to parse the png info
    embed = discord.Embed(title="About the image!", description="")
    prompt_field = png_data_list[0]
    if len(prompt_field) > 1024:
        prompt_field = f'{prompt_field[:1010]}....'
    embed.colour = settings.global_var.embed_color
    embed.add_field(name=f'Prompt', value=f'``{prompt_field}``', inline=False)
    # embed.add_field(name='Data model', value=f'Display name - ``{display_name}``\nModel name - ``{model_name}``'
    #                                         f'\nShorthash - ``{model_hash}``{activator_token}', inline=False)

    #copy_command = f'/draw prompt:{rev[1]} data_model:{display_name} steps:{rev[5]} width:{rev[6]} ' \
    #               f'height:{rev[7]} guidance_scale:{rev[8]} sampler:{rev[9]} seed:{rev[10]}'

    if negative_prompt != '':
        #copy_command += f' negative_prompt:{clean_negative}'
        n_prompt_field = negative_prompt
        if len(n_prompt_field) > 1024:
            n_prompt_field = f'{n_prompt_field[:1010]}....'
        embed.add_field(name=f'Negative prompt', value=f'``{n_prompt_field}``', inline=False)

    #extra_params = f'Sampling steps: ``{rev[5]}``\nSize: ``{rev[6]}x{rev[7]}``\nClassifier-free guidance ' \
    #               f'scale: ``{rev[8]}``\nSampling method: ``{rev[9]}``\nSeed: ``{rev[10]}``'
    
    #embed.add_field(name=f'Other parameters', value=extra_params, inline=False)
    embed.add_field(name=f'Command for copying', value=f'', inline=False)
    #embed.set_footer(text=copy_command)

    '''if len(copy_command) > 2048:
        button.disabled = True
        await interaction.response.edit_message(view=self)
        await interaction.followup.send(
            "The contents of 📋 exceeded Discord's character limit! Sorry, I can't display it...", ephemeral=True)'''

    await ctx.respond(embed=embed, ephemeral=True)
