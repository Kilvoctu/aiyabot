# AIYA

A Discord bot interface for Stable Diffusion

<img src=https://raw.githubusercontent.com/Kilvoctu/kilvoctu.github.io/master/pics/preview.png  width=50% height=50%>

## Usage

To generate an image from text, use the /draw command and include your prompt as the query.

<img src=https://raw.githubusercontent.com/Kilvoctu/kilvoctu.github.io/master/pics/preview2.png>

### Currently supported options

- negative prompts
- swap model/checkpoint (_see Notes_)
- sampling steps
- height/width (up to 768)
- CFG scale
- sampling method
- seed
- img2img
- denoising strength
- batch count

#### Bonus features

- /settings command - set per-server defaults for the following (_also see Notes!_):
  - negative prompts
  - model/checkpoint
  - sampling steps / max steps
  - sampling method
  - batch count / max batch count
- /stats command - shows how many /draw commands have been used.
- /tips command - basic tips for writing prompts.

## Setup requirements

- Set up [AUTOMATIC1111's Stable Diffusion AI Web UI](https://github.com/AUTOMATIC1111/stable-diffusion-webui).
  - AIYA is currently tested on commit `9e22a357545c0395c81dd800c72fa18f350545ec` of the Web UI.
- Run the Web UI as local host with api (`COMMANDLINE_ARGS= --listen --api`).
- Clone this repo.
- Create a text file in your cloned repo called ".env", formatted like so:

```dotenv
# .env
TOKEN = put your bot token here
```

- Run the bot by running launch.bat

## Notes

- Ensure AIYA has `bot` and `application.commands` scopes when inviting to your Discord server, and intents are enabled.
- As /settings can be abused, consider reviewing who can access the command. This can be done through Apps -> Integrations in your Server Settings.
- React to generated images with ❌ to delete them.
- Optional .env variables you can set:

```dotenv
URL = set URL if yours is not default (http://127.0.0.1:7860)
DIR = set folder to save images, otherwise the default is \outputs

# only set USER and PASS if you use --share and --gradio-auth

USER = your username
PASS = your password
COPY = set to anything if you want the bot to output the command that was used to produce the image instead of the prompt
```
- On first launch, AIYA will generate a models.csv with a default dummy value. If you'd like to add more models/checkpoints, replace the default value and add lines following the format in the header. An example may look like:
```
display_name|model_full_name
SD 1.5|v1-5-pruned-emaonly.ckpt [81761151]
WD 1.3|wd-v1-3-float32.ckpt [4470c325]
```
- In the Web UI, there is a setting named "Checkpoints to cache in RAM". If you have enough RAM, this value can be increased to speed up swapping.
