#!/usr/bin/env python3

import time
import traceback
import io

import asyncio

from .job import AbstractJob
from .sequence import Sequence

# will hopefully go away some day
debug = False
#debug = True

"""
An attempt at some plain markdown 
"""

class Scheduler:
    """An Scheduler instance works on a set of Job objects

    It will orchestrate them until they are all complete,
    starting with the ones that have no requirements, 
    and then starting the othe ones as their requirements are satisfied

    Running a Job means executing its `co_run()` method, which must be a coroutine

    The result of a job's `co_run()` is NOT taken into account, as
    long as it returns without raising an exception. If it does raise
    an exception, overall execution is aborted iff the job is
    critical. In all cases, the result and/or exception of each
    individual job can be inspected and retrieved individually at any
    time, including of course once the orchestration is complete.
    """

    def __init__(self,  *jobs_or_sequences, verbose=False):
        """
        Initialize from an iterable of jobs or sequences; their order is
        irrelevant.  More of these can be added later on.

        """
        self.jobs = set(Sequence._flatten(jobs_or_sequences))
        self.verbose = verbose
        ### why does it fail ?
        # bool
        self._failed_critical = False
        # False, or the intial timeout
        self._failed_timeout = False

    # think of an scheduler as a set of jobs
    def update(self, jobs):
        """
        add a collection of jobs - ditto, after `set.update()`
        """
        jobs = set(Sequence._flatten(jobs))
        self.jobs.update(jobs)

    def add(self, job):
        """
        add a single job - name is inspired from plain python `set.add()`
        """
        self.update([job])

    def failed_time_out(self):
        """
        Tells whether `orchestrate` has failed because of a time out
        """
        return self._failed_timeout

    def failed_critical(self):
        """
        Tells whether `orchestrate` has failed because 
        a critical job raised an exception
        """
        return self._failed_critical

    def why(self):
        """
        a string message explaining why orchestrate has failed
        """
        if self._failed_timeout:
            return "TIMED OUT after {}s".format(self._failed_timeout)
        elif self._failed_critical:
            return "at least one CRITICAL job has raised an exception"
        else:
            return "FINE"
        
    ####################
    def orchestrate(self, loop=None, *args, **kwds):
        """
        a synchroneous wrapper around `co_orchestrate()`
        """
        if loop is None:
            loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.co_orchestrate(loop=loop, *args, **kwds))

    ####################
    def sanitize(self):
        """
        Removes requirements that are not part of the scheduler
        This is mostly convenient in test scenarios
        In any case it is crucial that this property holds
        for orchestrate to perform properly.
        """

        for job in self.jobs:
            before = len(job.required)
            job.required &= self.jobs
            job._s_successors &= self.jobs
            after = len(job.required)
            if self.verbose and before != after:
                print(20*'*', "WARNING: job {} has had {} requirements removed"
                      .format(job, before - after))

    ####################
    def rain_check(self):
        """
        Performs minimum sanity check

        The purpose of this is primarily to check for cycles, 
        and/or missing starting points.

        It's not embedded in orchestrate because it's not strictly necessary
        but it's safer to run this before calling orchestrate if one wants 
        to type-check the jobs dependency graph early on.

        It might also help to have a sanitized scheduler, 
        but here again this is up to the caller

        RETURN:
        a boolean that is True if the topology looks clear 
        """
        try:
            for job in self.scan_in_order():
                pass
            return True
        except Exception as e:
            if self.verbose:
                print("rain_check failed", e)
            return False

    ####################
    def scan_in_order(self):
        """
        a generator function that scans the graph in the "right" order,
        i.e. starting from jobs that have no dependencies, and moving forward.

        Beware that this is not a separate iterator, so it can't be nested
        which in practice should not be a problem.
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
                if job._s_mark:
                    continue
                # if there's no requirement (first pass),
                # or later on if all requirements have already been marked,
                # then we can mark this one
                has_unmarked_requirements = False
                for required_job in job.required:
                    if required_job._s_mark is None:
                        has_unmarked_requirements = True
                if not has_unmarked_requirements:
                    job._s_mark = True
                    nb_marked += 1
                    changed = True
                    yield job
            # >= is for extra safety but it should be an exact match
            if nb_marked >= target_marked:
                # we're done
                break
            if not changed:
                # this is wrong
                raise Exception("scheduler could not be scanned - most likely because of cycles") 
        # if we still have jobs here it's not good either, although it should not happen
        # on a sanitized scheduler
        if nb_marked != target_marked:
            raise Exception("scheduler could not be scanned, {} jobs are not reachable from free jobs"
                            .format(target_marked - nb_marked))

    ####################
    def _reset_marks(self):
        """
        reset Job._s_mark on all jobs
        """
        for job in self.jobs:
            job._s_mark = None

    def _reset_tasks(self):
        """
        In case one tries to run the same scheduler twice
        """
        for job in self.jobs:
            job._task = None

    def _backlinks(self):
        """
        initialize Job._s_successors on all jobs
        as the reverse of Job.required
        """
        for job in self.jobs:
            job._s_successors = set()
        for job in self.jobs:
            for req in job.required:
                req._s_successors.add(job)

    def _ensure_future(self, job, loop):
        """
        this is the hook that lets us make sure the created Task object have a 
        backlink pointer to its correponding job
        """
        task = asyncio.ensure_future(job.co_run(), loop=loop)
        # create references back and forth between Job and asyncio.Task
        task._job = job
        job._task = task
        return task

    def _record_beginning(self, timeout):
        """
        Called once at the beginning of orchestrate, this method computes the absolute
        expiration date when a timeout is defined. 
        """
        if timeout is None:
            self.expiration = None
        else:
            self.expiration = time.time() + timeout

    def _remaining_timeout(self):
        """
        Called each time orchestrate is about to call asyncio.wait(), this method
        computes the timeout argument for wait - or None if orchestrate had no timeout
        """
        if self.expiration is None:
            return None
        else:
            return self.expiration - time.time()

    async def _tidy_tasks(self, pending):
        """
        Once orchestrate is done with its job, in order to tidy up the underlying 
        Task objects that have not completed, it is necessary to cancel them and wait for them
        according to the context, this can be with forever tasks, or because a timeout has occured
        """
        if pending:
            for task in pending:
                task.cancel()
            # wait for the forever tasks for a clean exit
            # don't bother to set a timeout, as this is expected to be immediate
            # since all tasks are canceled
            await asyncio.wait(pending)
        
    async def _tidy_tasks_exception(self, tasks):
        """
        Similar but in order to clear the exceptions, we need to run gather() instead
        """
        # do not use task._job.raised_exception() so we can use this with co_shutdown()
        # tasks as well (these are not attached to a job)
        exception_tasks = [ task for task in tasks if task._exception ]
        for task in exception_tasks:
            task.cancel()
            # if debug is turned on, provide details on the exceptions
            if debug:
                self._show_task_stack(task, "TIDYING {}"
                                      .format(task._job.repr(show_result_or_exception=False,
                                                             show_requires=False)))
        # don't bother to set a timeout, as this is expected to be immediate
        # since all tasks are canceled
        await asyncio.gather(*exception_tasks, return_exceptions=True)
        
    def _show_task_stack(self, task, msg='STACK', margin=4, limit=None):
        if isinstance(task, AbstractJob):
            task = task._task
        sep = margin * ' ' + 20 * '*'
        print(sep)
        print(sep, 'BEG ' + msg)
        print(sep)
        # naive approach would be like this, but does not support margin:
        #task.print_stack()
        stio = io.StringIO()
        task.print_stack(file=stio, limit=limit)
        stio.seek(0)
        for line in stio:
            print(margin * ' ' + line, end="")
        print(sep)
        print(sep, 'END ' + msg)
        print(sep)

    async def co_shutdown(self):
        """
        The idea here is to send a message to all the jobs once the orchestration is over
        Typically for example, several jobs sharing the same ssh connection will arrange for 
        that connection to be kept alive across an scheduler, but there is a need to tear these 
        connections down eventually
        """
        await self._feedback(None, "scheduler is shutting down...")
        tasks = [ asyncio.ensure_future(job.co_shutdown()) for job in self.jobs ]
        done, pending = await asyncio.wait(tasks, timeout = self._remaining_timeout())
        if len(pending) != 0:
            print("WARNING: {}/{} co_shutdown() methods have not returned within timeout"
                  .format(len(pending), len(self.jobs)))
            await self._tidy_tasks(pending)
        # xxx should consume any exception as well ?
        # self._tidy_tasks_exception(done)

    async def _feedback(self, jobs, state):
        """
        When self.verbose is set, provide feedback about the mentioned
        jobs having reached this state 
        if jobs is None, then state is a message to be shown as-is
        jobs may be a collection or an individual Job or Task object
        """
        if not self.verbose:
            return
        time_format = "%H-%M-%S"
        if jobs is None:
            print("{}: SCHEDULER: {}".format(time.strftime(time_format), state))
            return
        if not isinstance(jobs, (list, set, tuple)):
            jobs = jobs,
        for job in jobs:
            if not isinstance(job, AbstractJob):
                job = job._job
            print("{}: {}: {}".format(time.strftime(time_format),
                                      state, job.repr(show_result_or_exception=self.verbose,
                                                      show_requires=self.verbose)))

    async def co_orchestrate(self, loop=None, timeout=None):
        """
        the primary entry point for running an ordered set of jobs
        """
        if loop is None:
            loop = asyncio.get_event_loop()
        # initialize backlinks - i.e. _s_successors is the reverse of required
        self._backlinks()
        # clear any Task instance
        self._reset_tasks()
        # for computing global timeout
        self._record_beginning(timeout)
        # reset status
        self._failed_critical = False
        self._failed_timeout = False

        # how many jobs do we expect to complete: the ones that don't run forever
        nb_jobs_finite = len([j for j in self.jobs if not j.forever])
        # the other ones
        nb_jobs_forever = len(self.jobs) - nb_jobs_finite
        # count how many jobs have completed
        nb_jobs_done = 0

        # start with the free jobs
        entry_jobs = [ job for job in self.jobs if not job.required ]

        if not entry_jobs:
            raise ValueError("No entry points found - cannot orchestrate")
        
        if self.verbose:
            await self._feedback(None, "entering orchestrate with {} jobs"
                                .format(len(self.jobs)))

        await self._feedback(entry_jobs, "STARTING")
        
        pending = [ self._ensure_future(job, loop=loop)
                    for job in entry_jobs ]

        while True:
            done, pending \
                = await asyncio.wait(pending,
                                     timeout = self._remaining_timeout(),
                                     return_when = asyncio.FIRST_COMPLETED)

            done_ok = { t for t in done if not t._exception }
            await self._feedback(done_ok, "DONE")
            done_ko = done - done_ok
            await self._feedback(done_ko, "RAISED EXC.")
            
            # nominally we have exactly one item in done
            # it looks like the only condition where we have nothing in done is
            # because a timeout occurred
            # a little surprisingly, there are cases where done has more than one entry
            # typically when 2 jobs have very similar durations
            if not done or len(done) == 0:
                await self._feedback(None, "orchestrate: TIMEOUT occurred")
                # clean up
                await self._feedback(pending, "ABORTING")
                await self._tidy_tasks(pending)
                await self.co_shutdown()
                self._failed_timeout = timeout
                return False

            # exceptions need to be cleaned up 
            # clear the exception(s) in done
            await self._tidy_tasks_exception(done)
            # do we have at least one critical job with an exception ?
            critical_failure = False
            for done_task in done:
                done_job = done_task._job
                if done_job.raised_exception():
                    critical_failure = critical_failure or done_job.is_critical()
                    await self._feedback(done_job, "EXCEPTION occurred - on {}critical job"
                                        .format("non-" if not done_job.is_critical() else ""))
                    # make sure these ones show up even if not in debug mode
                    if debug:
                        self._show_task_stack(done_task, "DEBUG")
            if critical_failure:
                await self._tidy_tasks(pending)
                await self.co_shutdown()
                self._failed_critical = True
                await self._feedback(None, "Emergency exit upon exception in critical job")
                return False

            ### are we done ?
            # only account for not forever jobs (that may still finish, one never knows)
            done_jobs_not_forever = { j for j in done if not j._job.forever }
            nb_jobs_done += len(done_jobs_not_forever)

            if nb_jobs_done == nb_jobs_finite:
                if debug:
                    print("orchestrate: {} CLEANING UP at iteration {} / {}"
                          .format(4*'-', nb_jobs_done, nb_jobs_finite))
                assert len(pending) == nb_jobs_forever
                await self._feedback(pending, "TIDYING forever")
                await self._tidy_tasks(pending)
                await self.co_shutdown()
                return True

            # go on : find out the jobs that can be added to the mix
            # only consider the ones that are right behind any of the the jobs that just finished
            possible_next_jobs = set()
            for done_task in done:
                possible_next_jobs.update(done_task._job._s_successors)

            # find out which ones really can be added
            added = 0
            for candidate_next in possible_next_jobs:
                # do not add an job twice
                if candidate_next.is_started():
                    continue
                # we can start only if all requirements are satisfied
                # at this point entry points have is_started() -> return True so
                # they won't run this code
                requirements_ok = True
                for req in candidate_next.required:
                    if not req.is_done():
                        requirements_ok = False
                if requirements_ok:
                    await self._feedback(candidate_next, "STARTING")
                    pending.add(self._ensure_future(candidate_next, loop=loop))
                    added += 1

    ####################
    def list(self, details=False):
        """
        Print a complete list of jobs in some natural order, with their status
        summarized with a few signs.

        Beware that this might raise an exception if rain_check() has returned False
        """
        l = len(self.jobs)
        format = "{:02}" if l < 100 else "{:04}"
        # inject number in each job in their _s_label field
        for i, job in enumerate(self.scan_in_order(), 1):
            job._s_label = format.format(i)
        # so now we can refer to other jobs by their id when showing requirements
        for job in self.scan_in_order():
            print(job._s_label, job.repr(show_requires=True))
            if details and hasattr(job, 'details'):
                try:
                    details = job.details()
                    if details is not None:
                        print(details)
                except Exception as e:
                    print("<<cannot get details>>", e)
        
    def list_safe(self):
        """
        Print jobs in no specific order, works even if scheduler is broken wrt rain_check()
        """
        for i, job in enumerate(self.jobs):
            print(i, job)
        
    def debrief(self):
        """
        Designed for schedulers that have failed to orchestrate.

        Print a complete report, that includes `list()` but also gives 
        more stats and data.
        """
        nb_total =   len(self.jobs)
        done =       { j for j in self.jobs if j.is_done() }
        nb_done =    len(done)
        started =    { j for j in self.jobs if j.is_started() }
        nb_started = len(started)
        ongoing =    started - done
        nb_ongoing = len(ongoing)
        idle =       self.jobs - started
        nb_idle =    len(idle)
        
        exceptions = { j for j in self.jobs if j.raised_exception()}
        criticals =  { j for j in exceptions if j.is_critical()}

        message = "scheduler has a total of {} jobs".format(nb_total)
        def legible_message(nb, adj):
            if nb == 0: return " none is {}".format(adj)
            elif nb == 1: return " 1 is {}".format(adj)
            else : return " {} are {}".format(nb, adj)
        message += ", " + legible_message(nb_done, "done") 
        message += ", " + legible_message(nb_ongoing, "ongoing") 
        message += ", " + legible_message(nb_idle, "idle") 

        print(5 * '-', self.why())
        self.list()
        #####
        if exceptions:
            nb_exceptions  = len(exceptions)
            nb_criticals = len(criticals)
            print("===== {} job(s) with an exception, including {} critical"
                  .format(nb_exceptions, nb_criticals))
            # show critical exceptions first
            for j in self.scan_in_order():
                if j in criticals:
                    self._show_task_stack(j, "stack for CRITICAL JOB {}"
                                          .format(j.repr(show_result_or_exception=False,
                                                         show_requires=False)))
            # then exceptions that were not critical
            non_critical_exceptions = exceptions - criticals
            for j in self.scan_in_order():
                if j in non_critical_exceptions:
                    if not self.verbose:
                        print("non-critical: {}: exception {}".format(j.label(), j.raised_exception()))
                    if self.verbose:
                        self._show_task_stack(j, "non-critical job exception stack")

    def export_as_dotfile(self, filename):
        """
        Create a graph that depicts the jobs and their requires relationships
        in dot format for graphviz's `dot` utility.

        For example a PNG image can be then obtained by post-processing that dotfile with e.g. 

        `dot -Tpng foo.dot -o foo.png`
        """
        def label_to_id(job):
            return job.label().replace(' ', '_')
        with open(filename, 'w') as output:
            output.write("digraph G {\n")
            for job in self.scan_in_order():
                for r in job.required:
                    output.write("{} -> {};\n"
                                 .format(label_to_id(r),
                                         label_to_id(job)))                                 
            output.write("}\n")
        print("(Over)wrote {}".format(filename))
