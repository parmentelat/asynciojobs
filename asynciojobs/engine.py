#!/usr/bin/env python3

import time
import asyncio

from .job import AbstractJob
from .sequence import Sequence

class Engine:
    """
    An Engine instance works on a set of Job objects

    It will orchestrate them until they are all complete,
    starting with the ones that have no requirements, 
    and then starting the othe ones as their requirements are satisfied

    Running a Job means executing its co_run() method, which must be a coroutine

    As of this rough/early implementation: 
    (*) the result of `co_run` is NOT taken into account to implement some
        logic about how the overall job should behave. Instead the result and/or exception
        of each individual job can be retrieved individually once the orchestration is complete

    """

    default_critical = False

    def __init__(self,  *jobs_or_sequences, critical=None, verbose=False, debug=False):
        self.jobs = set(Sequence.flatten(jobs_or_sequences))
        if critical is None:
            critical = self.default_critical
        self.critical = critical
        # why does it fail ?
        self._critical_stop = False
        self._timed_out = False
        self.verbose = verbose
        self.debug = debug

    # think of an engine as a set of jobs
    def update(self, jobs):
        self.jobs.update(jobs)

    def add(self, job):
        self.jobs.add(job)

    def is_critical(self):
        return self.critical

    def why(self):
        """
        a string message explaining why orchestrate has failed
        """
        if self._timed_out:
            return "TIMED OUT"
        elif self._critical_stop:
            return "at least one CRITICAL job has raised an exception"
        else:
            return "FINE"
        
    def _reset_marks(self):
        """
        reset Job._mark on all jobs
        """
        for job in self.jobs:
            job._mark = None

    def _reset_tasks(self):
        """
        In case one tries to run the same engine twice
        """
        for job in self.jobs:
            job._task = None

    def _backlinks(self):
        """
        initialize Job._successors on all jobs
        as the reverse of Job.required
        """
        for job in self.jobs:
            job._successors = set()
        for job in self.jobs:
            for req in job.required:
                req._successors.add(job)

    ####################
    def orchestrate(self, loop=None, *args, **kwds):
        if loop is None:
            loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.co_orchestrate(loop=loop, *args, **kwds))

    ####################
    def sanitize(self, verbose=True):
        """
        Removes requirements that are not part of the engine
        This is mostly convenient in many test scenarios
        but in any case it is crucial that this property holds
        for orchestrate to perform properly
        """

        for job in self.jobs:
            before = len(job.required)
            job.required &= self.jobs
            job._successors &= self.jobs
            after = len(job.required)
            if verbose and before != after:
                print(20*'*', "WARNING: job {} has had {} requirements removed"
                      .format(job, before - after))

    ####################
    def rain_check(self):
        """
        performs minimum sanity check

        NOTE: the purpose of this is primarily to check for cycles
        it's not embedded in orchestrate because it's not strictly necessary
        but it's safer to run this before calling orchestrate if one wants 
        to type-check the jobs dependency graph early on

        it might also help to have a sanitized engine, 
        but here again this is up to the caller

        RETURN:
        a boolean that is True if the topology looks clear 
        """
        try:
            for job in self.scan_in_order():
                pass
            return True
        except Exception as e:
            if self.debug:
                print("rain_check failed", e)
            return False

    ####################
    def scan_in_order(self):
        """
        a generator function that scans the graph in the "right" order,
        i.e. starting from jobs that hav no dependencies and moving forward

        beware that this is not a separate iterator, so it can't be nested
        which in practice hould not be a problem
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
                if job._mark:
                    continue
                # if there's no requirement (first pass),
                # or later on if all requirements have already been marked,
                # then we can mark this one
                has_unmarked_requirements = False
                for required_job in job.required:
                    if required_job._mark is None:
                        has_unmarked_requirements = True
                if not has_unmarked_requirements:
                    job._mark = True
                    nb_marked += 1
                    changed = True
#                    if self.debug:
#                        print("rain_check: {}/{}, new={}"
#                              .format(nb_marked, target_marked, job))
                    yield job
            # >= is for extra safety but it should be an exact match
            if nb_marked >= target_marked:
                # we're done
                break
            if not changed:
                # this is wrong
                raise Exception("engine could not be scanned - most likely because of cycles") 
        # if we still have jobs here it's not good either, although it should not happen
        # on a sanitized engine
        if nb_marked != target_marked:
            raise Exception("engine could not be scanned, {} jobs are not reachable from free jobs"
                            .format(target_marked - nb_marked))

    ####################
    def ensure_future(self, job, loop):
        """
        this is the hook that lets us make sure the created Task object have a 
        backlink pointer to its correponding job
        """
        task = asyncio.ensure_future(job.co_run(), loop=loop)
        # create references back and forth between Job and asyncio.Task
        task._job = job
        job._task = task
        return task

    def mark_beginning(self, timeout):
        """
        Called once at the beginning of orchestrate, this method computes the absolute
        expiration date when a timeout is defined. 
        """
        if timeout is None:
            self.expiration = None
        else:
            self.expiration = time.time() + timeout

    def remaining_timeout(self):
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
            if self.debug:
                self.show_task_stack(task)
        # don't bother to set a timeout, as this is expected to be immediate
        # since all tasks are canceled
        await asyncio.gather(*exception_tasks, return_exceptions=True)
        
    def show_task_stack(self, task, msg='STACK'):
        if isinstance(task, AbstractJob):
            task = task._task
        sep = 20 * '*'
        print(sep)
        print(sep, 'BEG ' + msg)
        print(sep)
        task.print_stack()
        print(sep)
        print(sep, 'END ' + msg)
        print(sep)

    async def co_shutdown(self):
        """
        The idea here is to send a message to all the jobs once the orchestration is over
        Typically for example, several jobs sharing the same ssh connection will arrange for 
        that connection to be kept alive across an engine, but there is a need to tear these 
        connections down eventually
        """
        await self.feedback(None, "engine is shutting down...")
        tasks = [ asyncio.ensure_future(job.co_shutdown()) for job in self.jobs ]
        done, pending = await asyncio.wait(tasks, timeout = self.remaining_timeout())
        if len(pending) != 0:
            print("WARNING: {}/{} co_shutdown() methods have not returned within timeout"
                  .format(len(pending), len(self.jobs)))
            await self._tidy_tasks(pending)
        # xxx should consume any exception as well ?
        # self._tidy_tasks_exception(done)

    async def feedback(self, jobs, state):
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
            print("{}: ENGINE: {}".format(time.strftime(time_format), state))
            return
        if not isinstance(jobs, (list, set, tuple)):
            jobs = jobs,
        for job in jobs:
            if not isinstance(job, AbstractJob):
                job = job._job
            print("{}: {}: {}".format(time.strftime(time_format), state, job.nice(self.debug)))

    async def co_orchestrate(self, loop=None, timeout=None):
        """
        the primary entry point for running an ordered set of jobs
        """
        if loop is None:
            loop = asyncio.get_event_loop()
        # initialize backlinks - i.e. _successors is the reverse of required
        self._backlinks()
        # clear any Task instance
        self._reset_tasks()
        # for computing global timeout
        self.mark_beginning(timeout)
        # reset status
        self._critical_stop = False
        self._timed_out = False

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
        
        await self.feedback(entry_jobs, "STARTING")
        
        pending = [ self.ensure_future(job, loop=loop)
                    for job in entry_jobs ]

        while True:
            done, pending \
                = await asyncio.wait(pending,
                                     timeout = self.remaining_timeout(),
                                     return_when = asyncio.FIRST_COMPLETED)

            await self.feedback(done, "DONE")
            # nominally we have exactly one item in done
            # it looks like the only condition where we have nothing in done is
            # because a timeout occurred
            if not done or len(done) == 0:
                await self.feedback(None, "orchestrate: TIMEOUT occurred")
                # clean up
                await self.feedback(pending, "ABORTING")
                await self._tidy_tasks(pending)
                await self.co_shutdown()
                self._timed_out = True
                return False

            # a little surprisingly, there might be cases where done has more than one entry
            # typically when 2 jobs have very similar durations

            ### are we done ?
            # only account for not forever jobs (that may still finish, one never knows)
            done_jobs_not_forever = { j for j in done if not j._job.forever }
            nb_jobs_done += len(done_jobs_not_forever)
            if nb_jobs_done == nb_jobs_finite:
                if self.debug:
                    print("orchestrate: {} CLEANING UP at iteration {} / {}"
                          .format(4*'-', nb_jobs_done, nb_jobs_finite))
                assert len(pending) == nb_jobs_forever
                await self.feedback(pending, "TIDYING forever")
                await self._tidy_tasks(pending)
                await self.co_shutdown()
                return True

            # exceptions need to be cleaned up 
            # clear the exception
            await self._tidy_tasks_exception(done)
            # do we have at least one critical job with an exception ?
            critical = False
            for done_task in done:
                done_job = done_task._job
                if done_job.raised_exception():
                    critical = critical or done_job.is_critical(self)
                    await self.feedback(done_job, "EXCEPTION occurred - critical = {}".format(critical))
                    # make sure these ones show up even if not in debug mode
                    if not self.debug:
                        self.show_task_stack(done_task)                    
            if critical:
                await self._tidy_tasks(pending)
                await self.co_shutdown()
                self._critical_stop = True
                await self.feedback(None, "Emergency exit upon exception in critical job")
                return False

            # go on : find out the jobs that can be added to the mix
            # only consider the ones that are right behind any of the the jobs that just finished
            possible_next_jobs = set()
            for done_task in done:
                possible_next_jobs.update(done_task._job._successors)

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
                    await self.feedback(candidate_next, "STARTING")
                    pending.add(self.ensure_future(candidate_next, loop=loop))
                    added += 1

    ####################
    def list(self, sep=None):
        """
        print jobs in some natural order
        beware that this might raise an exception if rain_check() has returned False
        """
        if sep:
            print(sep)
        for i, job in enumerate(self.scan_in_order()):
            print(i, job)
        if sep:
            print(sep)
        
    def list_safe(self, sep=None):
        """
        print jobs as sorted in self.jobs
        """
        if sep:
            print(sep)
        for i, job in enumerate(self.jobs):
            print(i, job)
        if sep:
            print(sep)
        
    def debrief(self, verbose=False, sep=None):
        """
        Uses an object that has gone through orchestration
        and displays a listing of what has gone wrong
        Mostly useful if orchestrate() returned False
        """
        nb_total =   len(self.jobs)
        done =       { j for j in self.jobs if j.is_done() }
        nb_done =    len(done)
        exceptions = { j for j in self.jobs if j.raised_exception()}
        criticals =  { j for j in exceptions if j.is_critical(self)}

        if sep:
            print(sep)
        print("========== {} jobs done / {} total -- {}".format(nb_done, nb_total, self.why()))
        if exceptions:
            nb_exceptions  = len(exceptions)
            nb_criticals = len(criticals)
            print("===== {} jobs with an exception, including {} critical"
                  .format(nb_exceptions, nb_criticals))
            # show critical exceptions first
            for j in self.scan_in_order():
                if j in criticals:
                    if not verbose:
                        print("CRITICAL: {}: exception {}".format(j.label, j.raised_exception()))
                    else:
                        self.show_task_stack(j, "CRITICAL job exception stack")
            # then exceptions that were not critical
            non_critical_exceptions = exceptions - criticals
            for j in self.scan_in_order():
                if j in non_critical_exceptions:
                    if not verbose:
                        print("non-critical: {}: exception {}".format(j.label, j.raised_exception()))
                    if verbose:
                        self.show_task_stack(j, "non-critical job exception stack")
        if nb_done != nb_total:
            print("===== {} unfinished jobs".format(nb_total - nb_done))
            for j in self.jobs - done:
                  print("UNFINISHED {}".format(j))
        if sep:
            print(sep)
