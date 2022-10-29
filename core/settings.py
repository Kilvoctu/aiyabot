import json
import os
import discord

self = discord.Bot()
dir_path = os.path.dirname(os.path.realpath(__file__))

path = 'resources/'.format(dir_path)

template = {
            "default_steps": 30,
            "sampler": "Euler a",
            "negative_prompt": "",
            "max_steps": 50
        }

#initialize global variables here
class GlobalVar:
    url = ""
    dir = ""
    embed_color = discord.Colour.from_rgb(222, 89, 28)

global_var = GlobalVar()

def build(guild_id):
    settings = json.dumps(template)
    with open(path + guild_id + '.json', 'w') as configfile:
        configfile.write(settings)

def read(guild_id):
    with open(path + guild_id + '.json', 'r') as configfile:
        settings = json.load(configfile)
    return settings

def update(guild_id:str, sett:str, value):
    with open(path + guild_id + '.json', 'r') as configfile:
        settings = json.load(configfile)
    settings[sett] = value
    with open(path + guild_id + '.json', 'w') as configfile:
        json.dump(settings, configfile)

def files_check(self):
    # creating files if they don't exist
    if os.path.isfile('resources/stats.txt'):
        pass
    else:
        print(f'Uh oh, stats.txt missing. Creating a new one.')
        with open('resources/stats.txt', 'w') as f: f.write('0')
    if os.path.isfile('resources/None.json'):
        pass
    else:
        print(f'Setting up settings for DMs, called None.json')
        build("None")

    # guild settings files
    for guild in self.guilds:
        try:
            read(str(guild.id))
            print(f'I\'m using local settings for {guild.id} a.k.a {guild}.')
        except FileNotFoundError:
            build(str(guild.id))
            print(f'Creating new settings file for {guild.id} a.k.a {guild}.')

    #check .env for URL and DIR. if they don't exist, ignore it and go with defaults.
    if os.getenv("URL") == '':
        global_var.url = os.environ.get('URL').rstrip("/")
        print(f'Using URL: {global_var.url}')
    else:
        global_var.url = 'http://127.0.0.1:7860'
        print('Using default URL: http://127.0.0.1:7860')

    if os.getenv("DIR") == '':
        global_var.dir = os.environ.get('DIR')
        print(f'Using outputs directory: {global_var.dir}')
    else:
        global_var.dir = "outputs"
        print('Using default outputs directory: outputs')
    #if directory in DIR doesn't exist, create it
    dir_exists = os.path.exists(global_var.dir)
    if dir_exists is False:
        print(f'The folder for DIR doesn\'t exist! Creating folder at {global_var.dir}.')
        os.mkdir(global_var.dir)