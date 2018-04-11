"""
Implementation for the Window class, for schedulers
with a limited number of running jobs
"""

import asyncio


class Window:
    """
    The window class implements the logic that allows to
    throttle a scheduler instance to run only a limited number
    of simultaneous jobs.

    Users are not expected to create such objects by themselves,
    the scheduler takes care of that when needed
    """

    def __init__(self, jobs_window, loop):
        # jobs_window needs to be an integer
        if jobs_window is None:
            jobs_window = 0
        self.jobs_window = jobs_window
        self.loop = loop
        self.queue = asyncio.Queue(maxsize=jobs_window, loop=loop)

    def run_job(self, job):
        """
        a decorator around a coroutine, that will first get a slot in the queue

        REMEMBER that this object will need to be CALLED to become
        a future itself
        """
        async def wrapped():                            # pylint: disable=C0111
            # put anything to take a slot in the queue
            await self.queue.put(1)
            job._running = True                         # pylint: disable=w0212
            value = await job.co_run()
            # release slot in the queue
            await self.queue.get()
            # return the right thing
            return value
        return wrapped

    # for debugging
    async def monitor(self, period=3):
        """
        a coroutine that cyclically shows the status of the queue
        until it gets empty
        """
        await asyncio.sleep(period)
        while not self.queue.empty():
            print("queue has {}/{} elements busy"
                  .format(self.queue.qsize(), self.jobs_window))
            await asyncio.sleep(period)
