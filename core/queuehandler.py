import asyncio
from threading import Thread


class GlobalQueue:
    dream_thread = Thread()
    event_loop = asyncio.get_event_loop()
    queue = []

class QueueObject:
    def __init__(self, ctx, prompt, negative_prompt, steps, height, width, guidance_scale, sampler, seed,
                 strength, init_image, copy_command, batch_count, facefix):
        self.ctx = ctx
        self.prompt = prompt
        self.negative_prompt = negative_prompt
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
        self.facefix = facefix

async def process_dream(self, queue_object: QueueObject):
    GlobalQueue.dream_thread = Thread(target=self.dream,
                               args=(GlobalQueue.event_loop, queue_object))
    GlobalQueue.dream_thread.start()