# pylint: disable=c0111

import asyncio

from asynciojobs import Watch


async def co_print_sleep(watch, duration, message):
    # if start_watch was not called, show time with milliseconds
    if watch is None:
        Watch.print_wall_clock()
    else:
        watch.print_elapsed()
    print(message)
    await asyncio.sleep(duration)
    return f"duration={duration}"
