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
- Run the Web UI as local host (`COMMANDLINE_ARGS= --listen`).
- Clone this repo, then install dependencies in `requirements.txt` in your Python environment.
- Create a text file in your cloned repo called ".env", containing `TOKEN = [your bot token]`
- Run the bot by typing "python bot.py" in the repository directory.
- If you have a user name and password, inside .env add `USER = username` and `PASS = password` as seperate lines
- Set the URL/IP (required) with `URL = http://127.0.0.1` (Another example: `URL = https://redacted.gradio.app`)

Note: Ensure your bot has `bot` and `application.commands` scopes when inviting to your Discord server, and intents are enabled.

This bot is heavily based on:
https://github.com/harubaru/discord-stable-diffusion
with interfacing from:
https://github.com/gingivere0/dalebot
