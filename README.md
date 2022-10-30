# AIYA
A Discord bot interface for Stable Diffusion

<img src=https://raw.githubusercontent.com/Kilvoctu/kilvoctu.github.io/master/pics/preview.png  width=50% height=50%>

### Usage
To generate an image from text, use the /draw command and include your prompt as the query.

<img src=https://raw.githubusercontent.com/Kilvoctu/kilvoctu.github.io/master/pics/preview2.png>

#### Currently supported options
- negative prompts
- sampling steps
- height/width (up to 768)
- CFG scale
- sampling method
- seed
- img2img
- denoising strength

##### Bonus features
- /settings command - set per-server defaults for negative prompts, sampling steps, max steps, sampling method (_see Notes!_).
- /stats command - shows how many /draw commands have been used.
- /tips command - basic tips for writing prompts.

### Setup requirements
- Set up [AUTOMATIC1111's Stable Diffusion AI Web UI](https://github.com/AUTOMATIC1111/stable-diffusion-webui).
  - AIYA is currently tested on commit `36c21723b52f17d1de5ff13a50c326c7a0a95285` of the Web UI. 
- Run the Web UI as local host with api (`COMMANDLINE_ARGS= --listen --api`).
- Clone this repo.
- Create a text file in your cloned repo called ".env", formatted like so:
```
# .env
TOKEN = put your bot token here
```
- Run the bot by running launch.bat

#### Notes
- Ensure your bot has `bot` and `application.commands` scopes when inviting to your Discord server, and intents are enabled.
- As /settings can be abused, consider reviewing who can access the command. This can be done through Apps -> Integrations in your Server Settings.
- React to generated images with ❌ to delete them.
- Optional .env variables you can set:
```
URL = set URL if yours is not default (http://127.0.0.1:7860) 
DIR = set folder to save images, otherwise the default is \outputs
# only set USER and PASS if you use --share and --gradio-auth
USER = your username
PASS = your password
```