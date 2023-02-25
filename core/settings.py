import csv
import discord
import json
import os
import random
import requests
import time
import tomlkit
from typing import Optional

from core import queuehandler

self = discord.Bot()
dir_path = os.path.dirname(os.path.realpath(__file__))
path = 'resources/'.format(dir_path)

# the fallback defaults for AIYA if bot host doesn't set anything
template = {
    "negative_prompt": "",
    "data_model": "",
    "steps": 30,
    "max_steps": 50,
    "width": 512,
    "height": 512,
    "guidance_scale": "7.0",
    "sampler": "Euler a",
    "style": "None",
    "facefix": "None",
    "highres_fix": 'Disabled',
    "clip_skip": 1,
    "hypernet": "None",
    "lora": "None",
    "strength": "0.75",
    "batch": "1,1",
    "max_batch": "1,1",
    "upscaler_1": "ESRGAN_4x"
}

# default config data
default_config = """# This is the config file. It's advisable to restart if any changes are made.

# The URL address to the AUTOMATIC1111 Web UI
url = "http://127.0.0.1:7860"

# Credentials when using --share and --gradio-auth
user = ""
pass = ""

# Credentials when using --api-auth
apiuser = ""
apipass = ""

# Whether or not to save outputs to disk ("True"/"False")
save_outputs = "True"
# Whether or not to include parameter info into images ("True"/"False")
save_metadata = "True"

# The directory to save outputs (default = "outputs")
dir = "outputs"

# The limit of tasks a user can have waiting in queue (at least 1)
queue_limit = 1

# The maximum value allowed for width/height (keep as multiple of 64)
max_size = 1024

# AIYA won't generate if prompt has any words in the ban list.
# Separate with commas; example, ["a", "b", "c"]
prompt_ban_list = []
# These words will be automatically removed from the prompt.
prompt_ignore_list = []
# Choose whether or not ignored words are displayed to user.
display_ignored_words = "False"
# These words will be added to the beginning of the negative prompt.
negative_prompt_prefix = []
"""


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
    model_info = {}
    size_range = range(192, 1088, 64)
    sampler_names = []
    style_names = {}
    facefix_models = []
    embeddings_1 = []
    embeddings_2 = []
    hyper_names = []
    lora_names = []
    upscaler_names = []
    hires_upscaler_names = []
    save_outputs = "True"
    save_metadata = "True"
    queue_limit = 1
    prompt_ban_list = []
    prompt_ignore_list = []
    display_ignored_words = "False"
    negative_prompt_prefix = []


global_var = GlobalVar()


def batch_format(batch_string):
    format_batch_string = batch_string.replace(".", ",").split(",")
    values_given = len(format_batch_string)
    if values_given < 2:
        format_batch_string.append('1')
    # try to ensure each value is an integer of at least 1
    try:
        count = int(format_batch_string[0])
        if count < 1:
            count = 1
    except(Exception,):
        count = 1
    try:
        size = int(format_batch_string[1])
        if size < 1:
            size = 1
    except(Exception,):
        size = 1
    return count, size, values_given


def prompt_mod(prompt, negative_prompt):
    clean_negative_prompt = negative_prompt
    # if any banned words are in prompt, return immediately
    if global_var.prompt_ban_list:
        for x in global_var.prompt_ban_list:
            x = str(x.lower())
            if x in prompt.lower():
                return "Stop", x
    # otherwise mod the prompt/negative prompt
    if global_var.prompt_ignore_list or global_var.negative_prompt_prefix:
        for y in global_var.prompt_ignore_list:
            y = str(y.lower())
            if y in prompt.lower():
                prompt = prompt.replace(y, "")
        prompt = ' '.join(prompt.split())
        if prompt == '':
            prompt = ' '
        for z in global_var.negative_prompt_prefix:
            z = str(z.lower())
            if z in negative_prompt.lower():
                clean_negative_prompt = clean_negative_prompt.replace(z, "")
            else:
                negative_prompt = f"{z} {negative_prompt}"
        return "Mod", prompt, negative_prompt.strip(), clean_negative_prompt.strip()
    return "None"


def queue_check(author_compare):
    user_queue = 0
    for queue_object in queuehandler.GlobalQueue.queue:
        if queue_object.ctx.author.id == author_compare.id:
            user_queue += 1
            if user_queue >= global_var.queue_limit:
                return "Stop"


def stats_count(number):
    with open(f'{path}stats.txt', 'r') as f:
        data = list(map(float, f.readlines()))
    data[0] += number
    with open(f'{path}stats.txt', 'w') as f:
        f.write('\n'.join(str(int(x)) for x in data))


def messages():
    random_message = global_var.wait_message[random.randint(0, global_var.wait_message_count)]
    return random_message


def check(channel_id):
    try:
        read(str(channel_id))
    except FileNotFoundError:
        build(str(channel_id))
        print(f'This is a new channel!? Creating default settings file for this channel ({channel_id}).')
        # if models.csv has the blank "Default" data, update default settings
        with open(f'{path}models.csv', 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f, delimiter='|')
            for row in reader:
                if row['display_name'] == 'Default' and row['model_full_name'] == '':
                    update(str(channel_id), 'data_model', '')
                    print('I see models.csv is on defaults. Updating model settings to default.')


def build(channel_id):
    settings = json.dumps(template, indent=1)
    with open(path + channel_id + '.json', 'w') as configfile:
        configfile.write(settings)


def read(channel_id):
    with open(path + channel_id + '.json', 'r') as configfile:
        settings = dict(template)
        settings.update(json.load(configfile))

        # update deprecated 'count' to 'batch'
        if 'count' in settings or 'max_count' in settings:
            try:
                settings['batch'] = str(settings.pop('count'))
                settings['max_batch'] = str(settings.pop('max_count'))
            except(Exception,):
                pass
            with open(path + channel_id + '.json', 'w') as configfile2:
                json.dump(settings, configfile2, indent=1)

    return settings


def update(channel_id: str, sett: str, value):
    with open(path + channel_id + '.json', 'r') as configfile:
        settings = json.load(configfile)
    settings[sett] = value
    with open(path + channel_id + '.json', 'w') as configfile:
        json.dump(settings, configfile, indent=1)


def get_env_var_with_default(var: str, default: str) -> str:
    ret = os.getenv(var)
    return ret if ret is not None else default


def startup_check():
    config_exists = True
    if os.path.isfile(f'{path}config.toml'):
        pass
    else:
        print(f"Configuration file missing! I'm creating config.toml in {path}.")
        config_exists = False
        with open(f'{path}config.toml', "w") as toml_file:
            toml_file.write(tomlkit.dumps(tomlkit.loads(default_config)))

    with open(f'{path}config.toml', 'r') as fileObj:
        content = fileObj.read()
        config = tomlkit.loads(content)

    # update the config if any new keys were added
    if not tomlkit.loads(default_config).keys() == config.keys():
        print('Configuration file keys mismatch! Updating the file.')
        temp_config = {}
        for k, v in config.items():
            temp_config[k] = v

        with open(f'{path}config.toml', "w") as toml_file:
            toml_file.write(tomlkit.dumps(tomlkit.loads(default_config)))
        with open(f'{path}config.toml', 'r') as fileObj:
            content = fileObj.read()
            config = tomlkit.loads(content)
        for key, value in config.items():
            for k, v in temp_config.items():
                if k == key and value != v:
                    config[key] = v
                    f = open(f'{path}config.toml', 'w')
                    tomlkit.dump(config, f)
                    f.close()

    # port any settings that were set in .env file to the config
    if not config_exists:
        config['url'] = get_env_var_with_default('URL', 'http://127.0.0.1:7860').rstrip("/")
        config['dir'] = get_env_var_with_default('DIR', 'outputs')
        config['user'] = os.getenv("USER")
        config['pass'] = os.getenv("PASS")
        config['apiuser'] = os.getenv("APIUSER")
        config['apipass'] = os.getenv("APIPASS")
        f = open(f'{path}config.toml', 'w')
        tomlkit.dump(config, f)
        f.close()

    global_var.url = config['url']
    print(f'Using URL: {global_var.url}')
    global_var.dir = config['dir']
    print(f'Using outputs directory: {global_var.dir}')

    global_var.username = config['user']
    global_var.password = config['pass']
    global_var.api_user = config['apiuser']
    global_var.api_pass = config['apipass']

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
    with open(f'{path}messages.csv', encoding='UTF-8') as csv_file:
        message_data = list(csv.reader(csv_file, delimiter='|'))
        for row in message_data:
            global_var.wait_message.append(row[0])
    global_var.wait_message_count = len(global_var.wait_message) - 1

    # creating files if they don't exist
    if os.path.isfile(f'{path}stats.txt'):
        pass
    else:
        print(f'Uh oh, stats.txt missing. Creating a new one.')
        with open(f'{path}stats.txt', 'w') as f:
            f.write('0')

    header = ['display_name', 'model_full_name', 'activator_token']
    unset_model = ['Default', '', '']
    make_model_file = True
    replace_model_file = False
    # if models.csv exists and has data
    if os.path.isfile(f'{path}models.csv'):
        with open(f'{path}models.csv', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter="|")
            for i, row in enumerate(reader):
                # if header is missing columns, reformat the file
                if i == 0:
                    if len(row) < 3:
                        with open(f'{path}models.csv', 'r') as fp:
                            reader = csv.DictReader(fp, fieldnames=header, delimiter="|")
                            with open(f'{path}models2.csv', 'w', newline='') as fh:
                                writer = csv.DictWriter(fh, fieldnames=reader.fieldnames, delimiter="|")
                                writer.writeheader()
                                header = next(reader)
                                writer.writerows(reader)
                                replace_model_file = True
                # if first row has data, do nothing
                if i == 1:
                    make_model_file = False
        if replace_model_file:
            os.remove(f'{path}models.csv')
            os.rename(f'{path}models2.csv', f'{path}models.csv')
    # create/reformat model.csv if something is wrong
    if make_model_file:
        print(f'Uh oh, missing models.csv data. Creating a new one.')
        with open(f'{path}models.csv', 'w', newline='', encoding='utf-8') as f:
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
    # update global vars with stuff from config
    with open(f'{path}config.toml', 'r') as fileObj:
        content = fileObj.read()
        config = tomlkit.loads(content)

    # update these again in case changes were made
    global_var.url = config['url']
    global_var.dir = config['dir']
    global_var.username = config['user']
    global_var.password = config['pass']
    global_var.api_user = config['apiuser']
    global_var.api_pass = config['apipass']

    global_var.save_outputs = config['save_outputs']
    global_var.save_metadata = config['save_metadata']
    global_var.queue_limit = config['queue_limit']
    global_var.prompt_ban_list = [x for x in config['prompt_ban_list']]
    global_var.prompt_ignore_list = [x for x in config['prompt_ignore_list']]
    global_var.display_ignored_words = config['display_ignored_words']
    global_var.negative_prompt_prefix = [x for x in config['negative_prompt_prefix']]
    # slash command doesn't update this dynamically. Changes to size need a restart.
    global_var.size_range = range(192, config['max_size'] + 64, 64)

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
    r1 = s.get(global_var.url + "/sdapi/v1/samplers")
    r2 = s.get(global_var.url + "/sdapi/v1/prompt-styles")
    r3 = s.get(global_var.url + "/sdapi/v1/face-restorers")
    r4 = s.get(global_var.url + "/sdapi/v1/embeddings")
    r5 = s.get(global_var.url + "/sdapi/v1/hypernetworks")
    r6 = s.get(global_var.url + "/sdapi/v1/upscalers")
    r = s.get(global_var.url + "/sdapi/v1/sd-models")
    for s1 in r1.json():
        try:
            global_var.sampler_names.append(s1['name'])
        except(Exception,):
            # throw in last exception error for anything that wasn't caught earlier
            print("Can't connect to API for some reason!"
                  "Please check your .env URL or credentials.")
            os.system("pause")
    global_var.style_names['None'] = ''
    for s2 in r2.json():
        global_var.style_names[s2['name']] = s2['prompt'], s2['negative_prompt']
    for s3 in r3.json():
        global_var.facefix_models.append(s3['name'])
    for s4, shape in r4.json()['loaded'].items():
        if shape['shape'] == 768:
            global_var.embeddings_1.append(s4)
        if shape['shape'] == 1024:
            global_var.embeddings_2.append(s4)
    for s4, shape in r4.json()['skipped'].items():
        if shape['shape'] == 768:
            global_var.embeddings_1.append(s4)
        if shape['shape'] == 1024:
            global_var.embeddings_2.append(s4)
    for s5 in r5.json():
        global_var.hyper_names.append(s5['name'])
    for s6 in r6.json():
        global_var.upscaler_names.append(s6['name'])
    if 'SwinIR_4x' in global_var.upscaler_names:
        template['upscaler_1'] = 'SwinIR_4x'

    # create nested dict for models based on display_name in models.csv
    # model_info[0] = display name (top level)
    # model_info[1][0] = "title". this is sent to the API
    # model_info[1][1] = name of the model
    # model_info[1][2] = shorthash
    # model_info[1][3] = activator token
    with open(f'{path}models.csv', encoding='utf-8') as csv_file:
        model_data = list(csv.reader(csv_file, delimiter='|'))
        for row in model_data[1:]:
            for model in r.json():
                norm_csv_path = os.path.normpath(row[1])
                norm_api_path = os.path.normpath(model['filename'])
                if norm_csv_path.split(os.sep)[-1] == norm_api_path.split(os.sep)[-1] \
                        or norm_csv_path.replace(os.sep, '_') == model['model_name']:
                    global_var.model_info[row[0]] = model['title'], model['model_name'], model['hash'], row[2]
                    break
    # add "Default" if models.csv is on default, or if no model matches are found
    if not global_var.model_info:
        global_var.model_info[row[0]] = '', '', '', ''

    # iterate through config for anything unobtainable from API
    config_url = s.get(global_var.url + "/config")
    old_config = config_url.json()
    try:
        for c in old_config['components']:
            try:
                if c['props']:
                    if c['props']['elem_id'] == 'setting_sd_lora':
                        global_var.lora_names = c['props']['choices']
                    if c['props']['elem_id'] == 'txt2img_hr_upscaler':
                        global_var.hires_upscaler_names = c['props']['choices']
            except(Exception,):
                pass
    except(Exception,):
        print("Trouble accessing Web UI config! I can't pull the LoRAs or High-res upscaler lists!")
    # format some global lists, ensure default "None" options exist
    if 'None' not in global_var.facefix_models:
        global_var.facefix_models.insert(0, 'None')
    if 'None' not in global_var.hyper_names:
        global_var.hyper_names.insert(0, 'None')
    global_var.lora_names.remove('')
    global_var.lora_names.insert(0, 'None')
    global_var.hires_upscaler_names.insert(0, 'Disabled')
