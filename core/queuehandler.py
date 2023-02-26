import asyncio
from threading import Thread


# the queue object for txt2image and img2img
class DrawObject:
    def __init__(self, cog, ctx, simple_prompt, prompt, negative_prompt, data_model, steps, width, height,
                 guidance_scale, sampler, seed, strength, init_image, batch, style, facefix, highres_fix,
                 clip_skip, hypernet, lora, view):
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
        self.style = style
        self.facefix = facefix
        self.highres_fix = highres_fix
        self.clip_skip = clip_skip
        self.hypernet = hypernet
        self.lora = lora
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


# the queue object for posting to Discord
class PostObject:
    def __init__(self, cog, ctx, content, file, files, embed, view):
        self.cog = cog
        self.ctx = ctx
        self.content = content
        self.file = file
        self.files = files
        self.embed = embed
        self.view = view


# any command that needs to wait on processing should use the dream thread
class GlobalQueue:
    dream_thread = Thread()
    post_event_loop = asyncio.get_event_loop()
    queue: list[DrawObject | UpscaleObject | IdentifyObject] = []

    post_thread = Thread()
    event_loop = asyncio.get_event_loop()
    post_queue: list[PostObject] = []


def process_queue():
    def start(target_queue: list[DrawObject | UpscaleObject | IdentifyObject]):
        queue_object = target_queue.pop(0)
        queue_object.cog.dream(GlobalQueue.event_loop, queue_object)

    if GlobalQueue.queue:
        start(GlobalQueue.queue)


async def process_dream(self, queue_object: DrawObject | UpscaleObject | IdentifyObject):
    GlobalQueue.dream_thread = Thread(target=self.dream, args=(GlobalQueue.event_loop, queue_object))
    GlobalQueue.dream_thread.start()


def process_post(self, queue_object: PostObject):
    if GlobalQueue.post_thread.is_alive():
        GlobalQueue.post_queue.append(queue_object)
    else:
        GlobalQueue.post_thread = Thread(target=self.post, args=(GlobalQueue.post_event_loop, queue_object))
        GlobalQueue.post_thread.start()
