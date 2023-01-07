import csv
import discord
import json
import os
import random
import requests
import time
from typing import Optional

self = discord.Bot()
dir_path = os.path.dirname(os.path.realpath(__file__))

path = 'resources/'.format(dir_path)

template = {
    "negative_prompt": "",
    "data_model": "",
    "default_steps": 30,
    "max_steps": 50,
    "default_width": 512,
    "default_height": 512,
    "sampler": "Euler a",
    "default_count": 1,
    "max_count": 1,
    "clip_skip": 1,
    "hypernet": "None"
}


# initialize global variables here
class GlobalVar:
    url = ""
    dir = ""
    wait_message = []
    wait_message_count = 0
    embed_color = discord.Colour.from_rgb(222, 89, 28)
    gradio_auth = False
    username: Optional[str] = None
    password: Optional[str] = None
    api_auth = False
    api_user: Optional[str] = None
    api_pass: Optional[str] = None
    send_model = False
    model_names = {}
    model_tokens = {}
    simple_model_pairs = {}
    size_range = range(192, 1088, 64)
    sampler_names = []
    style_names = {}
    facefix_models = []
    embeddings_1 = []
    embeddings_2 = []
    hyper_names = []


global_var = GlobalVar()


def stats_count(number):
    with open('resources/stats.txt', 'r') as f:
        data = list(map(int, f.readlines()))
    data[0] += number
    with open('resources/stats.txt', 'w') as f:
        f.write('\n'.join(str(x) for x in data))


def messages():
    random_message = global_var.wait_message[random.randint(0, global_var.wait_message_count)]
    return random_message


def build(guild_id):
    settings = json.dumps(template)
    with open(path + guild_id + '.json', 'w') as configfile:
        configfile.write(settings)


def read(guild_id):
    with open(path + guild_id + '.json', 'r') as configfile:
        settings = dict(template)
        settings.update(json.load(configfile))
    return settings


def update(guild_id: str, sett: str, value):
    with open(path + guild_id + '.json', 'r') as configfile:
        settings = json.load(configfile)
    settings[sett] = value
    with open(path + guild_id + '.json', 'w') as configfile:
        json.dump(settings, configfile)


def get_env_var_with_default(var: str, default: str) -> str:
    ret = os.getenv(var)
    return ret if ret is not None else default


def startup_check():
    # check .env for parameters. if they don't exist, ignore it and go with defaults.
    global_var.url = get_env_var_with_default('URL', 'http://127.0.0.1:7860').rstrip("/")
    print(f'Using URL: {global_var.url}')

    global_var.dir = get_env_var_with_default('DIR', 'outputs')
    print(f'Using outputs directory: {global_var.dir}')

    global_var.username = os.getenv("USER")
    global_var.password = os.getenv("PASS")
    global_var.api_user = os.getenv("APIUSER")
    global_var.api_pass = os.getenv("APIPASS")

    # check if Web UI is running
    connected = False
    while not connected:
        try:
            response = requests.get(global_var.url + '/sdapi/v1/cmd-flags')
            # lazy method to see if --api-auth commandline argument is set
            if response.status_code == 401:
                global_var.api_auth = True
                # lazy method to see if --api-auth credentials are set
                if (not global_var.api_pass) or (not global_var.api_user):
                    print('API rejected me! If using --api-auth, '
                          'please check your .env file for APIUSER and APIPASS values.')
                    os.system("pause")
            # lazy method to see if --api commandline argument is not set
            if response.status_code == 404:
                print('API is unreachable! Please check Web UI COMMANDLINE_ARGS for --api.')
                os.system("pause")
            return requests.head(global_var.url)
        except(Exception,):
            print(f'Waiting for Web UI at {global_var.url}...')
            time.sleep(20)


def files_check():
    # load random messages for aiya to say
    with open('resources/messages.csv') as csv_file:
        message_data = list(csv.reader(csv_file, delimiter='|'))
        for row in message_data:
            global_var.wait_message.append(row[0])
    global_var.wait_message_count = len(global_var.wait_message) - 1

    # creating files if they don't exist
    if os.path.isfile('resources/stats.txt'):
        pass
    else:
        print(f'Uh oh, stats.txt missing. Creating a new one.')
        with open('resources/stats.txt', 'w') as f:
            f.write('0')

    header = ['display_name', 'model_full_name', 'activator_token']
    unset_model = ['Default', '', '']
    make_model_file = True
    replace_model_file = False
    # if models.csv exists and has data
    if os.path.isfile('resources/models.csv'):
        with open('resources/models.csv', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter="|")
            for i, row in enumerate(reader):
                # if header is missing columns, reformat the file
                if i == 0:
                    if len(row) < 3:
                        with open('resources/models.csv', 'r') as fp:
                            reader = csv.DictReader(fp, fieldnames=header, delimiter="|")
                            with open('resources/models2.csv', 'w', newline='') as fh:
                                writer = csv.DictWriter(fh, fieldnames=reader.fieldnames, delimiter="|")
                                writer.writeheader()
                                header = next(reader)
                                writer.writerows(reader)
                                replace_model_file = True
                # if first row has data, do nothing
                if i == 1:
                    make_model_file = False
        if replace_model_file:
            os.remove('resources/models.csv')
            os.rename('resources/models2.csv', 'resources/models.csv')
    # create/reformat model.csv if something is wrong
    if make_model_file:
        print(f'Uh oh, missing models.csv data. Creating a new one.')
        with open('resources/models.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f, delimiter="|")
            writer.writerow(header)
            writer.writerow(unset_model)

    # if directory in DIR doesn't exist, create it
    dir_exists = os.path.exists(global_var.dir)
    if dir_exists is False:
        print(f"The folder for DIR doesn't exist! Creating folder at {global_var.dir}.")
        os.mkdir(global_var.dir)

    populate_global_vars()


def populate_global_vars():
    # get display_name:model_full_name pairs from models.csv into global variable
    # do same for display_name:activator token pairs
    with open('resources/models.csv', encoding='utf-8') as csv_file:
        model_data = list(csv.reader(csv_file, delimiter='|'))
        for row in model_data[1:]:
            global_var.model_names[row[0]] = row[1]
            global_var.model_tokens[row[0]] = row[2]

    # pull list of samplers, styles and face restorers from api
    # create persistent session since we'll need to do a few API calls
    s = requests.Session()
    if global_var.api_auth:
        s.auth = (global_var.api_user, global_var.api_pass)

    # do a check to see if --gradio-auth is set
    r0 = s.get(global_var.url + '/sdapi/v1/cmd-flags')
    response_data = r0.json()
    if response_data['gradio_auth']:
        global_var.gradio_auth = True

    if global_var.gradio_auth:
        login_payload = {
            'username': global_var.username,
            'password': global_var.password
        }
        s.post(global_var.url + '/login', data=login_payload)
    else:
        s.post(global_var.url + '/login')

    # load many values from Web UI into global variables
    r = s.get(global_var.url + "/sdapi/v1/samplers")
    r2 = s.get(global_var.url + "/sdapi/v1/prompt-styles")
    r3 = s.get(global_var.url + "/sdapi/v1/face-restorers")
    r4 = s.get(global_var.url + "/sdapi/v1/sd-models")
    r5 = s.get(global_var.url + "/sdapi/v1/embeddings")
    r6 = s.get(global_var.url + "/sdapi/v1/hypernetworks")
    for s1 in r.json():
        try:
            global_var.sampler_names.append(s1['name'])
        except(Exception,):
            # throw in last exception error for anything that wasn't caught earlier
            print("Can't connect to API for some reason!"
                  "Please check your .env URL or credentials.")
            os.system("pause")
    for s2 in r2.json():
        global_var.style_names[s2['name']] = s2['prompt']
    for s3 in r3.json():
        global_var.facefix_models.append(s3['name'])
    for s4 in r4.json():
        global_var.simple_model_pairs[s4['title']] = s4['model_name']
    for s5, shape in r5.json()['loaded'].items():
        if shape['shape'] == 768:
            global_var.embeddings_1.append(s5)
        if shape['shape'] == 1024:
            global_var.embeddings_2.append(s5)
    for s5, shape in r5.json()['skipped'].items():
        if shape['shape'] == 768:
            global_var.embeddings_1.append(s5)
        if shape['shape'] == 1024:
            global_var.embeddings_2.append(s5)
    # add default "None" hypernetwork as option
    global_var.hyper_names.append('None')
    for s6 in r6.json():
        global_var.hyper_names.append(s6['name'])


def guilds_check(self):
    # guild settings files. has to be done after on_ready
    for guild in self.guilds:
        try:
            read(str(guild.id))
            print(f'I\'m using local settings for {guild.id} a.k.a {guild}.')
            # if models.csv has the blank "Default" data, update guild settings
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
