#!/usr/bin/env python3

"""
The PureScheduler class is a set of AbstractJobs, that together with their
*required* relationship, form an execution graph.
"""

import time
import io
import asyncio

from .bestset import BestSet

from .job import AbstractJob
from .sequence import Sequence
from .window import Window
from .watch import Watch
from .dotstyle import DotStyle

#
# will hopefully go away some day
DEBUG = False                                           # pylint: disable=C0103
# DEBUG = True

# pylint settings
# W0212: we have a lot of accesses to protected members of other classes
# R0914 Too many local variables
# R0904 Too many public methods (xxx this one should be reachable)
# C0302 Too many lines in module (would be nice to not count docstrings)
# pylint: disable=R0914, R0904, C0302

# Historical note: we used to formally define the Schedulable type hint
# but that ended up clobbering the documentation, and was more harmful
# than helpful
# in plain english, a Schedulable object is either
# an instance of AbstractJob or of Sequence


class PureScheduler:                                    # pylint: disable=r0902
    """
    A PureScheduler instance is made of a set of AbstractJob objects.

    The purpose of the scheduler object is to orchestrate an execution of
    these jobs that respects the *required* relationships,
    until they are all complete. It starts with the ones that have no
    requirement, and then triggers the other ones as their requirement
    jobs complete.

    For this reason, the dependency/requirements graph **must be acyclic**.

    Optionnally a scheduler orchestration can be confined to a finite number
    of concurrent jobs (see the ``jobs_window`` parameter below).

    It is also possible to define a ``timeout`` attribute on the object,
    that will limit the execution time of a scheduler.


    Running an AbstractJob means executing its :meth:`co_run()` method,
    which must be a coroutine

    The result of a job's :meth:`~asynciojobs.job.AbstractJob.co_run()`
    is NOT taken into account, as
    long as it returns without raising an exception. If it does raise
    an exception, overall execution is aborted iff the job is
    critical. In all cases, the result and/or exception of each
    individual job can be inspected and retrieved individually at any
    time, including of course once the orchestration is complete.

    Parameters:
      jobs_or_sequences: instances of `AbstractJob` or `Sequence`.
        The order in which they are mentioned is irrelevant.
      jobs_window: is an integer that specifies how many jobs
        can be run simultaneously. None or 0 means no limit.
      timeout: can be an `int` or `float` and is expressed
       in seconds; it applies to the overall orchestration of that scheduler,
       not to any individual job. Can be also ``None``, which means no timeout.
      shutdown_timeout: same meaning as ``timeout``, but for the shutdown phase.
      watch: if the caller passes a :class:`~asynciojobs.watch.Watch`
        instance, it is used in debugging messages to show the time
        elapsed wrt that watch, instead of using the wall clock.
      verbose (bool): flag that says if execution should be verbose.


    Examples:
      Creating an empty scheduler::

        s = Scheduler()

      A scheduler with a single job::

        s = Scheduler(Job(asyncio.sleep(1)))

      A scheduler with 2 jobs in parallel::

        s = Scheduler(Job(asyncio.sleep(1)),
                      Job(asyncio.sleep(2)))

      A scheduler with 2 jobs in sequence::

        s = Scheduler(
                Sequence(
                    Job(asyncio.sleep(1)),
                    Job(asyncio.sleep(2))
                ))

    In this document, the ``Schedulable`` name refers to a type hint, that
    encompasses instances of either the `AbstractJob` or `Sequence` classes.

    """

    def __init__(self, *jobs_or_sequences,
                 jobs_window=None, timeout=None,
                 shutdown_timeout=1,
                 watch=None, verbose=False):

        self.jobs = BestSet(
            Sequence._flatten(jobs_or_sequences))       # pylint: disable=W0212
        self.jobs_window = jobs_window
        # timeout is in seconds
        self.timeout = timeout
        self.shutdown_timeout = shutdown_timeout
        self.watch = watch
        self.verbose = verbose
        # why does it fail ?
        # bool
        self._failed_critical = False
        # False, or the initial timeout
        self._failed_timeout = False
        # see also _record_beginning
        self._expiration = None
        # avoid multiple shutdowns
        self._did_shutdown = False

    # think of an scheduler as a set of jobs
    def update(self, jobs):
        """
        Adds a collection of ``Schedulable`` objects;
        this method is named after ``set.update()``.

        Parameters:
          jobs: a collection of ``Schedulable`` objects.

        Returns:
          self: the scheduler object, for cascading insertions if needed.
        """
        jobs = BestSet(Sequence._flatten(jobs))      # pylint: disable=W0212
        self.jobs.update(jobs)
        return self

    def add(self, job):
        """
        Adds a single ``Schedulable`` object;
        this method name is inspired from plain python ``set.add()``

        Parameters:
          job: a single ``Schedulable`` object.

        Returns:
          self: the scheduler object, for cascading insertions if needed.
        """
        self.update([job])
        return self

    def remove(self, job):
        """
        Removes a single ``Schedulable`` object;
        this method name is inspired from plain python ``set.remove()``

        Parameters:
          job: a single ``Schedulable`` object.

        Raises:
          KeyError: if job not in scheduler.

        Returns:
          self: the scheduler object, for cascading insertions if needed.
        """
        self.jobs.remove(job)
        return self

    def __len__(self):
        """
        You can call len() on a PureScheduler object.
        Returns:
          int: number of jobs in the scheduler.
        """
        return len(self.jobs)

    def failed_time_out(self):
        """
        Returns:
          bool: returns True if and only if :meth:`co_run()`
          has failed because of a time out.
        """
        return self._failed_timeout

    def failed_critical(self):
        """
        Returns:
          bool: returns True if and only if :meth:`co_run()`
          has failed because a critical job has raised an exception.
        """
        return self._failed_critical

    def why(self):
        """
        Returns:
          str: a message explaining why :meth:`co_run()` has failed,
          or ``"FINE"`` if it has not failed.

        Notes:

          At this point the code does not check that :meth:`co_run()` has
          actually been called.
        """
        if self._failed_timeout:
            return "TIMED OUT after {}s".format(self._failed_timeout)
        if self._failed_critical:
            return "a CRITICAL job has raised an exception"
        return "FINE"

    ####################
    def sanitize(self):
        """
        This method ensures that the requirements relationship is closed within
        the scheduler. In other words, it removes any requirement attached to a
        job in this scheduler, but that is not itself part of the scheduler.

        This can come in handy in some scheduler whose composition depends on
        external conditions.

        In any case it is crucial that this property holds
        for :meth:`co_run()` to perform properly.

        Returns:
          bool: returns True if scheduler object was fine,
          and False if at least one removal was needed.
        """

        changes = False
        for job in self.jobs:
            before = len(job.required)
            job.required &= self.jobs
            job._s_successors &= self.jobs
            after = len(job.required)
            if before != after:
                changes = True
                if self.verbose:
                    print(20 * '*',
                          "WARNING: job {} has had {} requirements removed"
                          .format(job, before - after))
            # recursively scan nested schedulers
            if isinstance(job, PureScheduler):
                changes = job.sanitize() or changes
        return not changes

    ####################
    def check_cycles(self):
        """
        Performs a minimal sanity check.
        The purpose of this is primarily to check for cycles,
        and/or missing starting points.

        It's not embedded in :meth:`co_run()` because
        it is not strictly necessary, but it is safer to call this
        before running the scheduler if one wants to double-check the
        jobs dependency graph early on.

        It might also help to have a sanitized scheduler,
        but here again this is up to the caller.

        Returns:
            bool: True if the topology is fine
        """
        try:
            for _ in self.topological_order():
                pass
            return True
        except Exception as exc:                        # pylint: disable=W0703
            if self.verbose:
                print("check_cycles failed", exc)
            return False

    ####################
    def topological_order(self):
        """
        A generator function that scans the graph in topological order,
        in the same order as the orchestration,
        i.e. starting from jobs that have no dependencies, and moving forward.

        Beware that this is not a separate iterator, so it can't be nested,
        which in practice should not be a problem.

        Examples:

          Assuming all jobs have a ``label`` attribute,
          print them in the "right" order::

            for job in scheduler.topological_order():
                print(job.label)
        """
        self._reset_marks()
        nb_marked = 0
        target_marked = len(self.jobs)

        while True:
            # detect a fixed point
            changed = False
            # loop on unfinished business
            for job in self.jobs:
                # ignore jobs already marked
                if job._s_mark:                         # pylint: disable=W0212
                    continue
                # if there's no requirement (first pass),
                # or later on if all requirements have already been marked,
                # then we can mark this one
                has_unmarked_requirements = False
                for required_job in job.required:
                    if required_job._s_mark is None:    # pylint: disable=W0212
                        has_unmarked_requirements = True
                if not has_unmarked_requirements:
                    job._s_mark = True                  # pylint: disable=W0212
                    nb_marked += 1
                    changed = True
                    yield job
            # >= is for extra safety but it should be an exact match
            if nb_marked >= target_marked:
                # we're done
                break
            if not changed:
                # this is wrong
                raise Exception(
                    "scheduler could not be scanned"
                    " - most likely because of cycles")
        # if we still have jobs here it's not good either,
        # although it should not happen on a sanitized scheduler
        if nb_marked != target_marked:
            raise Exception("scheduler could not be scanned,"
                            " {} jobs are not reachable from free jobs"
                            .format(target_marked - nb_marked))

    # entry and exit jobs
    def entry_jobs(self):
        """
        A generator that yields all jobs that have no requirement.

        Exemples:

          List all entry points::

             for job in scheduler.entry_points():
                 print(job)
        """
        for job in self.jobs:
            if not job.required:
                yield job

    def exit_jobs(self, *,
                  discard_forever=True,
                  compute_backlinks=True):
        """
        A generator that yields all jobs that are
        not a requirement to another job; it is thus in some sense
        the reverse of :meth:`entry_points()`.

        Parameters:
          discard_forever: if True, jobs marked as forever are skipped; forever
            jobs often have no successors, but are seldom of interest when
            calling this method.
          compute_backlinks: for this method to work properly, it is necessary
            to compute backlinks, an internal structure that holds the opposite
            of the *required* relationship. Passing False here allows to skip
            that stage, when that relationship is known to be up to date
            already.

        """
        if compute_backlinks:
            self._backlinks()
        for job in self.jobs:
            if discard_forever and job.forever:
                continue
            if not job._s_successors:                   # pylint: disable=w0212
                yield job

    def _entry_csv(self):
        result = ", ".join(job.repr_id()
                           for job in self.entry_jobs())
        if result:
            result = "{" + result + "}"
        return result

    def _exit_csv(self, **exit_kwds):
        'accepts same parameters as self.exit_jobs()'
        result = ", ".join(job.repr_id()
                           for job in self.exit_jobs(**exit_kwds))
        if result:
            result = "{" + result + "}"
        return result

    def some_entry_job(self):
        """
        Returns one randomly picked entry job
        Needed when creating the dot format, because
        of the specifics of that format; although it may be
        that returning any job would do the job as well
        """
        for job in self.entry_jobs():
            return job
        raise ValueError("no entry found")

    @staticmethod
    def _middle_index(last):
        return (last-1) // 2

    def middle_entry_job(self):
        """
        Like some_entry_job, but as an attempt to improve graphical layout
        we return the job that has its index in the middle of the entry jobs
        """
        # scan once
        number_entries = sum(1 for _ in self.entry_jobs())
        if not number_entries:
            raise ValueError("no entry found")
        # scan again until mid-way
        entries = self.entry_jobs()
        index = self._middle_index(number_entries)
        for _, job in zip(range(index+1), entries):
            pass
        # pylint detects that job is possibley undefined,
        # which could only occur if range(index+1) is empty
        # but index is >= 0 so we're in the clear
        return job                                      # pylint: disable=w0631

    def some_exit_job(self, **exit_kwds):
        """
        Same for exit nodes;
        accepts same parameters as self.exit_jobs()
        """
        for job in self.exit_jobs(**exit_kwds):
            return job
        raise ValueError("No exit found")

    def middle_exit_job(self, **exit_kwds):
        """
        ditto for exit nodes
        """
        number_exits = sum(1 for _ in self.exit_jobs(**exit_kwds))
        # no need to do this in any case from now on
        exit_kwds['compute_backlinks'] = False
        if not number_exits:
            raise ValueError("no exit found")
        exits = self.exit_jobs(**exit_kwds)
        index = self._middle_index(number_exits)
        for _, job in zip(range(index+1), exits):
            pass
        # ditto
        return job                                      # pylint: disable=w0631

    def repr_entries(self):                             # pylint: disable=c0111
        return "entries={}".format(self._entry_csv())

    def repr_exits(self):                               # pylint: disable=c0111
        return "exits={}".format(self._exit_csv(compute_backlinks=True))

    ####################
    def _reset_marks(self):
        """
        reset Job._s_mark on all jobs
        """
        for job in self.jobs:
            job._s_mark = None                          # pylint: disable=W0212

    def _reset_tasks(self):
        """
        In case one tries to run the same scheduler twice
        """
        for job in self.jobs:
            job._task = None                            # pylint: disable=W0212

    def _backlinks(self):
        """
        initialize Job._s_successors on all jobs
        as the reverse of Job.required
        """
        for job in self.jobs:
            job._s_successors = BestSet()            # pylint: disable=W0212
        for job in self.jobs:
            for req in job.required:
                req._s_successors.add(job)              # pylint: disable=W0212

    def _ensure_future(self, job, window, loop):        # pylint: disable=R0201
        """
        this is the hook that lets us make sure the created Task objects
        have a backlink pointer to their corresponding job
        """
        #
        # this is where we call co_run()
        #
        # the decorated object is a coroutine that needs to be CALLED:
        #                                               vv
        task = asyncio.ensure_future(window.run_job(job)(), loop=loop)
        # create references back and forth between Job and asyncio.Task
        task._job = job                                 # pylint: disable=W0212
        job._task = task                                # pylint: disable=W0212
        return task

    def _record_beginning(self, timeout):
        """
        Called once at the beginning of :meth:`co_run()`, this method
        computes the absolute expiration date when a timeout is defined.
        """
        self._expiration = \
            None if timeout is None \
            else time.time() + timeout

    def _remaining_timeout(self):
        """
        Called each time :meth:`co_run()` is about to call `asyncio.wait()`,
        this method computes the timeout argument for wait
        - or None if co_run is called without a timeout
        """
        return \
            None if self._expiration is None \
            else self._expiration - time.time()

    async def _tidy_tasks(self, pending):
        """
        Once :meth:`co_run()` is done, in order to tidy up the underlying
        Task objects that have not completed, it is necessary to cancel
        them and wait for them.

        According to the context, this can be with forever tasks,
        or because a timeout has occured.
        """
        if pending:
            for task in pending:
                task.cancel()
            # wait for the forever tasks for a clean exit
            # don't bother to set a timeout, as this is expected
            # to be immediate since all tasks are canceled
            await asyncio.wait(pending)

    async def _tidy_tasks_exception(self, tasks):
        """
        Similar but in order to clear the exceptions,
        we need to run gather() instead
        """
        exception_tasks = [task for task in tasks
                           if task._exception]          # pylint: disable=W0212
        for task in exception_tasks:
            task.cancel()
            # if DEBUG is turned on, provide details on the exceptions
            if DEBUG:
                job = task._job                         # pylint: disable=W0212
                self._show_task_stack(
                    task,
                    "TIDYING {} {} {}"
                    .format(job.repr_id(), job.repr_short(), job.repr_main()))
        # don't bother to set a timeout,
        # this is expected to be immediate
        # since all tasks are canceled
        await asyncio.gather(*exception_tasks, return_exceptions=True)

    @staticmethod
    def _show_task_stack(task, msg='STACK', margin=4, limit=None):
        if isinstance(task, AbstractJob):
            task = task._task                           # pylint: disable=W0212
        sep = margin * ' ' + 20 * '*'
        print(sep)
        print(sep, 'BEG ' + msg)
        print(sep)
        # naive approach would be like this, but does not support margin:
        # task.print_stack()
        stio = io.StringIO()
        task.print_stack(file=stio, limit=limit)
        stio.seek(0)
        for line in stio:
            print(margin * ' ' + line, end="")
        print(sep)
        print(sep, 'END ' + msg)
        print(sep)

    async def _feedback(self, jobs, state, force=False):
        """
        When self.verbose is set, provide feedback about the mentioned
        jobs having reached this state
        if jobs is None, then state is a message to be shown as-is
        jobs may be a collection or an individual Job or Task object
        """
        if not force and not self.verbose:
            return

        def print_time():                               # pylint: disable=c0111
            if self.watch is not None:
                self.watch.print_elapsed()
            else:
                Watch.print_wall_clock()
        name = ""
        # with this line we allow a PureScheduler to have a label
        # it's mostly applicable to Scheduler instances, but can come in
        # handy for pure Scheduler's as well
        if hasattr(self, 'label'):
            name = "({})".format(self.label)            # pylint: disable=e1101

        # general feedback when no job is specified by caller
        if jobs is None:
            print_time()
            print("SCHEDULER{}: {}".format(name, state))
            return
        if not isinstance(jobs, (list, BestSet, set, tuple)):
            jobs = (jobs,)
        for job in jobs:
            if not isinstance(job, AbstractJob):
                # we expect a task here
                job = job._job                          # pylint: disable=W0212
            print_time()
            print("{} {}: {} {} {}"
                  .format(name, state,
                          job.repr_id(), job.repr_short(), job.repr_main()),
                  end="")
            if self.verbose:
                print(" {} {}"
                      .format(job.repr_result(),
                              job.repr_requires()),
                      end="")
            print()

    ####################
    def shutdown(self):
        """
        A synchroneous wrapper around :meth:`co_shutdown()`.

        Returns:
          bool: True if everything went well, False otherwise;
          see :meth:`co_shutdown()` for details.

        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.co_shutdown())

    async def co_shutdown(self):
        """
        Shut down the scheduler, by sending the
        :meth:`~asynciojobs.job.AbstractJob.co_shutdown()`
        method to all the jobs, possibly nested.

        Within nested schedulers, a job receives the `shutdown` event when its
        **enclosing** scheduler terminates, and **not** at the end of the
        **outermost** scheduler.

        Also note that all job instances receive the 'co_shutdown()' method,
        even the ones that have not yet started; it is up to the `co_shutdown()`
        method to triage the jobs according to their life cycle status - see
        :meth:`~asynciojobs.job.AbstractJob.is_running()` and similar.

        This mechanism should be used only for minimal housekeeping only, it is
        recommended that intrusive cleanup be made part of separate, explicit
        methods.

        :Note: typically in apssh for example, several jobs sharing the same ssh
        connection need to arrange for that connection to *be kept alive  across
        an entire scheduler lifespan, and closed later on. Historically there
        had been an attempt to deal with this automagically, through the present
        shutdown mechanism. However, this turned out to be the wrong choice, as
        the choice of closing connections needs to be left to the user.
        Additionally, with nested schedulers, this can become pretty awkward.
        Closing ssh connections is now to be achieved explicitly through a call
        to a specific apssh function.

        Returns:
          bool: True if all the
           :meth:`~asynciojobs.job.AbstractJob.co_shutdown()`
           methods attached to the jobs in the scheduler complete
           within ``shutdown_timeout``, which is an attribute of the scheduler.
           If the ``shutdown_timeout`` attribute on this object is ``None``,
           no timeout is implemented.

        Notes:
          There is probably space for a lot of improvement here xxx:

          - behaviour is unspecified if any of the co_shutdown()
            methods raises an exception;
          - right now, a subscheduler that sees a timeout expiration
            does not cause the overall co_shutdown() to return ``False``,
            which is arguable;
          - another possible weakness in current implementation is that
            it does not support to shutdown a scheduler that is still running.
        """

        # implementation note
        # it could be tempting to have this code only send co_shutdown
        # on pure jobs
        # however this approach does not work in cases where a timeout occurs
        # which causes a (sub-)nested scheduler to be kind of paused, without
        # actually being aware of it (its co_run() code does not return at all)
        # so it's much simpler to always scan all the whole scheduler tree,
        # but to skip schedulers that have already shut down

        if self._did_shutdown:
            return

        self._did_shutdown = True

        tasks = [asyncio.ensure_future(job.co_shutdown())
                 for job in self.jobs]

        if not tasks:
            return True

        # warning: xxx this use a unique attribute to remember expiration
        # so things might/probably will get messed up if one attempts
        # to shutdown a scheduler while it is running.
        self._record_beginning(self.shutdown_timeout)
        timeout = self._remaining_timeout()

        await self._feedback(None, "scheduler is shutting down...")

        # the done part is of no use here
        _, pending = await asyncio.wait(tasks, timeout=timeout)
        # everything went fine
        # NOTE however: here we say that sub-schedulers that expired in timeout
        # should not impact the overall result; this is an arguable choice
        if not pending:
            return True

        # with nested schedulers, this message would not be helpful
        # because it is only guaranteed to show up at the toplevel
        # and in addition the jobs count is local to the scheduler
        # this is why this it's a verbose/feedback thing
        await self._feedback(
            None,
            "WARNING: {}/{} co_shutdown() methods"
            " have not returned within timeout"
            .format(len(pending), len(self.jobs)))
        await self._tidy_tasks(pending)
        # we might need to consume any exception as well ?
        # self._tidy_tasks_exception(done)
        return False

    ####################
    def run(self, *args, **kwds):
        """
        A synchroneous wrapper around :meth:`co_run()`,
        please refer to that link for details on parameters and return value.

        Also, the canonical name for this is ``run()`` but for historical
        reasons you can also use ``orchestrate()`` as an alias for ``run()``.
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.co_run(*args, **kwds))

    # define the alias for legacy
    orchestrate = run

    async def co_run(self):                       # pylint: disable=R0912,R0915

        """
        The primary entry point for running a scheduler.
        See also :meth:`run()` for a synchronous wrapper around this coroutine.

        Runs member jobs (that is, schedule their `co_run()` method)
        in an order that satisfies their *required* relationsship.

        Proceeds to the end no matter what, except if either:

        * one critical job raises an exception, or
        * a timeout occurs.

        Returns:
          bool: `True` if none of these 2 conditions occur, `False` otherwise.

        Jobs marked as ``forever`` are not waited for.

        No automatic shutdown is performed, user needs to explicitly call
        :meth:`co_shutdown()` or :meth:`shutdown()`.
        """
        loop = asyncio.get_event_loop()
        # create a Window no matter what; it will know what to do
        # also if jobs_window is None
        window = Window(self.jobs_window, loop)

        # initialize; this one is not crucial but is helpful
        # for debugging purposes
        self._set_sched_ids()
        # backlinks - i.e. _s_successors is the reverse of required
        self._backlinks()
        # clear any Task instance
        self._reset_tasks()
        # for computing global timeout
        self._record_beginning(self.timeout)
        # reset status
        self._failed_critical = False
        self._failed_timeout = False

        # empty schedulers are fine too
        if not self.jobs:
            return True

        # how many jobs do we expect to complete: the ones that don't run
        # forever
        nb_jobs_finite = len([j for j in self.jobs if not j.forever])
        # the other ones
        nb_jobs_forever = len(self.jobs) - nb_jobs_finite
        # count how many jobs have completed
        nb_jobs_done = 0

        # start with the free jobs
        entry_jobs = [job for job in self.jobs if not job.required]

        if not entry_jobs:
            raise ValueError("No entry points found - cannot orchestrate")

        if self.verbose:
            await self._feedback(None, "entering co_run() with {} jobs"
                                 .format(len(self.jobs)))

        await self._feedback(entry_jobs, "STARTING")

        pending = [self._ensure_future(job, window, loop=loop)
                   for job in entry_jobs]

        while True:
            done, pending \
                = await asyncio.wait(pending,
                                     timeout=self._remaining_timeout(),
                                     return_when=asyncio.FIRST_COMPLETED)

            done_ok = {t for t in done
                       if not t._exception}             # pylint: disable=W0212
            await self._feedback(done_ok, "DONE")
            done_ko = done - done_ok
            await self._feedback(done_ko, "RAISED EXC.")

            # nominally we have exactly one item in done
            # the only condition where we have nothing in done is
            # because a timeout occurred
            # there are also cases where done has more than one entry
            # typically when 2 jobs have very similar durations
            if not done:
                await self._feedback(None,
                                     "PureScheduler.co_run: TIMEOUT occurred",
                                     force=True)
                # clean up
                await self._feedback(pending, "ABORTING")
                await self._tidy_tasks(pending)
                await self.co_shutdown()
                self._failed_timeout = self.timeout
                return False

            # exceptions need to be cleaned up
            # clear the exception(s) in done
            await self._tidy_tasks_exception(done)
            # do we have at least one critical job with an exception ?
            critical_failure = False
            for done_task in done:
                done_job = done_task._job               # pylint: disable=W0212
                if done_job.raised_exception():
                    critical_failure = critical_failure \
                        or done_job.is_critical()
                    await self._feedback(
                        done_job, "EXCEPTION occurred - on {}critical job"
                        .format("non-" if not done_job.is_critical() else ""))
                    # make sure these ones show up even if not in debug mode
                    if DEBUG:
                        self._show_task_stack(done_task, "DEBUG")
            if critical_failure:
                await self._tidy_tasks(pending)
                await self.co_shutdown()
                self._failed_critical = True
                await self._feedback(
                    None, "Emergency exit upon exception in critical job",
                    force=True)
                return False

            # are we done ?
            # only account for not forever jobs (that may still finish, one
            # never knows)
            done_jobs_not_forever = {
                j for j in done
                if not j._job.forever}                  # pylint: disable=W0212
            nb_jobs_done += len(done_jobs_not_forever)

            if nb_jobs_done == nb_jobs_finite:
                if DEBUG:
                    print("PureScheduler.co_run: {} CLEANING UP at iter. {}/{}"
                          .format(4 * '-', nb_jobs_done, nb_jobs_finite))
                if self.verbose and nb_jobs_forever != len(pending):
                    print("WARNING - apparent mismatch"
                          " - {} forever jobs, {} are pending"
                          .format(nb_jobs_forever, len(pending)))
                await self._feedback(pending, "TIDYING forever")
                await self._tidy_tasks(pending)
                await self.co_shutdown()
                return True

            # go on : find out the jobs that can be added to the mix
            # only consider the ones that are right behind any of the the jobs
            # that just finished
            # no need to use and BestSet here
            possible_next_jobs = set()
            for done_task in done:
                possible_next_jobs.update(
                    done_task._job._s_successors)       # pylint: disable=W0212

            # find out which ones really can be added
            added = 0
            for candidate_next in possible_next_jobs:
                # do not add an job twice
                if candidate_next.is_running():
                    continue
                # we can start only if all requirements are satisfied
                # at this point entry points have is_running() -> return True
                # so they won't run this code
                requirements_ok = True
                for req in candidate_next.required:
                    if not req.is_done():
                        requirements_ok = False
                if requirements_ok:
                    await self._feedback(candidate_next, "STARTING")
                    pending.add(self._ensure_future(
                        candidate_next, window, loop=loop))
                    added += 1

    def _total_length(self):
        """
        Counts the total number of jobs that need to be numbered
        in nested scenarii.

        A regular job counts for 1,
        and a scheduler counts for 1 + its own _total_length

        Returns:
          int: total number of nodes in subject and nested schedulers

        """
        return sum(job._job_count()                     # pylint: disable=w0212
                   for job in self.jobs)

    def _set_sched_ids(self, start=1, id_format=None):
        """
        Write into each job._sched_id an id compliant
        with topological order.

        Returns:
          int: the next index to use
        """
        # id_format is computed once by the toplevel scheduler
        # and then passed along the tree

        if id_format is None:
            import math
            # how many chars do we need to represent all jobs
            total = self._total_length()
            width = 1 if total <= 9 \
                else int(math.log(total-1, 10)) + 1
            # id_format is intended to be e.g. {:02d}
            id_format = "{{:0{w}d}}".format(w=width)    # pylint: disable=w1303
        i = start
        for job in self.topological_order():
            i = job._set_sched_id(i, id_format)         # pylint: disable=w0212
        return i

    def _set_sched_ids_safe(self, stack):
        """
        Similar to _set_sched_ids, in that the member jobs get their
        internal sched_id set, for identifying jobs when expliciting
        internal relationships in list_safe().

        The difference here is that the numbering is not based on topological
        order: jobs in a scheduler are scanned in random order, and jobs in
        nested schedulers get prefixed.
        """
        root = ".".join(str(index) for index in stack)
        for i, job in enumerate(self.jobs, 1):
            job._sched_id = "{}.{}".format(root, i)     # pylint: disable=W0212
            if isinstance(job, PureScheduler):
                job._set_sched_ids_safe(stack+[i])      # pylint: disable=W0212

    # ----
    def list(self, details=False):
        """
        Prints a complete list of jobs in topological order, with their status
        summarized with a few signs. See the README for examples and a legend.

        Beware that this might raise an exception if :meth:`check_cycles()`
        would return ``False``, i.e. if the graph is not acyclic.
        """
        # so now we can refer to other jobs by their id when showing
        # requirements
        self._set_sched_ids()
        for job in self.topological_order():
            job._list(details, 0, True)                 # pylint: disable=W0212

    def list_safe(self):
        """
        Print jobs in no specific order, the advantage being that it
        works even if scheduler is broken wrt :meth:`check_cycles()`.
        On the other hand, this method is not able to list requirements.
        """
        self._set_sched_ids_safe([])
        for job in self.jobs:
            # pass as stack a list of indexes
            job._list_safe(True)                        # pylint: disable=W0212


    # ----
    def __repr__(self):
        # linter says unused variable but it is indeed used in f-string
        nb_total = len(self.jobs)                       # pylint: disable=W0641
        done = {j for j in self.jobs if j.is_done()}
        nb_done = len(done)                             # pylint: disable=W0641
        running = {j for j in self.jobs if j.is_running()}
        ongoing = running - done
        nb_ongoing = len(ongoing)                       # pylint: disable=W0641
        idle = self.jobs - running
        nb_idle = len(idle)                             # pylint: disable=W0641
        return "{type} with {nb_done} done + {nb_ongoing} ongoing" \
               " + {nb_idle} idle = {nb_total} job(s)" \
            .format(type=type(self).__name__, **locals())

    def debrief(self, details=False):
        """
        Designed for schedulers that have failed to orchestrate.

        Print a complete report, that includes `list()` but also gives
        more stats and data.
        """
        nb_total = len(self.jobs)
        done = {j for j in self.jobs if j.is_done()}
        nb_done = len(done)
        running = {j for j in self.jobs if j.is_running()}
        ongoing = running - done
        nb_ongoing = len(ongoing)
        idle = self.jobs - running
        nb_idle = len(idle)

        exceptions = {j for j in self.jobs if j.raised_exception()}
        criticals = {j for j in exceptions if j.is_critical()}

        message = "scheduler has a total of {} jobs".format(nb_total)

        def legible_message(number, adj):               # pylint: disable=C0111
            if number == 0:
                return " none is {}".format(adj)
            if number == 1:
                return " 1 is {}".format(adj)
            return " {} are {}".format(number, adj)
        message += ", " + legible_message(nb_done, "done")
        message += ", " + legible_message(nb_ongoing, "ongoing")
        message += ", " + \
            legible_message(nb_idle, "idle (or scheduled but not running)")

        print(5 * '-', self.why())
        self.list(details)
        #####
        if exceptions:
            nb_exceptions = len(exceptions)
            nb_criticals = len(criticals)
            print("===== {} job(s) with an exception, including {} critical"
                  .format(nb_exceptions, nb_criticals))
            # show critical exceptions first
            for j in self.topological_order():
                if j in criticals:
                    self._show_task_stack(
                        j, "stack for CRITICAL JOB {} {} {}"
                        .format(j.repr_id(), j.repr_short(), j.repr_main()))
            # then exceptions that were not critical
            non_critical_exceptions = exceptions - criticals
            for j in self.topological_order():
                if j not in non_critical_exceptions:
                    continue
                if not self.verbose:
                    print("non-critical: {}: exception {}"
                          .format(j._get_text_label(),  # pylint: disable=W0212
                                  j.raised_exception()))
                    if self.verbose:
                        self._show_task_stack(
                            j, "non-critical job exception stack")

    # ----
    def iterate_jobs(self, scan_schedulers=False):
        """
        A generator that scans all jobs and subjobs

        Parameters:
          scan_schedulers: if set, nested schedulers are ignored,
            only actual jobs are reported; otherwise, nested schedulers
            are listed as well.
        """
        if scan_schedulers:
            yield self
        for job in self.jobs:
            yield from job._iterate_jobs(               # pylint: disable=W0212
                scan_schedulers=scan_schedulers)

    # ----
    # graphical outputs

    # in a first attempt we had one function to store a dot format into a file
    # and another one to build the graph natively; hence duplication of code
    # there are simpler means to do that
    # in addition with nested schedulers things become a bit messy, so
    # it's crucial to stick to one single code

    def dot_format(self):
        """
        Creates a graph that depicts the jobs and their *requires*
        relationships, in `DOT Format`_.

        Returns:
          str: a representation of the graph in `DOT Format`_
          underlying this scheduler.

        See graphviz_'s documentation, together with its `Python wrapper
        library`_, for more information on the format and available tools.

        See also `Wikipedia on DOT`_ for a list of tools that support the
        ``dot`` format.

        As a general rule, ``asynciojobs`` has a support for producing
        `DOT Format`_ but stops short of actually importing ``graphviz``
        that can be cumbersome to install, but for the notable exception
        of the :meth:graph() method. See that method for how
        to convert a ``PureScheduler`` instance into a native ``DiGraph``
        instance.

        .. _DOT Format: https://graphviz.gitlab.io/_pages/doc/info/lang.html

        .. _graphviz: https://graphviz.gitlab.io/documentation/

        .. _Python wrapper library: https://graphviz.readthedocs.io/en/stable/

        .. _Wikipedia on DOT: https://en.wikipedia.org/wiki/
DOT_%28graph_description_language%29
        """
        self._set_sched_ids()
        return "digraph asynciojobs" + self._dot_body(DotStyle())

    def _dot_body(self, dot_style):
        """
        Creates the dot body for a scheduler, i.e the part between
        brackets, without the surrounding ``digraph`` or ``subgraph``
        declaration, that must be added from the outside, depending
        on whether we have a main scheduler or a nested one.
        """
        # use ids so as to not depend on labels

        result = ""
        result += "{\n"
        result += "compound=true;\n"
        result += "graph [{}];\n".format(dot_style)
        for job in self.topological_order():

            # regular jobs
            if not isinstance(job, PureScheduler):
                # declare node, attach label, and set visual attributes
                result += job.repr_id()
                result += ' [{}]\n'.format(job.dot_style())

                # add edges
                for req in job.required:

                    # upstream is a regular job
                    if not isinstance(req, PureScheduler):
                        result += ("{} -> {};\n"
                                   .format(req.repr_id(), job.repr_id()))

                    # upstream is a scheduler
                    else:
                        from_node = req.middle_exit_job()
                        cluster_name = req.dot_cluster_name()
                        result += ("{} -> {} [ltail={}];\n"
                                   .format(from_node.repr_id(),
                                           job.repr_id(),
                                           cluster_name))

            # nested scheduler
            else:
                # insert a subgraph instead

                cluster_name = job.dot_cluster_name()
                result += "subgraph {}".format(cluster_name)
                result += job._dot_body(                # pylint: disable=w0212
                    job.dot_style())

                for req in job.required:

                    # upstream is a regular job
                    if not isinstance(req, PureScheduler):
                        result += ("{} -> {} [lhead={}];\n"
                                   .format(req.repr_id(),
                                           job.middle_entry_job().repr_id(),
                                           cluster_name))

                    # upstream is a scheduler as well
                    else:
                        src_cluster_name = req.dot_cluster_name()
                        result += ("{} -> {} [lhead={} ltail={}];\n"
                                   .format(req.middle_exit_job().repr_id(),
                                           job.middle_entry_job().repr_id(),
                                           cluster_name,
                                           src_cluster_name))

        result += "}\n"
        return result

    def export_as_dotfile(self, filename):
        """
        This method does not require ``graphviz`` to be installed, it
        writes a file in dot format for post-processing with
        e.g. graphviz's ``dot`` utility. It is a simple wrapper around
        :meth:`dot_format()`.

        Parameters:
          filename: where to store the result.

        Returns:
          str: a message that can be printed for information, like e.g.
          ``"(Over)wrote foo.dot"``

        See also the :meth:`graph()` method that serves a similar purpose but
        natively as a ``graphviz`` object.

        As an example of post-processing, a PNG image can be then obtained from
        that dotfile with e.g.::

          dot -Tpng foo.dot -o foo.png
        """
        with open(filename, 'w') as output:
            output.write(self.dot_format())
        return "(Over)wrote {}".format(filename)

    def graph(self):
        """
        Returns:
          graphviz.Digraph: a graph

        This method serves the same purpose as :meth:`export_to_dotfile()`,
        but it natively returns a graph instance. For that reason,
        its usage requires the installation of the ``graphviz`` package.

        This method is typically useful in a Jupyter notebook,
        so as to visualize a scheduler in graph format  - see
        http://graphviz.readthedocs.io/en/stable/manual.html#jupyter-notebooks
        for how this works.

        The dependency from ``asynciojobs`` to ``graphviz`` is limited
        to this method and :meth:`export_as_pngfile()`,
        as it these are the only places that need it,
        and as installing ``graphviz`` can be cumbersome.

        For example, on MacOS I had to do both::

          brew install graphviz     # for the C/C++ binary stuff
          pip3 install graphviz     # for the python bindings
        """

        from graphviz import Source
        return Source(source=self.dot_format())

    def export_as_pngfile(self, filename):
        """
        Convenience wrapper that creates a png file. Like :meth:`graph()`,
        it requires the ``graphviz`` package to be installed.

        Parameters:
          filename: output filename, without the ``.png`` extension
        Returns:
          created file name

        Notes:
          - This actually uses the binary `dot` program.
          - A file named as the output but with a ``.dot`` extension
            is created as an artefact by this method.
        """
        # we refrain from using graph.format / graph.render
        # because with that method we cannot control the location
        # of the .dot file; that is dangerous when using e.g.
        #    scheduler.export_as_pngfile(__file__)
        import os
        dotfile = "{}.dot".format(filename)
        pngfile = "{}.png".format(filename)
        self.export_as_dotfile(dotfile)
        os.system("dot -Tpng {} -o {}"
                  .format(dotfile, pngfile))
        return pngfile
