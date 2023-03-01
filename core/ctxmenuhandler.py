import base64
import discord
import requests

from core import settings


# functions to look for styles in the prompts
def prompt_search(search, field):
    search_list = search.split('{prompt}')
    matches = 0
    for y in search_list:
        if y in field:
            matches += 1
    if matches == len(search_list):
        return True


def prompt_remove(search, field):
    search_list = search.split('{prompt}')
    for y in search_list:
        if y in field:
            field = field.replace(y, '').strip()
    return field.strip(',')


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

    # grab prompt and negative prompt
    prompt_field = png_data_list[0]
    negative_prompt = str(png_data_list[1]).split("Negative prompt: ", 1)[1]

    # initialize model info
    display_name, model_name, model_hash = 'Unknown', 'Unknown', 'Unknown'
    activator_token = ''

    # initialize extra params
    steps, size, guidance_scale, sampler, seed = '', '', '', '', ''
    style = 'None'
    facefix = ''
    highres_fix = ''
    clip_skip = ''
    hypernet = ''
    lora = ''
    strength = ''

    print(f"this is the remaining params: {png_data_list[2]}")

    # try to find the style used and remove from prompts
    for key, value in settings.global_var.style_names.items():
        try:
            style_prompt = list(value)
            if prompt_search(style_prompt[0], prompt_field) and prompt_search(style_prompt[1], negative_prompt):
                style = [key, value]
                break
        except(Exception,):
            pass
    # if style is not none then remove its tokens from prompts
    if style[0] != 'None':
        prompt_field = prompt_remove(style[1][0], prompt_field)
        negative_prompt = prompt_remove(style[1][1], negative_prompt)

    extra_params_split = png_data_list[2].split(", ")
    for line in extra_params_split:
        # grab model info
        if 'Model hash: ' in line:
            model_hash = line.split(': ', 1)[1]
        if 'Model: ' in line:
            model_name = line.split(': ', 1)[1]

        # grab guaranteed extra params
        if 'Steps: ' in line:
            steps = line.split(': ', 1)[1]
        if 'Size: ' in line:
            size = line.split(': ', 1)[1]
        if 'CFG scale: ' in line:
            guidance_scale = line.split(': ', 1)[1]
        if 'Sampler: ' in line:
            sampler = line.split(': ', 1)[1]
        if 'Seed: ' in line:
            seed = line.split(': ', 1)[1]

    width_height = size.split("x")

    # try to find the model name and activator token
    for model in settings.global_var.model_info.items():
        if model[1][2] == model_hash or model[1][1] == model_name:
            display_name = model[0]
            if model[1][3]:
                activator_token = f"\nActivator token - ``{model[1][3]}``"

            if model[1][3] in prompt_field:
                prompt_field = prompt_field.replace(f"{model[1][3]} ", "")
    # strip any folders from model name
    model_name = model_name.split('_', 1)[-1]

    # run prompts through mod function
    mod_results = settings.prompt_mod(prompt_field, negative_prompt)
    if mod_results[0] == "Mod":
        prompt_field = mod_results[1]
        negative_prompt = mod_results[3]

    # give the best effort in trying to parse the png info
    embed = discord.Embed(title="About the image!", description="")
    if len(prompt_field) > 1024:
        prompt_field = f'{prompt_field[:1010]}....'
    embed.colour = settings.global_var.embed_color
    embed.add_field(name=f'Prompt', value=f'``{prompt_field}``', inline=False)
    embed.add_field(name='Data model', value=f'Display name - ``{display_name}``\nModel name - ``{model_name}``'
                                             f'\nShorthash - ``{model_hash}``{activator_token}', inline=False)

    copy_command = f'/draw prompt:{prompt_field} steps:{steps} width:{width_height[0]} height:{width_height[1]} ' \
                   f'guidance_scale:{guidance_scale} sampler:{sampler} seed:{seed}'
    if display_name != 'Unknown':
        copy_command += f' data_model: {display_name}'

    if negative_prompt != '':
        # copy_command += f' negative_prompt:{clean_negative}'
        n_prompt_field = negative_prompt
        if len(n_prompt_field) > 1024:
            n_prompt_field = f'{n_prompt_field[:1010]}....'
        embed.add_field(name=f'Negative prompt', value=f'``{n_prompt_field}``', inline=False)

    extra_params = f'Sampling steps: ``{steps}``\nSize: ``{size}``\nClassifier-free guidance scale: ``{guidance_scale}``\nSampling method: ``{sampler}``\nSeed: ``{seed}``'

    if style[0] != 'None':
        copy_command += f' style:{style[0]}'
        extra_params += f'\nStyle preset: ``{style[0]}``'
    
    embed.add_field(name=f'Other parameters', value=extra_params, inline=False)
    embed.add_field(name=f'Command for copying', value=f'', inline=False)
    embed.set_footer(text=copy_command)

    await ctx.respond(embed=embed, ephemeral=True)
