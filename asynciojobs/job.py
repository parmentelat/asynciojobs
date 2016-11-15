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

# Engine == graph
# Job == node

class AbstractJob:
    """
    AbstractJob is a virtual class:

    (*) it offers some very basic graph-related features to model requirements
        a la makefile
    (*) its subclasses are expected to implement a `co_run()` method 
        that specifies the actual behaviour as a coroutine

    Can be created with 
    (*) boolean flag 'forever', if set, means the job is not returning at all and runs forever
        in this case Engine.orchestrate will not wait for that job, and will terminate it once all
        the regular i.e. not-forever jobs are done
    (*) an optional label - for convenience only

    It's mostly a companion class to the Engine class, that does the heavy lifting
    """

    def __init__(self, forever, label, critical=None, required=None):
        if label is None:
            label = "NOLABEL"
        self.label = str(label)
        self.forever = forever
        self.critical = critical
        # for convenience, one can mention only one AbstractJob
        self.required = set()
        self.requires(required)
        # once submitted in the asyncio loop/scheduler, the `co_run()` gets embedded in a 
        # Task object, that is our handle when talking to asyncio.wait
        self._task = None
        # ==== fields for our friend Engine all start with _e_
        # this is for graph browsing algos
        self._e_mark = None
        # the reverse of required
        self._e_successors = set()
        # if this is set by the engine, we use it for listing relationships
        self._e_label = None

    ##########
    _has_support_for_unicode = None

    @classmethod
    def detect_support_for_unicode(klass):
        if klass._has_support_for_unicode is None:
            try:
                klass._c_saltire.encode(sys.stdout.encoding)
                klass._has_support_for_unicode = True
            except UnicodeEncodeError as e:
                klass._has_support_for_unicode = False
        return klass._has_support_for_unicode
            

    ########## unicode version
    _c_saltire       = "\u2613" # ☓
    _c_circle_arrow  = "\u21ba" # ↺
    _c_flag          = "\u2690" # ⚐
    _c_warning       = "\u26a0" # ⚠
    _c_frowning_face = "\u2639" # ☹
    _c_smiling_face  = "\u263b" # ☻
    #_c_sun           = "\u2609" # ☉
    _c_infinity      = "\u221e" # ∞
    

    def short_unicode(self):
        # is it done, or ongoing, or not yet started ?
        c_running = self._c_saltire if self.is_done() else \
                 self._c_circle_arrow if self.is_started() else \
                 self._c_flag
        # is it critical or not ?
        c_crit = self._c_warning if self.is_critical() else " "
        # has it raised an exception or not ?
        # white frowning face or sun
        c_boom = self._c_frowning_face if self.raised_exception() \
                 else self._c_smiling_face if self.is_started() \
                 else " "
        # is it going forever or not
        c_forever = self._c_infinity if self.forever else " "

        # add extra white space as unicode chars in terminal tend to be wider than others
        return "{} {} {} {}".format(c_crit, c_boom, c_running, c_forever)
        
    def short_ascii(self):
        # is it done, or ongoing, or not yet started ?
        c_running = "x" if self.is_done() else \
                 "o" if self.is_started() else \
                 ">"
        # is it critical or not ?
        c_crit = "!" if self.is_critical() else " "
        # has it raised an exception or not ?
        # white frowning face or sun
        c_boom = ":(" if self.raised_exception() \
                 else ":)" if self.is_started() \
                 else "  "
        # is it going forever or not
        c_forever = "8" if self.forever else " "

        # add extra white space as unicode chars in terminal tend to be wider than others
        return "{} {} {} {}".format(c_crit, c_boom, c_running, c_forever)

    def short(self):
        """
        return a 4 characters string (in fact possibly 7 with interspaces)
        that illustrate the 4 dimensions of the job, that is
        (*) is it done/started/idle
        (*) is it declared as forever
        (*) is it critical
        (*) did it trigger an exception
        """
        if self.detect_support_for_unicode():
            return self.short_unicode()
        else:
            return self.short_ascii()
    
    def e_label(self, use_e_label):
        # use the label set from engine if present, otherwise our own verbose one
        return self.label if not use_e_label else ( self._e_label or self.label )

    def repr(self, show_requires=True, show_successors=False, use_e_label = False):
        info = self.short()
        info += " <{} `{}`".format(type(self).__name__, self.label)

        ### show info - IDLE means not started at all
        exception = self.raised_exception()
        if exception:
            critical_msg = "CRITICAL EXCEPTION" if self.is_critical() else "exception"
            info += " => {}:!!{}:{}!!".format(critical_msg, type(exception).__name__, exception)
        elif self.is_done():
            info += " -> {}".format(self.result())
        info += ">"
        ### show dependencies in both directions
        if show_requires and self.required:
            info += " - requires:{" + ", ".join(a.e_label(use_e_label) for a in self.required) + "}"
        # this is almost always turned off anyways
        if show_successors and self._e_successors:
            info += " - allows: {" + ", ".join(a.e_label(use_e_label) for a in self._e_successors) + "}"
        return info
    
    def __repr__(self):
        return self.__repr__(show_requires=False, use_e_label = False)

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
        return self._task is not None
    def is_done(self):
        return self._task is not None and self._task._state == asyncio.futures._FINISHED
    def raised_exception(self):
        """returns an exception if applicable, or None"""
        return self._task is not None and self._task._exception

    def is_critical(self):
        return self.critical

    def result(self):
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
        Just run this one job on its own - useful for debugging
        the internals of that job, e.g. for checking for gross mistakes
        and other exceptions
        """
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.co_run())


####################
class Job(AbstractJob):

    """
    Most mundane form is to provide a coroutine yourself
    """
    
    def __init__(self, coro, forever=False, label=None, *args, **kwds):
        self.coro = coro
        AbstractJob.__init__(self, forever=forever, label=label, *args, **kwds)

    async def co_run(self):
        result = await self.coro
        return result

    async def co_shutdown(self):
        pass
