import asyncio


class Window:

    def __init__(self, jobs_window, loop):
        # jobs_window needs to be an integer
        if jobs_window is None:
            jobs_window = 0
        self.jobs_window = jobs_window
        self.loop = loop
        self.queue = asyncio.Queue(maxsize=jobs_window, loop=loop)

    # a decorator around a coroutine,
    # that will first get a slot in the queue
    #
    # REMEMBER that this object will need to be CALLED to become
    # a future itself
    #
    def run_job(self, job):
        async def wrapped():
            # put anything to take a slot in the queue
            await self.queue.put(1)
            job._running = True
            value = await job.co_run()
            # release slot in the queue
            await self.queue.get()
            # return the right thing
            return value
        return wrapped

    # for debugging
    async def monitor(self, period=3):
        await asyncio.sleep(period)
        while not self.queue.empty():
            print("queue has {}/{} elements busy"
                  .format(queue.qsize(), self.jobs_window))
            await asyncio.sleep(period)
