import os
import json

dir_path = os.path.dirname(os.path.realpath(__file__))

path = '{}/generated/'.format(dir_path)

template = {
            "default_steps": 30,
            "sampler": "Euler",
            "negative_prompt": "",
            "max_steps": 30
        }




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
