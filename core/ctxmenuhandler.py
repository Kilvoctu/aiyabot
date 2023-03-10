import base64
import discord
import re
import requests
from urlextract import URLExtract

from core import settings
from core import queuehandler
from core import upscalecog
from core import viewhandler


def extra_net_search(field):
    loras_used, hypers_used = {}, {}
    lora_results = re.findall('<lora:(.*?)>', field, re.DOTALL)
    hyper_results = re.findall('<hypernet:(.*?)>', field, re.DOTALL)
    for lora in lora_results:
        loras_used[lora.split(':')[0]] = lora.split(':')[1]
    for hyper in hyper_results:
        hypers_used[hyper.split(':')[0]] = hyper.split(':')[1]
    return loras_used, hypers_used


# functions to look for styles in the prompts
def style_search(search, field):
    search_list = search.split('{prompt}')
    matches = 0
    for y in search_list:
        if y in field:
            matches += 1
    if matches == len(search_list):
        return True


def style_remove(search, field):
    search_list = search.split('{prompt}')
    for y in search_list:
        if y in field:
            field = field.replace(y, '').strip()
    return field.strip(',')


async def parse_image_info(ctx, image_url, command):
    message = ''
    try:
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
        if "Negative prompt: " in png_data_list[1]:
            negative_prompt = str(png_data_list[1]).split("Negative prompt: ", 1)[1]
        else:
            negative_prompt = ''
            png_data_list.insert(1, '')

        # initialize model info
        display_name, model_name, model_hash = 'Unknown', 'Unknown', 'Unknown'
        activator_token = ''

        # initialize extra params
        steps, size, guidance_scale, sampler, seed = '', '', '', '', ''
        style, facefix, highres_fix, clip_skip = '', '', '', ''
        strength, has_init_url = '', False
        if command == 'button' and ctx is not None:
            has_init_url = True

        # try to find extra networks
        hypernet, lora = extra_net_search(prompt_field)

        # try to find the style used and remove from prompts
        for key, value in settings.global_var.style_names.items():
            try:
                style_prompt = list(value)
                if style_search(style_prompt[0], prompt_field) and style_search(style_prompt[1], negative_prompt):
                    style = [key, value]
                    break
            except(Exception,):
                pass
        # if style is not none then remove its tokens from prompts
        if style:
            prompt_field = style_remove(style[1][0], prompt_field)
            negative_prompt = style_remove(style[1][1], negative_prompt)

        # grab parameters
        extra_params_split = png_data_list[2].split(", ")
        for line in extra_params_split:
            if 'Model hash: ' in line:
                model_hash = line.split(': ', 1)[1]
            if 'Model: ' in line:
                model_name = line.split(': ', 1)[1]

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

            if 'Face restoration: ' in line:
                facefix = line.split(': ', 1)[1]
            if 'Hires upscaler: ' in line:
                highres_fix = line.split(': ', 1)[1]
            if 'Clip skip: ' in line:
                clip_skip = line.split(': ', 1)[1]

            if 'Denoising strength: ' in line:
                strength = line.split(': ', 1)[1]

        width_height = size.split("x")

        # try to find the model name and activator token
        for model in settings.global_var.model_info.items():
            if model[1][2] == model_hash or model[1][1] == model_name:
                display_name = model[0]
                if model[1][3]:
                    activator_token = f"\nActivator token - ``{model[1][3]}``"
                    prompt_field = prompt_field.replace(f"{model[1][3]} ", "")
        # strip any folders from model name
        model_name = model_name.split('_', 1)[-1]

        # run prompts through mod function
        mod_results = settings.prompt_mod(prompt_field, negative_prompt)
        if mod_results[0] == "Mod":
            prompt_field = mod_results[1]
            negative_prompt = mod_results[3]

        # create embed and give the best effort in trying to parse the png info
        embed = discord.Embed(title="About the image!", description="")
        if not has_init_url:  # for some reason this bugs out the embed
            embed.set_thumbnail(url=image_url)
        if len(prompt_field) > 1024:
            prompt_field = f'{prompt_field[:1010]}....'
        embed.colour = settings.global_var.embed_color
        embed.add_field(name=f'Prompt', value=f'``{prompt_field}``', inline=False)
        embed.add_field(name='Data model', value=f'Display name - ``{display_name}``\nModel name - ``{model_name}``'
                                                 f'\nShorthash - ``{model_hash}``{activator_token}', inline=False)

        copy_command = f'/draw prompt:{prompt_field} steps:{steps} width:{width_height[0]} height:{width_height[1]}' \
                       f' guidance_scale:{guidance_scale} sampler:{sampler} seed:{seed}'
        if display_name != 'Unknown':
            copy_command += f' data_model:{display_name}'

        if negative_prompt != '':
            copy_command += f' negative_prompt:{negative_prompt}'
            n_prompt_field = negative_prompt
            if len(n_prompt_field) > 1024:
                n_prompt_field = f'{n_prompt_field[:1010]}....'
            embed.add_field(name=f'Negative prompt', value=f'``{n_prompt_field}``', inline=False)

        extra_params = f'Sampling steps: ``{steps}``\nSize: ``{size}``\nClassifier-free guidance scale: ' \
                       f'``{guidance_scale}``\nSampling method: ``{sampler}``\nSeed: ``{seed}``'

        if style:
            copy_command += f' styles:{style[0]}'
            extra_params += f'\nStyle preset: ``{style[0]}``'
        if facefix:
            copy_command += f' facefix:{facefix}'
            extra_params += f'\nFace restoration model: ``{facefix}``'
        if highres_fix:
            copy_command += f' highres_fix:{highres_fix}'
            extra_params += f'\nHigh-res fix: ``{highres_fix}``'
        if clip_skip:
            copy_command += f' clip_skip:{clip_skip}'
            extra_params += f'\nCLIP skip: ``{clip_skip}``'

        embed.add_field(name=f'Other parameters', value=extra_params, inline=False)

        if lora or hypernet:
            network_params = ''
            for key, value in hypernet.items():
                network_params += f'\nLoRA: ``{key}`` (multiplier: ``{value}``)'
            for key, value in lora.items():
                network_params += f'\nHypernet: ``{key}`` (multiplier: ``{value}``)'
            embed.add_field(name=f'Extra networks', value=network_params, inline=False)

        if has_init_url:
            # not interested in adding embed fields for strength and init_image
            copy_command += f' strength:{strength} init_url:{str(ctx)}'

        embed.add_field(name=f'Command for copying', value=f'', inline=False)
        embed.set_footer(text=copy_command)

        if command == 'button':
            return embed

        await ctx.respond(embed=embed, ephemeral=True)
    except Exception as e:
        print('The image info command broke: ' + str(e))
        if command == 'slash':
            message = "\nIf you're copying from Discord and think there should be image info," \
                      " try **Copy Link** instead of **Copy Image**"
        await ctx.respond(content=f"The image information is empty or unreadable!{message}", ephemeral=True)


async def get_image_info(ctx, message: discord.Message):
    # look for images in message
    all_content = message.content
    if message.attachments:
        for i in message.attachments:
            all_content += f"\n{i}"
    extractor = URLExtract()
    urls = extractor.find_urls(all_content)

    if not urls:
        await ctx.respond(content="No images were found in the message...", ephemeral=True)
        return

    for image_url in urls:
        await parse_image_info(ctx, image_url, "context")


async def quick_upscale(self, ctx, message: discord.Message):
    # look for images in message (we will only use the first one, though)
    all_content = message.content
    if message.attachments:
        for i in message.attachments:
            all_content += f"\n{i}"
    extractor = URLExtract()
    urls = extractor.find_urls(all_content)

    if not urls:
        await ctx.respond(content="No images were found in the message...", ephemeral=True)
        return

    # update defaults with any new defaults from settingscog
    channel = '% s' % ctx.channel.id
    settings.check(channel)
    upscaler_1 = settings.read(channel)['upscaler_1']

    init_image = requests.get(urls[0])
    resize = settings.global_var.quick_upscale_resize
    upscaler_2, upscaler_2_strength = "None", '0.5'
    gfpgan, codeformer = '0.0', '0.0'
    upscale_first = False

    message = ''
    if len(urls) > 1:
        message = 'the first image '

    # set up tuple of parameters
    input_tuple = (
        ctx, resize, init_image, upscaler_1, upscaler_2, upscaler_2_strength, gfpgan, codeformer, upscale_first)
    view = viewhandler.DeleteView(input_tuple)
    user_queue_limit = settings.queue_check(ctx.author)
    upscale_dream = upscalecog.UpscaleCog(self)
    if queuehandler.GlobalQueue.dream_thread.is_alive():
        if user_queue_limit == "Stop":
            await ctx.send_response(
                content=f"Please wait! You're past your queue limit of {settings.global_var.queue_limit}.",
                ephemeral=True)
        else:
            queuehandler.GlobalQueue.queue.append(queuehandler.UpscaleObject(upscale_dream, *input_tuple, view))
    else:
        await queuehandler.process_dream(upscale_dream, queuehandler.UpscaleObject(upscale_dream, *input_tuple, view))
    if user_queue_limit != "Stop":
        await ctx.send_response(
            f'<@{ctx.author.id}>, upscaling {message}by ``{resize}``x using ``{upscaler_1}``!\n'
            f'Queue: ``{len(queuehandler.GlobalQueue.queue)}``', delete_after=45.0)
