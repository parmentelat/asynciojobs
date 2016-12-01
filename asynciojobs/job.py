# -*- coding: utf-8 -*-
import sys
import asyncio

debug = False
#debug = True

# my first inclination had been to specialize asyncio.Task
# it does not work well though, because you want to model
# dependencies **before** anything starts, of course
# but in asyncio, creating a Task object implies scheduling that for execution

# so, let's have it the other way around
# what we need is a way to attach our own Job instances to the Task (and back)
# classes right after Task creation, so that
# (*) once asyncio.wait is done, we can easily find out wich Jobs are done or pending
# (*) from one Job, easily know what its status is by lloing into its Task obj
#     (if already started)

# Scheduler == graph
# Job == node

"""
This module defines `AbstractJob` that is the base class for all the jobs in a Scheduler.

It also defines a couple of simple job classes.
"""
 

class AbstractJob:
    """
    AbstractJob is a virtual class:

    (*) it offers some very basic graph-related features to model requirements
        'a la' makefile
    (*) its subclasses are expected to implement a `co_run()` and a `co_shutdown()` methods
        that specifies the actual behaviour of the job, as coroutines

    It's mostly a companion class to the Scheduler class, that triggers these methods

    In addition, each job can be created with 
    (*) boolean flag 'forever', if set, means the job is not returning at all and runs forever
    in this case Scheduler.orchestrate will not wait for that job, and will terminate it once all
    the regular i.e. not-forever jobs are done
    (*) an optional label - for convenience only

    -----

    As far as labelling, things have become a little tricky

    When listing an instance of Scheduler, there are 2 ways we need to show a job

    * first there is a plain label, that may/should be set at creation time

    * second, when showing references (like the jobs that a given job requires), 
    we show ids like '01' and similar.
    Except that, the job itself has no idea about that at first, 
    it's the Scheduler instance that decides on that

    ------

    Besides, if a job instance has a `details()` method, then this is used to produce 
    additional details for that job when running Scheduler.list(details=True)


    """

    def __init__(self, forever=False, label=None, critical=False, required=None,
                 scheduler = None):
        self.forever = forever
        self.critical = critical
        # access label through a method so we can invoke default_label() if missing
        self._label = label
        # for convenience, one can mention only one AbstractJob
        self.required = set()
        self.requires(required)
        # convenience again
        if scheduler is not None:
            scheduler.add(self)
        # once submitted in the asyncio loop/scheduler, the `co_run()` gets embedded in a 
        # Task object, that is our handle when talking to asyncio.wait
        self._task = None
        # ==== fields for our friend Scheduler all start with _s_
        # this is for graph browsing algos
        self._s_mark = None
        # the reverse of required
        self._s_successors = set()
        # if this is set by the scheduler, we use it for listing relationships
        self._s_label = None

    def label(self, use_s_label=False):
        """
        Implements the logic for finding a job's label
        * if use_s_label is set, looks in self._s_label that is expected to have been set by
        companion class Scheduler; if not set returns a warning msg 'XXXX'
        * otherwise, looks for the label  used at creation-time, and otherwise
        runs its class's `default_label()` method
        """
        if use_s_label:
            return self._s_label or 'XXXX'
        else:
            if self._label is not None:
                return str(self._label)
            elif hasattr(self, 'default_label'):
                return self.default_label()
            else:
                return "NOLABEL"

    ##########
    _has_support_for_unicode = None

    @classmethod
    def _detect_support_for_unicode(klass):
        if klass._has_support_for_unicode is None:
            try:
                klass._c_saltire.encode(sys.stdout.encoding)
                klass._has_support_for_unicode = True
            except UnicodeEncodeError as e:
                klass._has_support_for_unicode = False
        return klass._has_support_for_unicode
            

    ########## unicode version
    #_c_frowning_face = "\u2639" # ☹
    #_c_smiling_face  = "\u263b" # ☻
    _c_saltire       = "\u2613" # ☓
    _c_circle_arrow  = "\u21ba" # ↺
    _c_flag          = "\u2690" # ⚐
    _c_warning       = "\u26a0" # ⚠
    _c_black_star    = "\u2605" # ★
    _c_sun           = "\u2609" # ☉
    _c_infinity      = "\u221e" # ∞
    

    def _short_unicode(self):
        """
        a small (7 chars) badge that summarizes the job's internal attributes
        uses non-ASCII characters
        """
        # is it done, or ongoing, or not yet started ?
        c_running = self._c_saltire if self.is_done() else \
                 self._c_circle_arrow if self.is_started() else \
                 self._c_flag
        # is it critical or not ?
        c_crit = self._c_warning if self.is_critical() else " "
        # has it raised an exception or not ?
        c_boom = self._c_black_star if self.raised_exception() \
                 else self._c_sun if self.is_started() \
                 else " "
        # is it going forever or not
        c_forever = self._c_infinity if self.forever else " "

        # add extra white space as unicode chars in terminal tend to be wider than others
        return "{} {} {} {}".format(c_crit, c_boom, c_running, c_forever)
        
    def _short_ascii(self):
        """
        a small (7 chars) badge that summarizes the job's internal attributes
        uses ASCII-only characters
        """
        # is it done, or ongoing, or not yet started ?
        c_running = "x" if self.is_done() else \
                 "o" if self.is_started() else \
                 ">"
        # is it critical or not ?
        c_crit = "!" if self.is_critical() else " "
        # has it raised an exception or not ?
        c_boom = ":(" if self.raised_exception() \
                 else ":)" if self.is_started() \
                 else "  "
        # is it going forever or not
        c_forever = "8" if self.forever else " "

        # add extra white space as unicode chars in terminal tend to be wider than others
        return "{} {} {} {}".format(c_crit, c_boom, c_running, c_forever)

    def short(self):
        """
        return a 4 characters string (in fact 7 with interspaces)
        that summarizes the 4 dimensions of the job, that is
        (*) is it done/started/idle
        (*) is it declared as forever
        (*) is it critical
        (*) did it trigger an exception
        """
        if self._detect_support_for_unicode():
            return self._short_unicode()
        else:
            return self._short_ascii()
    
    def repr(self, show_requires=True, show_result_or_exception=True):
        """
        returns a string that describes this job instance, with details as specified
        """
        info = self.short()
        info += " <{} `{}`>".format(type(self).__name__, self.label())

        ### show info - IDLE means not started at all
        if show_result_or_exception:
            exception = self.raised_exception()
            if exception:
                critical_msg = "CRIT. EXC." if self.is_critical() else "exception"
                info += "!! {} => {}:{}!!".format(critical_msg, type(exception).__name__, exception)
            elif self.is_done():
                info += "[[ -> {}]]".format(self.result())

        ### show dependencies in both directions
        if show_requires and self.required:
            info += " - requires {" + ", ".join(a.label(use_s_label=True) for a in self.required) + "}"
        return info
    
    def __repr__(self):
        return self.repr(show_requires=False)

    def requires(self, *requirements):
        """
        add requirements to a given job

        with j* being jobs or sequences, one can call:
        j1.requires(None)
        j1.requires([None])
        j1.requires((None,))
        j1.requires(j2)
        j1.requires(j2, j3)
        j1.requires([j2, j3])
        j1.requires((j2, j3))
        j1.requires(([j2], [[[j3]]]))
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
                for r in requirement:
                    self.requires(r)
            # not quite sure about what do to here in fact
            else:
                print("WARNING: fishy requirement in AbstractJob.requires")
                self.requires(list(requirement))

    def is_started(self):
        """
        returns a boolean that tells if the job has been scheduled already
        """
        return self._task is not None
    def is_done(self):
        """
        returns a boolean that tells if the job has completed
        """
        return self._task is not None and self._task._state == asyncio.futures._FINISHED
    def raised_exception(self):
        """
        returns an exception if the job has completed by raising an exception, None otherwise
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
        AbstractJob.__init__(self, *args, **kwds)

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
    A job that just  does print on messages, and optionnally sleeps for some time

    sleep is an optional float that tells how long to sleep after the messages get printed

    banner is an optional separation line, like 40*'='; it won't make it into details()
    """

    def __init__(self, *messages, sleep=None, banner=None,
                 # these are for AbstractJob
                 label = None, required = None):
        self.messages = messages
        self.sleep = sleep
        self.banner = banner
        AbstractJob.__init__(self, label = label, required = required)

    async def co_run(self):
        if self.banner:
            print(self.banner + " ", end="")
        print(*self.messages)
        if self.sleep:
            print("Sleeping for {}s".format(self.sleep))
            await asyncoio.sleep(self.sleep)

    async def co_shutdown(self):
        pass

    def details(self):
        result = ""
        if self.sleep:
            result += "adds sleep {}s ".format(self.sleep)
        result += "msg= "
        result += self.messages[0]
        result += "..." if len(self.messages) > 1 else ""
        return result
        
    def default_label(self):
        return self.details()
