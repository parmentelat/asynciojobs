# -*- coding: utf-8 -*-

"""
This module defines `AbstractJob` that is the base class for all the jobs
in a Scheduler.

It also defines a couple of simple job classes.
"""

import sys
import asyncio

debug = False
# debug = True

# my first inclination had been to specialize asyncio.Task
# it does not work well though, because you want to model
# dependencies **before** anything starts, of course
# but in asyncio, creating a Task object implies scheduling that for execution

# so, let's have it the other way around
# what we need is a way to attach our own Job instance to the corresp.
# Task instance (and back) right after Task creation, so that
# (*) once asyncio.wait is done, we can easily find out
#     wich Jobs are done or pending
# (*) from one Job, easily know what its status is by
#     looking into its Task obj - if already scheduled

# Scheduler == graph
# Job == node


class AbstractJob:
    """AbstractJob is a virtual class:

    * it offers some very basic graph-related features to model requirements
      'a la' makefile
    * its subclasses are expected to implement a `co_run()`
      and a `co_shutdown()` methods that specifies
      the actual behaviour of the job, as coroutines

    It's mostly a companion class to the Scheduler class,
    that triggers these methods

    In addition, each job can be created with

    * boolean flag 'forever', if set, means the job is not returning
    at all and runs forever
    in this case Scheduler.orchestrate will not wait for that job,
    and will terminate it once all the regular i.e. not-forever jobs are done

    * an optional label - for convenience only

    -----

    As far as labelling, each subclass of `AbstractJob` implements a
    default labelling scheme, so it is not mandatory to set a specific
    label on each job instance, however it is sometimes useful.

    ------

    Besides, if a job instance has a `details()` method,
    then this is used to produce additional details for that job
    when running Scheduler.list(details=True)

    """

    def __init__(self, forever=False, label=None, critical=False,
                 required=None, scheduler=None):
        self.forever = forever
        self.critical = critical
        # access label through a method so we can invoke default_label() if
        # missing
        self._label = label
        # for convenience, one can mention only one AbstractJob
        self.required = set()
        self.requires(required)
        # convenience again
        if scheduler is not None:
            scheduler.add(self)
        # once submitted in the asyncio loop/scheduler,
        # `co_run()` gets embedded in a Task object,
        # that is our handle when talking to asyncio.wait
        self._task = None
        # this is updated by the Window class when the job makes it through
        self._running = False
        # ==== fields for our friend Scheduler all start with _s_
        # this is for graph browsing algos
        self._s_mark = None
        # the reverse of required
        self._s_successors = set()
        # if this is set by the scheduler, we use it for listing relationships
        self._s_label = None

    def label(self, use_s_label=False):
        """
        The logic for finding a job's label

        In terms of labelling, things have become a little tricky over
        time. When listing an instance of Scheduler, there are 2 ways
        we need to show a job

        * first there is a plain label, that may/should be set at creation time

        * second, when showing references (like the jobs that a given job
          requires), we show ids like '01' and similar.
        Except that, the job itself has no idea about that at first,
        it's the Scheduler instance that decides on that.

        So:

        * if use_s_label is True, looks in self._s_label that is expected
        to have been set by companion class Scheduler;
        if not set returns a warning msg '??'

        * otherwise, i.e. if use_s_label is False, looks for the label
          used at creation-time, and otherwise runs its class's
          `default_label()` method

        """
        if use_s_label:
            return self._s_label or '??'
        else:
            if self._label is not None:
                return str(self._label)
            elif hasattr(self, 'default_label'):
                return self.default_label()
            else:
                return "NOLABEL"

    def dot_label(self):
        """
        The method used by `Scheduler.export_as_dotfile`
        
        Because that goes in a dot file, it can have 
        "\n" inserted, that will render as newlines in the output png

        If this method is not defined on a concrete class, 
        just use label() instead
        """
        return self.label()

    ##########
    _has_support_for_unicode = None  # type: bool

    @classmethod
    def _detect_support_for_unicode(cls):
        if cls._has_support_for_unicode is None:
            try:
                cls._c_saltire.encode(sys.stdout.encoding)
                cls._has_support_for_unicode = True
            except UnicodeEncodeError:
                cls._has_support_for_unicode = False
        return cls._has_support_for_unicode

    # unicode version
    # _c_frowning_face = "\u2639" # ☹
    # _c_smiling_face  = "\u263b" # ☻
    _c_saltire = "\u2613"  # ☓
    _c_circle_arrow = "\u21ba"  # ↺
    _c_black_flag = "\u2691"  # ⚑
    _c_white_flag = "\u2690"  # ⚐
    _c_warning = "\u26a0"  # ⚠
    _c_black_star = "\u2605"  # ★
    _c_sun = "\u2609"  # ☉
    _c_infinity = "\u221e"  # ∞

    def _short_unicode(self):
        """
        a small (7 chars) badge that summarizes the job's internal attributes
        uses non-ASCII characters
        """
        # where is it in the lifecycle
        c_running = self._c_saltire if self.is_done() else \
            self._c_circle_arrow if self.is_running() else \
            self._c_black_flag if self.is_scheduled() else \
            self._c_white_flag
        # is it critical or not ?
        c_crit = self._c_warning if self.is_critical() else " "
        # has it raised an exception or not ?
        c_boom = self._c_black_star if self.raised_exception() \
            else self._c_sun if self.is_running() \
            else " "
        # is it going forever or not
        c_forever = self._c_infinity if self.forever else " "

        # add extra white space as unicode chars in terminal tend to be wider
        # than others
        return "{} {} {} {}".format(c_crit, c_boom, c_running, c_forever)

    def _short_ascii(self):
        """
        a small (7 chars) badge that summarizes the job's internal attributes
        uses ASCII-only characters
        """
        # where is it in the lifecycle
        c_running = "x" if self.is_done() else \
            "o" if self.is_running() else \
            "." if self.is_scheduled() else \
            ">"
        # is it critical or not ?
        c_crit = "!" if self.is_critical() else " "
        # has it raised an exception or not ?
        c_boom = ":(" if self.raised_exception() \
                 else ":)" if self.is_running() \
                 else "  "
        # is it going forever or not
        c_forever = "8" if self.forever else " "

        # add extra white space as unicode chars in terminal tend to be wider
        # than others
        return "{} {} {} {}".format(c_crit, c_boom, c_running, c_forever)

    def short(self):
        """
        return a 4 characters string (in fact 7 with interspaces)
        that summarizes the 4 dimensions of the job, that is

        * its point in the lifecycle: idle → scheduled → running → done

        * is it declared as forever

        * is it declared as critical

        * did it trigger an exception

        LifeCycle: see `is_done` for more details; in un-windowed schedulers,
        there is no distinction between scheduled and running.

        In windowed orchestrations, a job that is scheduled but not running
        is waiting for a slot in the global window.
        """
        if self._detect_support_for_unicode():
            return self._short_unicode()
        else:
            return self._short_ascii()

    def repr(self, show_requires=True, show_result_or_exception=True):
        """
        returns a string that describes this job instance,
        with details as specified
        """
        info = self.short()
        info += " <{} `{}`>".format(type(self).__name__, self.label())

        if show_result_or_exception:
            exception = self.raised_exception()
            if exception:
                critical_msg = "CRIT. EXC." if self.is_critical() \
                               else "exception"
                info += "!! {} => {}:{}!!"\
                        .format(critical_msg,
                                type(exception).__name__, exception)
            elif self.is_done():
                info += "[[ -> {}]]".format(self.result())

        # show dependencies in both directions
        if show_requires and self.required:
            info += " - requires {" + ", ".join(a.label(use_s_label=True)
                                                for a in self.required) + "}"
        return info

    def __repr__(self):
        return self.repr(show_requires=False)

    def requires(self, *requirements):
        """
        add requirements to a given job

        with `j{1,2,3}` being jobs or sequences, one can call:

        * j1.requires(None)

        * j1.requires([None])

        * j1.requires((None,))

        * j1.requires(j2)

        * j1.requires(j2, j3)

        * j1.requires([j2, j3])

        * j1.requires((j2, j3))

        * j1.requires(([j2], [[[j3]]]))
        """
        from .sequence import Sequence
        for requirement in requirements:
            if requirement is None:
                continue
            if isinstance(requirement, AbstractJob):
                self.required.add(requirement)
            elif isinstance(requirement, Sequence):
                if requirement.jobs:
                    self.required.add(requirement.jobs[-1])
            elif isinstance(requirement, (tuple, list)):
                for req in requirement:
                    self.requires(req)
            # not quite sure about what do to here in fact
            else:
                print("WARNING: fishy requirement in AbstractJob.requires")
                self.requires(list(requirement))

    def is_idle(self):
        """
        a boolean that is true if the job has not been scheduled
        already, which means that one of its requirements is not fulfilled.

        Implies `not is_scheduled()` and so a fortiori
        `not is_running` and `not is_done()`

        """
        return self._task is None

    def is_scheduled(self):
        """
        boolean that tells if the job has been scheduled;
        if True, the job's requirements are met and it has
        proceeded to the windowing system; equivalent to `not is_idle()`
        """
        return self._task is not None

    def is_running(self):
        """
        Once a job starts, it tries to get a slot in the windowing sytem.
        This method returns True if the job has received the green
        light from the windowing system. Implies `is_scheduled()`
        """
        return self._running

    def is_done(self):
        """
        a job lifecycle is idle → scheduled → running → done

        a boolean that tells if the job has completed.

        Implies `is_scheduled()` and `is_running()`
        """
        return self._task is not None \
            and self._task._state == asyncio.futures._FINISHED

    def raised_exception(self):
        """
        returns an exception if the job has completed by raising an exception,
        None otherwise
        """
        return self._task is not None and self._task._exception

    def is_critical(self):
        """
        a boolean that tells whether this job is a critical job or not
        """
        return self.critical

    def result(self):
        """
        when this job is completed and has not raised an exception, this
        method lets you retrieve the job's result. i.e. the value returned
        by its `co_run()` method
        """
        if not self.is_done():
            raise ValueError("job not finished")
        return self._task._result

    async def co_run(self):
        """
        abstract virtual - needs to be implemented
        """
        print("AbstractJob.co_run() needs to be implemented on class {}"
              .format(self.__class__.__name__))

    async def co_shutdown(self):
        """
        abstract virtual - needs to be implemented
        """
        print("AbstractJob.co_shutdown() needs to be implemented on class {}"
              .format(self.__class__.__name__))

    def standalone_run(self):
        """
        A convenience helper that just runs this one job on its own

        Mostly useful for debugging the internals of that job,
        e.g. for checking for gross mistakes and other exceptions
        """
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.co_run())

    # if subclass redefines details(), then that will show up in list()

####################


class Job(AbstractJob):

    """
    Most mundane form: built from a coroutine
    """

    def __init__(self, corun, coshutdown=None, *args, **kwds):
        """
        Create a job from a coroutine

        Example:
        async def aprint(message, delay):
            print(message)
            await asyncio.sleep(delay)

        j = Job(aprint("Welcome - idling for 3 seconds", 3))
        """
        self.corun = corun
        self.coshutdown = coshutdown
        super().__init__(*args, **kwds)

    async def co_run(self):
        result = await self.corun
        return result

    async def co_shutdown(self):
        if self.coshutdown:
            result = await self.coshutdown
            return result

    def details(self):
        return repr(self.corun)

####################


class PrintJob(AbstractJob):
    """
    A job that just  does print on messages,
    and optionnally sleeps for some time

    sleep is an optional float that tells how long
    to sleep after the messages get printed

    banner is an optional separation line,
    like 40*'='; it won't make it into details()
    """

    def __init__(self, *messages, sleep=None, banner=None,
                 # these are for AbstractJob
                 scheduler=None,
                 label=None, required=None):
        self.messages = messages
        self.sleep = sleep
        self.banner = banner
        super().__init__(label=label, required=required, scheduler=scheduler)

    async def co_run(self):
        try:
            if self.banner:
                print(self.banner + " ", end="")
            print(*self.messages)
            if self.sleep:
                print("Sleeping for {}s".format(self.sleep))
                await asyncio.sleep(self.sleep)
        except Exception:
            import traceback
            traceback.print_exc()

    async def co_shutdown(self):
        pass

    def details(self):
        result = ""
        if self.sleep:
            result += "[+ sleep {}s] ".format(self.sleep)
        result += "msg= "
        result += self.messages[0]
        result += "..." if len(self.messages) > 1 else ""
        return result

    def default_label(self):
        return self.details()
