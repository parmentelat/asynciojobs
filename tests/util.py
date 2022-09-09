# pylint: disable=c0111

import asyncio

from pathlib import Path

from asynciojobs import Watch, Job, Scheduler


async def co_print_sleep(watch, duration, message):
    # if start_watch was not called, show time with milliseconds
    if watch is None:
        Watch.print_wall_clock()
    else:
        watch.print_elapsed()
    print(message)
    await asyncio.sleep(duration)
    return f"duration={duration}"


# def produce_png(scheduler, name):
#     produce_graphic(scheduler, name, format="png")

def produce_svg(scheduler, name):
    produce_graphic(scheduler, name, format="svg")

def produce_graphic(scheduler, name, format):

    tests_dir = Path('tests')
    if tests_dir.exists():
        actual_name = tests_dir / name
    else:
        actual_name = Path(name)

    scheduler.export_as_graphic(actual_name, format)
    print(f"graphic files produced in {actual_name}.{{dot,{format}}}")


def diamond_from_jobs(watch, j1, j2, j3, j4, scheduler_class=Scheduler):
    diamond = scheduler_class(watch=watch)
    diamond.add(j1)
    diamond.add(j2)
    diamond.add(j3)
    diamond.add(j4)
    j2.requires(j1)
    j3.requires(j1)
    j4.requires(j2)
    j4.requires(j3)
    return diamond

def diamond_scheduler(watch, duration, msg, scheduler_class=Scheduler):
    """
    create a small diamond scheduler
    total duration = duration
    """
    top = Job(co_print_sleep(watch, duration/4, f"top {msg}"),
              label=f"top {msg}1")
    left = Job(co_print_sleep(watch, duration/2, f"left {msg}"),
               label=f"left {msg}")
    right = Job(co_print_sleep(watch, duration/2, f"right {msg}", ),
                label=f"right {msg}")
    bottom = Job(co_print_sleep(watch, duration / 4, f"bottom {msg}"),
                label=f"bottom {msg}")
    return diamond_from_jobs(watch, top, left, right, bottom)


def diamond_scheduler(watch, duration, msg, scheduler_class=Scheduler):
    """
    create a small diamond scheduler
    total duration = duration
    """
    diamond = scheduler_class(watch=watch)
    top = Job(co_print_sleep(watch, duration/4, f"top {msg}"),
              label=f"top {msg}1",
              scheduler=diamond)
    left = Job(co_print_sleep(watch, duration/2, f"left {msg}"),
               label=f"left {msg}",
               required=top, scheduler=diamond)
    right = Job(co_print_sleep(watch, duration/2, f"right {msg}", ),
                label=f"right {msg}",
                required=top, scheduler=diamond)
    Job(co_print_sleep(watch, duration / 4, f"bottom {msg}"),
        label=f"bottom {msg}",
        required=(left, right), scheduler=diamond)
    return diamond


def pipes(watch, duration, msg, *,
          nb_pipes=2, scheduler_class=Scheduler):
    """
    2 pipes of 2 jobs each
    total duration = duration
    """
    sched = scheduler_class(watch=watch)
    for i in range(1, nb_pipes+1):
        top = Job(co_print_sleep(watch, duration/2, f"top{i} {msg}"),
                  label=f"top{i} {msg}")
        bottom = Job(co_print_sleep(watch, duration/2, f"bot{i} {msg}"),
                     label=f"bot{i} {msg}",
                     required=top)
        sched.update({top, bottom})
    return sched
