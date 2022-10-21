import os
import requests
import json
from enum import Enum
import platform
from core import stablecog
responsestr = {}


# only need to get the schema once
def setup():
    port = os.getenv('port')
    global responsestr
    formdata = {
        'username': os.getenv('USERNAME'),
        'password': os.getenv('PWD')
    };

    try:
        response_format = requests.get(f"http://127.0.0.1:{port}/config")
    except:
        requests.post(f'http://127.0.0.1:{port}', data=formdata)
        response_format = requests.get(f"http://127.0.0.1:{port}/config")
        
    responsestr = response_format.json()


# prob don't need to do this lmao
class PayloadFormat(Enum):
    TXT2IMG = 0
    IMG2IMG = 1
    UPSCALE = 2


def do_format(StableCog, payload_format: PayloadFormat):

    # dependencies have ids that point to components. these components (usually) have a label (like "Sampling steps")
    # and a default value (like "20"). we find the dependency we want (key "js" must have value "submit" for txt2img,
    # "submit_img2img" for img2img, and "get_extras_tab_index" for upscale).
    # then iterate through the ids in that dependency and match them with the corresponding id in the components.
    # store the label:value pairs in txt2imgjson.
    # example:
    # {"components":[
    #               { "id": 6,
    #                 "props":{
    #                           "label":"Prompt",
    #                           "value":""
    #                          }
    #                 }, etc ],
    #   "dependencies":[
    #                  { "inputs":{
    #                       6,etc
    #                              },
    #                     "js":"submit", etc
    #                   }]
    # }
    #
    # dict["dependencies"]["input"][0] equals 6 which is the id of the component for Prompt
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
        # later on, json payload uses the function index to determine what parameters to accept.
        # function index is the position in dependencies in the schema that the function appears,
        # so txt2img is the 13th function (in this version, could change in the future)
        if dependenciesjson[dep]["js"] == "submit" and txt2img_fn_index == 0:
            # not sure if it's different on linux but this is a guess
            txt2img_fn_index = dep
        elif dependenciesjson[dep]["js"] == "submit_img2img" and img2img_fn_index == 0:
            img2img_fn_index = dep
        elif dependenciesjson[dep]["js"] == "get_extras_tab_index" and upscale_fn_index == 0:
            upscale_fn_index = dep

    for identifier in dependencylist:
        for component in componentsjson:
            if identifier == component["id"]:
                # one of the labels is empty
                if component["props"].get("name") == "label":
                    labelvaluetuplelist.append(("", 0))
                # img2img has a duplicate label that messes things up
                elif component["props"].get("label") == "Image for img2img" and component["props"].get("elem_id") != "img2img_image":
                    labelvaluetuplelist.append(("", None))
                # upscale has a duplicate label that messes things up
                elif component["props"].get("label") == "Source" and component["props"].get("elem_id") == "pnginf_image":
                    labelvaluetuplelist.append(("", None))
                # only gonna use the one upscaler, idc
                elif component["props"].get("label") == "Upscaler 1":
                    labelvaluetuplelist.append((component["props"].get("label"), "ESRGAN_4x"))
                # slightly changing the img2img Script label so it doesn't clash with another label of the same name
                elif component["props"].get("label") == "Script" and len(component["props"].get("choices")) > 3:
                    labelvaluetuplelist.append(("Scripts", "None"))
                elif component["props"].get("label") == "Sampling method":
                    labelvaluetuplelist.append(("Sampling method", "Euler a"))
                    StableCog.sampling_methods = component["props"].get("choices")
                # these are the labels and values we actually care about
                else:
                    labelvaluetuplelist.append((component["props"].get("label"), component["props"].get("value")))
                break

    # iterate through txt2imgjson, find a label you're looking for, and store the index for later use by StableCog
    for i in range(0, len(labelvaluetuplelist)):
        if labelvaluetuplelist[i][0] == "Prompt":
            StableCog.prompt_ind = i
        elif labelvaluetuplelist[i][0] == "Negative prompt":
            StableCog.exclude_ind = i
        elif labelvaluetuplelist[i][0] == "Sampling Steps":
            StableCog.sample_ind = i
        elif labelvaluetuplelist[i][0] == "Batch count":
            StableCog.num_ind = i
        elif labelvaluetuplelist[i][0] == "CFG Scale":
            StableCog.conform_ind = i
        elif labelvaluetuplelist[i][0] == "Seed":
            StableCog.seed_ind = i
        elif labelvaluetuplelist[i][0] == "Height":
            StableCog.resy_ind = i
        elif labelvaluetuplelist[i][0] == "Width":
            StableCog.resx_ind = i
        elif labelvaluetuplelist[i][0] == "Denoising strength":
            StableCog.denoise_ind = i
        elif labelvaluetuplelist[i][0] == "Image for img2img":
            StableCog.data_ind = i
        elif labelvaluetuplelist[i][0] == "Source":
            StableCog.data_ind = i
        elif labelvaluetuplelist[i][0] == "Resize":
            StableCog.resize_ind = i
        elif labelvaluetuplelist[i][0] == "Scripts":
            StableCog.script_ind = i
        elif labelvaluetuplelist[i][0] == "Loops":
            StableCog.loop_ind = i
        elif labelvaluetuplelist[i][0] == "Sampling method":
            StableCog.sampling_methods_ind = i

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
