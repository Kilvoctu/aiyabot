import aiohttp
import asyncio
import discord
import random
from threading import Thread


# the queue object for txt2image and img2img
class DrawObject:
    def __init__(self, cog, ctx, simple_prompt, prompt, negative_prompt, data_model, steps, width, height,
                 guidance_scale, sampler, seed, strength, init_image, batch, styles, facefix, highres_fix,
                 clip_skip, extra_net, epoch_time, view):
        self.cog = cog
        self.ctx = ctx
        self.simple_prompt = simple_prompt
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.data_model = data_model
        self.steps = steps
        self.width = width
        self.height = height
        self.guidance_scale = guidance_scale
        self.sampler = sampler
        self.seed = seed
        self.strength = strength
        self.init_image = init_image
        self.batch = batch
        self.styles = styles
        self.facefix = facefix
        self.highres_fix = highres_fix
        self.clip_skip = clip_skip
        self.extra_net = extra_net
        self.epoch_time = epoch_time
        self.view = view


# the queue object for extras - upscale
class UpscaleObject:
    def __init__(self, cog, ctx, resize, init_image, upscaler_1, upscaler_2, upscaler_2_strength, gfpgan, codeformer,
                 upscale_first, view):
        self.cog = cog
        self.ctx = ctx
        self.resize = resize
        self.init_image = init_image
        self.upscaler_1 = upscaler_1
        self.upscaler_2 = upscaler_2
        self.upscaler_2_strength = upscaler_2_strength
        self.gfpgan = gfpgan
        self.codeformer = codeformer
        self.upscale_first = upscale_first
        self.view = view


# the queue object for identify (interrogate)
class IdentifyObject:
    def __init__(self, cog, ctx, init_image, phrasing, view):
        self.cog = cog
        self.ctx = ctx
        self.init_image = init_image
        self.phrasing = phrasing
        self.view = view


# the queue object for generate
class GenerateObject:
    def __init__(self, cog, ctx, prompt):
        self.cog = cog
        self.ctx = ctx
        self.prompt = prompt


# the queue object for posting to Discord
class PostObject:
    def __init__(self, cog, ctx, content, file, embed, view):
        self.cog = cog
        self.ctx = ctx
        self.content = content
        self.file = file
        self.embed = embed
        self.view = view


# any command that needs to wait on processing should use the dream thread
class GlobalQueue:
    dream_thread = Thread()
    post_event_loop = asyncio.get_event_loop()
    queue: list[DrawObject | UpscaleObject | IdentifyObject] = []
    
    # new generate Queue
    generate_queue: list[GenerateObject] = []
    generate_thread = Thread()
    
    post_thread = Thread()
    event_loop = asyncio.get_event_loop()
    post_queue: list[PostObject] = []
    
    def get_queue_sizes():
        return {
            "General Queue": len(GlobalQueue.queue),
            "/Generate Queue": len(GlobalQueue.generate_queue)
        }
        
    @staticmethod
    async def update_progress_message(queue_object):
        ctx = queue_object.ctx
        prompt = queue_object.prompt
        
        # check for an existing progression message, if yes delete the previous one
        async for old_msg in ctx.channel.history(limit=10):
            if old_msg.embeds:
                if old_msg.embeds[0].title == "Running Job Progress":
                    await old_msg.delete()
        
        # send first message to discord, Initialization
        embed = discord.Embed(title="Initialization...", color=discord.Color.blue())
        progress_msg = await ctx.send(embed=embed)
        
        # progress loop
        null_counter = 0
        while not queue_object.is_done:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://127.0.0.1:7860/sdapi/v1/progress?skip_current_image=false") as response:
                    data = await response.json()
                    
                    progress = round(data["progress"] * 100)
                    eta_relative = round(data["eta_relative"])
                    short_prompt = queue_object.prompt[:125] + "..." if len(prompt) > 125 else prompt
                    job = data['state']['job']
                    sampling_step = data['state']['sampling_step']
                    sampling_steps = data['state']['sampling_steps']
                    queue_size = len(GlobalQueue.queue)
                    
                    # adjust job output
                    if job == "scripts_txt2img":
                        job = "Batch 1 out of 1"
                    elif job.startswith("task"):
                        job = "Job running locally by the owner"

                    # check for walking-dead function
                    if progress == 0:
                        null_counter += 1
                    else:
                        null_counter = 0
                    if null_counter >= 12:
                        await progress_msg.delete()
                        return
                    
                    # check recent messages and Spam the bottom, like pinned
                    latest_message = await ctx.channel.history(limit=1).flatten()
                    latest_message = latest_message[0] if latest_message else None
                    
                    if latest_message and latest_message.id != progress_msg.id:
                        await progress_msg.delete()
                        progress_msg = await ctx.send(embed=embed)
                    
                    # message update
                    random_color = discord.Color.from_rgb(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                    embed = discord.Embed(title=f"Running Job Progress", description=f"**Prompt**: {short_prompt}\n**Progress**: {progress}%\n**Remaining**: {eta_relative} seconds\n**Current Step**: {sampling_step}/{sampling_steps}  -  {job}\n**Queued Jobs:**: {queue_size}", color=random_color)
                    await progress_msg.edit(embed=embed)
                    
                    await asyncio.sleep(0.5)
                    
        # done, delete
        await progress_msg.delete()

    def process_queue():
        def start(target_queue: list[DrawObject | UpscaleObject | IdentifyObject | GenerateObject]):
            queue_object = target_queue.pop(0)
            queue_object.cog.dream(GlobalQueue.event_loop, queue_object)

        if GlobalQueue.queue:
            start(GlobalQueue.queue)


async def process_dream(self, queue_object: DrawObject | UpscaleObject | IdentifyObject):
    GlobalQueue.dream_thread = Thread(target=self.dream, args=(GlobalQueue.event_loop, queue_object))
    GlobalQueue.dream_thread.start()

async def process_generate(self, queue_object: GenerateObject):
    GlobalQueue.generate_thread = Thread(target=self.dream, args=(GlobalQueue.event_loop, queue_object))
    GlobalQueue.generate_thread.start()

def process_post(self, queue_object: PostObject):
    if GlobalQueue.post_thread.is_alive():
        GlobalQueue.post_queue.append(queue_object)
    else:
        GlobalQueue.post_thread = Thread(target=self.post, args=(GlobalQueue.post_event_loop, queue_object))
        GlobalQueue.post_thread.start()
