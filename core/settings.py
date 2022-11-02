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
            "max_count": 1,
            "data_model": ""
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

    header = ['display_name', 'model_full_name']
    unset_model = ['Default', '']
    make_model_file = True
    #if models.csv exists and has data, assume it's good to go
    if os.path.isfile('resources/models.csv'):
        with open('resources/models.csv', encoding='utf-8') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if i == 1:
                    make_model_file = False
    #otherwise create/reformat it
    if make_model_file:
        print(f'Uh oh, missing models.csv data. Creating a new one.')
        with open('resources/models.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter = "|")
            writer.writerow(header)
            writer.writerow(unset_model)

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
            #if models.csv has the blank "Default" data, update guild settings
            with open('resources/models.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f, delimiter='|')
                for row in reader:
                    if row['display_name'] == 'Default' and row['model_full_name'] == '':
                        update(str(guild.id), 'data_model', '')
                        print('I see models.csv is on defaults. Updating guild model settings to default.')
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
    with requests.Session() as s:
        if global_var.username is not None:
            login_payload = {
                'username': global_var.username,
                'password': global_var.password
            }
            s.post(global_var.url + '/login', data=login_payload)
            config_url = s.get(global_var.url + "/config")
        else:
            s.post(global_var.url + '/login')
            config_url = s.get(global_var.url + "/config")
        old_config = config_url.json()
        #check all dependencies in config to see if there's a target value
        #and if there is, match the target value to the id value of component we want
        #this provides the fn_index needed for the payload to old api
        for d in range(len(old_config["dependencies"])):
            try:
                for c in old_config["components"]:
                    if old_config["dependencies"][d]["targets"][0] == c["id"] and c["props"].get(
                            "label") == "Stable Diffusion checkpoint":
                        global_var.model_fn_index = d
            except(Exception,):
                pass
        print("The fn_index for the model is " + str(global_var.model_fn_index) + "!")