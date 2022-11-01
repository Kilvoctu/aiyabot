import csv
import json
import os
import requests
from typing import Optional
import discord

self = discord.Bot()
dir_path = os.path.dirname(os.path.realpath(__file__))

path = 'resources/'.format(dir_path)

template = {
            "default_steps": 30,
            "sampler": "Euler a",
            "negative_prompt": "",
            "max_steps": 50,
            "default_count": 1,
            "max_count": 1
        }

#initialize global variables here
class GlobalVar:
    url = ""
    dir = ""
    embed_color = discord.Colour.from_rgb(222, 89, 28)
    username: Optional[str] = None
    password: Optional[str] = None
    copy_command: bool = False
    model_fn_index = 0
    default_model = ""

global_var = GlobalVar()

def build(guild_id):
    settings = json.dumps(template)
    with open(path + guild_id + '.json', 'w') as configfile:
        configfile.write(settings)

def read(guild_id):
    with open(path + guild_id + '.json', 'r') as configfile:
        settings = dict(template)
        settings.update(json.load(configfile))
    return settings

def update(guild_id:str, sett:str, value):
    with open(path + guild_id + '.json', 'r') as configfile:
        settings = json.load(configfile)
    settings[sett] = value
    with open(path + guild_id + '.json', 'w') as configfile:
        json.dump(settings, configfile)

def get_env_var_with_default(var: str, default: str) -> str:
    ret = os.getenv(var)
    return ret if ret is not None else default

def files_check():
    #creating files if they don't exist
    if os.path.isfile('resources/stats.txt'):
        pass
    else:
        print(f'Uh oh, stats.txt missing. Creating a new one.')
        with open('resources/stats.txt', 'w') as f:
            f.write('0')
    if os.path.isfile('resources/models.csv'):
        pass
    else:
        print(f'Uh oh, models.csv missing. Creating a new one.')
        header = ['model display name', 'model name in web ui']
        with open('resources/models.csv', 'w', newline='', encoding='utf-8') as f:
            f.write("#Enter your list of models following the format. Don't remove these first two rows!\n")
            writer = csv.writer(f, delimiter = "|")
            writer.writerow(header)

    #check .env for parameters. if they don't exist, ignore it and go with defaults.
    global_var.url = get_env_var_with_default('URL', 'http://127.0.0.1:7860').rstrip("/")
    print(f'Using URL: {global_var.url}')

    global_var.dir = get_env_var_with_default('DIR', 'outputs')
    print(f'Using outputs directory: {global_var.dir}')

    global_var.username = os.getenv("USER")
    global_var.password = os.getenv("PASS")
    global_var.copy_command = os.getenv("COPY") is not None

    #if directory in DIR doesn't exist, create it
    dir_exists = os.path.exists(global_var.dir)
    if dir_exists is False:
        print(f'The folder for DIR doesn\'t exist! Creating folder at {global_var.dir}.')
        os.mkdir(global_var.dir)

def guilds_check(self):
    #guild settings files. has to be done after on_ready
    for guild in self.guilds:
        try:
            read(str(guild.id))
            print(f'I\'m using local settings for {guild.id} a.k.a {guild}.')
        except FileNotFoundError:
            build(str(guild.id))
            print(f'Creating new settings file for {guild.id} a.k.a {guild}.')

    if os.path.isfile('resources/None.json'):
        pass
    else:
        print(f'Setting up settings for DMs, called None.json')
        build("None")

#iterate through the old api at /config to get things we need that don't exist in new api
def old_api_check():
    config_url = requests.get(global_var.url + "/config")
    old_config = config_url.json()

    #get the model currently selected in web ui, set as global fallback model
    current_model = old_config["components"][1]["props"]["value"]
    global_var.default_model = current_model
    print("Fallback model set to " + str(current_model) + "!")

    global model_fn_index
    #check all dependencies in config to see if there's a target value
    #and if there is, match the target value to the id value of component we want
    #this provides the fn_index needed for the payload to old api
    for d in range(len(old_config["dependencies"])):
        try:
            for c in old_config["components"]:
                if old_config["dependencies"][d]["targets"][0] == c["id"] and c["props"].get(
                        "label") == "Stable Diffusion checkpoint":
                    global_var.model_fn_index = d
        except:
            pass
    print("The fn_index for the model is " + str(global_var.model_fn_index) + "!")