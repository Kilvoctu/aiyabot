import asyncio
from threading import Thread


#the queue object for txt2image and img2img
class DrawObject:
    def __init__(self, ctx, prompt, negative_prompt, data_model, steps, height, width, guidance_scale, sampler, seed,
                 strength, init_image, copy_command, batch_count, style, facefix, simple_prompt):
        self.ctx = ctx
        self.prompt = prompt
        self.negative_prompt = negative_prompt
        self.data_model = data_model
        self.steps = steps
        self.height = height
        self.width = width
        self.guidance_scale = guidance_scale
        self.sampler = sampler
        self.seed = seed
        self.strength = strength
        self.init_image = init_image
        self.copy_command = copy_command
        self.batch_count = batch_count
        self.style = style
        self.facefix = facefix
        self.simple_prompt = simple_prompt

#any command that needs to wait on processing should use the dream thread
class GlobalQueue:
    dream_thread = Thread()
    event_loop = asyncio.get_event_loop()
    queue = []
async def process_dream(self, queue_object):
    GlobalQueue.dream_thread = Thread(target=self.dream,
                               args=(GlobalQueue.event_loop, queue_object))
    GlobalQueue.dream_thread.start()