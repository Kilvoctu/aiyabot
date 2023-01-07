# AIYA

A Discord bot interface for Stable Diffusion

<img src=https://raw.githubusercontent.com/Kilvoctu/kilvoctu.github.io/master/pics/preview.png  width=50% height=50%>

## Setup requirements

- Set up [AUTOMATIC1111's Stable Diffusion AI Web UI](https://github.com/AUTOMATIC1111/stable-diffusion-webui).
  - AIYA is currently tested on commit `5f4fa942b8ec3ed3b15a352903489d6f9e6eb46e` of the Web UI.
- Run the Web UI as local host with api (`COMMANDLINE_ARGS= --listen --api`).
- Clone this repo.
- Create a text file in your cloned repo called ".env", formatted like so:
```dotenv
# .env
TOKEN = put your bot token here
```
- Run AIYA by running launch.bat (or launch.sh for Linux)

## Usage

To generate an image from text, use the /draw command and include your prompt as the query.

<img src=https://raw.githubusercontent.com/Kilvoctu/kilvoctu.github.io/master/pics/preview2.png>

### Currently supported options

- negative prompts
- swap model/checkpoint (_[see wiki](https://github.com/Kilvoctu/aiyabot/wiki/Model-swapping)_)
- sampling steps
- width/height (up to 1024)
- CFG scale
- sampling method
- seed
- img2img
- denoising strength
- batch count
- Web UI styles
- face restoration
- high-res fix
- CLIP skip
- hypernetworks

#### Bonus features

- /settings command - set per-server defaults for the following (_see Notes!_):
  - negative prompts
  - model/checkpoint
  - sampling steps / max steps
  - sampling method
  - batch count / max batch count
  - CLIP skip
  - hypernetworks
  - refresh (update AIYA's options with any changes from Web UI)
- /identify command - create a caption for your image.
- /stats command - shows how many /draw commands have been used.
- /tips command - basic tips for writing prompts and other info.
- /upscale command - resize your image.
- buttons - certain outputs will contain buttons.
  - 🖋 - edit prompt, then generate a new image with same parameters.
  - 🎲 - randomize seed, then generate a new image with same parameters.
  - 📋 - view the generated image's information.
  - ❌ - deletes the generated image.

## Notes

- Ensure AIYA has `bot` and `application.commands` scopes when inviting to your Discord server, and intents are enabled.
- As /settings can be abused, consider reviewing who can access the command. This can be done through Apps -> Integrations in your Server Settings.
- [See wiki for optional .env variables you can set.](https://github.com/Kilvoctu/aiyabot/wiki/.env-Settings)
- [See wiki for notes on swapping models.](https://github.com/Kilvoctu/aiyabot/wiki/Model-swapping)


## Credits

AIYA only exists thanks to these awesome people:
- AUTOMATIC1111, and all the contributors to the Web UI repo.
  - https://github.com/AUTOMATIC1111/stable-diffusion-webui
- harubaru, my entryway into Stable Diffusion (with Waifu Diffusion) and foundation for the AIYA Discord bot.
  - https://github.com/harubaru/waifu-diffusion
  - https://github.com/harubaru/discord-stable-diffusion
- gingivere0, for PayloadFormatter class for the original API. Without that, I'd have given up from the start. Also has a great Discord bot as a no-slash-command alternative.
  - https://github.com/gingivere0/dalebot
- You, for using AIYA and contributing with PRs, bug reports, feedback, and more!