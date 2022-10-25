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

### Setup requirements
- Set up [AUTOMATIC1111's Stable Diffusion AI Web UI](https://github.com/AUTOMATIC1111/stable-diffusion-webui).
- Run the Web UI as local host with api (`COMMANDLINE_ARGS= --listen --api`).
- Clone this repo.
- Create a text file in your cloned repo called ".env", formatted like so:
```
TOKEN = put your bot token here
URL = WEB UI's full URL (default = http://127.0.0.1:7860)
DIR = folder to save images (default = outputs)
# only set USER and PASS if you use --share and --gradio-auth
USER = your username
PASS = your password
```
- Run the bot by running launch.bat

Note: Ensure your bot has `bot` and `application.commands` scopes when inviting to your Discord server, and intents are enabled.
