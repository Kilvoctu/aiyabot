import os
from os.path import exists
import sys
import discord
import asyncio
import json
import requests
from dotenv import load_dotenv
from core.logging import get_logger
from enum import Enum

#start up initialization stuff
global URL
self = discord.Bot()
intents = discord.Intents.default()
intents.members = True
load_dotenv()
embed_color = discord.Colour.from_rgb(222, 89, 28)
responsestr = {}
self.logger = get_logger(__name__)

file_exists = exists('resources/stats.txt')
if file_exists is False:
    self.logger.info(f'stats.txt missing. Creating new file.')
    with open('resources/stats.txt', 'w') as f: f.write('0')

class IndexKeeper:
    prompt_ind = 0
    exclude_ind = 0
    sample_ind = 0
    resy_ind = 0
    resx_ind = 0
    conform_ind = 0
    sampling_methods_ind = 0
    seed_ind = 0
    denoise_ind = 0
    data_ind = 0
    def request_ind(self):
        return self.request_ind

if os.environ.get('URL') == '':
    URL = 'http://127.0.0.1:7860'
    print('Using Default URL: http://127.0.0.1:7860')
else:
    URL = os.environ.get('URL')
with requests.Session() as s:
    if os.environ.get('USER'):
        if os.environ.get('PASS') == '':
            raise SystemExit('There is no password set. Please set a password in the .env file.')
        else:
            LogInPayload = {
                'username': os.getenv('USER'),
                'password': os.getenv('PASS')
            }
        print('Logging into the API')
        p = s.post(URL + '/login', data=LogInPayload)
    else:
        print('No Username Set')
        p = s.post(URL + '/login')
    r = s.get(URL + '/config')

    response_format = s.get(URL + '/config')
    responsestr = response_format.json()
    print('Web UI config loaded.')

class PayloadFormat(Enum):
    TXT2IMG = 0
    IMG2IMG = 1
    UPSCALE = 2

#look through web ui config and get indices
def do_format(payload_format: PayloadFormat):
    dependenciesjson = responsestr["dependencies"]
    componentsjson = responsestr["components"]
    dependencylist = []
    labelvaluetuplelist = []

    txt2img_fn_index = 0
    img2img_fn_index = 0
    upscale_fn_index = 0

    for dep in range(0, len(dependenciesjson)):
        if (dependenciesjson[dep]["js"] == "submit" and payload_format == PayloadFormat.TXT2IMG) or (dependenciesjson[dep]["js"] == "submit_img2img" and payload_format == PayloadFormat.IMG2IMG) or (dependenciesjson[dep]["js"] == "get_extras_tab_index" and payload_format == PayloadFormat.UPSCALE):
            dependencylist = dependenciesjson[dep]["inputs"].copy()
            for i in dependenciesjson[dep]["outputs"]:
                try:
                    dependencylist.append(i.copy())
                except:
                    dependencylist.append(i)

        if dependenciesjson[dep]["js"] == "submit" and txt2img_fn_index == 0:
            txt2img_fn_index = dep
        elif dependenciesjson[dep]["js"] == "submit_img2img" and img2img_fn_index == 0:
            img2img_fn_index = dep
        elif dependenciesjson[dep]["js"] == "get_extras_tab_index" and upscale_fn_index == 0:
            upscale_fn_index = dep

    for identifier in dependencylist:
        for component in componentsjson:
            if identifier == component["id"]:
                #one of the labels is empty
                if component["props"].get("name") == "label":
                    labelvaluetuplelist.append(("", 0))
                #img2img has a duplicate label that messes things up
                elif component["props"].get("label") == "Image for img2img" and component["props"].get("elem_id") != "img2img_image":
                    labelvaluetuplelist.append(("", None))
                #upscale has a duplicate label that messes things up
                elif component["props"].get("label") == "Source" and component["props"].get("elem_id") == "pnginf_image":
                    labelvaluetuplelist.append(("", None))
                #only use the one upscaler
                elif component["props"].get("label") == "Upscaler 1":
                    labelvaluetuplelist.append((component["props"].get("label"), "ESRGAN_4x"))
                #slightly changing the img2img Script label so it doesn't clash with another label of the same name
                elif component["props"].get("label") == "Script" and len(component["props"].get("choices")) > 3:
                    labelvaluetuplelist.append(("Scripts", "None"))
                elif component["props"].get("label") == "Sampling method":
                    labelvaluetuplelist.append(("Sampling method", "Euler a"))
                    self.sampling_methods = component["props"].get("choices")
                #these are the labels and values we actually care about
                else:
                    labelvaluetuplelist.append((component["props"].get("label"), component["props"].get("value")))
                break

    for i in range(0, len(labelvaluetuplelist)):
        if labelvaluetuplelist[i][0] == "Prompt":
            IndexKeeper.prompt_ind = i
        elif labelvaluetuplelist[i][0] == "Negative prompt":
            IndexKeeper.exclude_ind = i
        elif labelvaluetuplelist[i][0] == "Sampling Steps":
            IndexKeeper.sample_ind = i
        elif labelvaluetuplelist[i][0] == "Batch count":
            IndexKeeper.num_ind = i
        elif labelvaluetuplelist[i][0] == "CFG Scale":
            IndexKeeper.conform_ind = i
        elif labelvaluetuplelist[i][0] == "Seed":
            IndexKeeper.seed_ind = i
        elif labelvaluetuplelist[i][0] == "Height":
            IndexKeeper.resy_ind = i
        elif labelvaluetuplelist[i][0] == "Width":
            IndexKeeper.resx_ind = i
        elif labelvaluetuplelist[i][0] == "Denoising strength":
            IndexKeeper.denoise_ind = i
        elif labelvaluetuplelist[i][0] == "Image for img2img":
            IndexKeeper.data_ind = i
        elif labelvaluetuplelist[i][0] == "Source":
            IndexKeeper.data_ind = i
        elif labelvaluetuplelist[i][0] == "Resize":
            IndexKeeper.resize_ind = i
        elif labelvaluetuplelist[i][0] == "Scripts":
            IndexKeeper.script_ind = i
        elif labelvaluetuplelist[i][0] == "Loops":
            IndexKeeper.loop_ind = i
        elif labelvaluetuplelist[i][0] == "Sampling method":
            IndexKeeper.sampling_methods_ind = i

    data = []
    for i in labelvaluetuplelist:
        data.append(i[1])
    filename = "data.json"
    prepend = "{\"fn_index\": %s,\"data\": " % txt2img_fn_index
    if payload_format == PayloadFormat.IMG2IMG:
        filename = "imgdata.json"
        prepend = "{\"fn_index\": %s,\"data\": " % img2img_fn_index
    elif payload_format == PayloadFormat.UPSCALE:
        filename = "updata.json"
        prepend = "{\"fn_index\": %s,\"data\": " % upscale_fn_index
    postend = ",\"session_hash\": \"cucp21gbbx8\"}"
    with open(filename, "w") as f:
        f.write(prepend)
        f.write(json.dumps(data, indent=2))
        f.write(postend)

#do initial formatting, then load stablecog
do_format(PayloadFormat.TXT2IMG)
print(f'Indices-prompt:{IndexKeeper.prompt_ind}, exclude:{IndexKeeper.exclude_ind}, steps:{IndexKeeper.sample_ind}, height:{IndexKeeper.resy_ind}, width:{IndexKeeper.resx_ind}, cfg scale:{IndexKeeper.conform_ind}, sampler:{IndexKeeper.sampling_methods_ind}, seed:{IndexKeeper.seed_ind}')

self.load_extension('core.stablecog')
self.load_extension('core.tipscog')

#stats slash command
@self.slash_command(name = 'stats', description = 'How many images has the bot generated?')
async def stats(ctx):
    with open('resources/stats.txt', 'r') as f: data = list(map(int, f.readlines()))
    embed = discord.Embed(title='Art generated', description=f'I have created {data[0]} pictures!', color=embed_color)
    await ctx.respond(embed=embed)

@self.event
async def on_ready():
    self.logger.info(f'Logged in as {self.user.name} ({self.user.id})')
    await self.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name='drawing tutorials.'))

#feature to delete generations. give bot "Add Reactions" permission (or not, to hide the ❌)
@self.event
async def on_message(message):
    if message.author == self.user:
        try:
            if message.embeds[0].fields[0].name == 'command':
                await message.add_reaction('❌')
        except:
            pass

@self.event
async def on_raw_reaction_add(ctx):
    if ctx.emoji.name == '❌':
        message = await self.get_channel(ctx.channel_id).fetch_message(ctx.message_id)
        if message.embeds:
            if message.embeds[0].footer.text == f'{ctx.member.name}#{ctx.member.discriminator}':
                await message.delete()


async def shutdown(bot):
    await bot.close()

try:
    self.run(os.getenv('TOKEN'))
except KeyboardInterrupt:
    self.logger.info('Keyboard interrupt received. Exiting.')
    asyncio.run(shutdown(self))
except SystemExit:
    self.logger.info('System exit received. Exiting.')
    asyncio.run(shutdown(self))
except Exception as e:
    self.logger.error(e)
    asyncio.run(shutdown(self))
finally:
    sys.exit(0)