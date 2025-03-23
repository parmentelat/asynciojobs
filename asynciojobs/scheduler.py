"""
The ``Scheduler`` class makes it easier to nest scheduler objects.
"""

# pylint: disable=w0212

from asynciojobs import PureScheduler
from asynciojobs import AbstractJob


class Scheduler(PureScheduler, AbstractJob):
    """
    The ``Scheduler`` class is a mixin of the two
    :class:`~asynciojobs.purescheduler.PureScheduler` and
    :class:`~asynciojobs.job.AbstractJob` classes.

    As such it can be used to create nested schedulers,
    since it is a scheduler that can contain jobs,
    and at the same time it is a job, and so it can be included in
    a scheduler.

    Parameters:
      jobs_or_sequences: passed to
        :class:`~asynciojobs.purescheduler.PureScheduler`,
        allows to add these jobs inside of the newly-created scheduler;
      jobs_window: passed to
        :class:`~asynciojobs.purescheduler.PureScheduler`;
      timeout: passed to
        :class:`~asynciojobs.purescheduler.PureScheduler`;
      shutdown_timeout: passed to
        :class:`~asynciojobs.purescheduler.PureScheduler`;
      watch (Watch): passed to
        :class:`~asynciojobs.purescheduler.PureScheduler`;
      verbose (bool): passed to
        :class:`~asynciojobs.purescheduler.PureScheduler`;
      kwds: all other named arguments are sent
        to the :class:`~asynciojobs.job.AbstractJob` constructor.


    Example:

      Here's how to create a very simple scheduler with
      an embedded sub-scheduler; the whole result is equivalent to a simple
      4-steps sequence::

        main = Scheduler(
           Sequence(
             Job(aprint("begin", duration=0.25)),
             Scheduler(
               Sequence(
                 Job(aprint("middle-begin", duration = 0.25)),
                 Job(aprint("middle-end", duration = 0.25)),
               )
             ),
             Job(aprint("end", duration=0.25)),
           )
        main.run()

    Notes:

      There can be several good reasons for using nested schedulers:

      * the scope of a ``window`` object applies to a scheduler, so a nested
        scheduler is a means to apply windoing on a specific set of jobs;
      * likewise the ``timeout`` attribute only applies to the run for the
        whole scheduler;
      * you can use ``forever`` jobs that will be terminated earlier than
        the end of the global scheduler;
      * strictly speaking, the outermost instance in this example could be an
        instance of ``PureScheduler``, but in practice it is simpler to always
        create instances of ``Scheduler``.

      Using an intermediate-level scheduler can in some case help alleviate or
      solve such issues.

    """
    def __init__(self, *jobs_or_sequences,
                 jobs_window=None, timeout=None,
                 shutdown_timeout=1,
                 watch=None, verbose=False,
                 **kwds):

        PureScheduler.__init__(self, *jobs_or_sequences,
                               jobs_window=jobs_window, timeout=timeout,
                               shutdown_timeout=shutdown_timeout,
                               watch=watch, verbose=verbose)
        AbstractJob.__init__(self, **kwds)

    async def co_run(self):
        """
        Supersedes the :meth:`~asynciojobs.puresheduler.PureScheduler.co_run`
        method in order to account for **critical** schedulers.

        `Scheduler` being a subclass of `AbstractJob`, we need to account
        for the possibility that a scheduler is defined as ``critical``.

        If the inherited ``co_run()`` method fails because
        of an exception of a timeout, a critical Scheduler will trigger an
        exception, instead of returning ``False``:

        * if orchestration failed because an internal job has raised an
          exception, raise that exception;
        * if it failed because of a timeout, raise ``TimeoutError``

        Returns:
          bool: ``True`` if everything went well;
            ``False`` for non-critical schedulers that go south.

        Raises:
          TimeoutError: for critical schedulers that do not complete in time,
          Exception: for a critical scheduler that has a critical job that
            triggers an exception, in which case it bubbles up.
        """
        # run as a pure scheduler, will always return True or False
        pure = await PureScheduler.co_run(self)
        # fine
        if pure is True:
            return pure
        # non-critical : we're done
        if not self.critical:
            return pure
        # a timeout
        if self.failed_time_out():
            raise TimeoutError("critical scheduler took too long")
        # a critical job has exploded
        if self.failed_critical():
            # need to find at least one critical job
            # that has raised an exception
            for job in self.jobs:
                if not job.critical:
                    continue
                exc = job.raised_exception()
                if exc:
                    raise exc
        # we should not reach this point
        raise ValueError("Internal error in Scheduler.co_run()")

    def _set_sched_id(self, start, id_format):
        """
        Works as a complicit to PureScheduler._set_sched_ids.
        It sets local the ``_sched_id`` attribute and returns the index
        for the next job.
        """
        # first set index on the current (kind of fake) node
        i = AbstractJob._set_sched_id(self,
                                      start, id_format)
        # go on with the jobs in sub scheduler
        return PureScheduler._set_sched_ids(self,
                                            i, id_format)

    def _job_count(self):
        """
        Complicit to PureScheduler._total_length()

        Returns:
          int: 1 + number of nodes included/nested
        """
        return 1 + self._total_length()

    def _list(self, details, depth, recursive, silence_done_jobs):
        """
        Complicit to PureScheduler.list()
        """
        indent = ('>'*depth + ' ') if depth else ''
        print("{} {} {}{} {} {} -> {}"
              .format(self.repr_id(),
                      self.repr_short(),
                      indent,
                      self.repr_main(),
                      self.repr_result(),
                      self.repr_requires(),
                      self.repr_entries()))
        if recursive:
            for job in self.topological_order():
                job._list(details, depth+1, recursive, silence_done_jobs)
            print(self.repr_id(),
                  # this should be 7-spaces like repr_short()
                  '--end--',
                  '<'*(depth+1),
                  self.repr_main(),
                  self.repr_exits())

    def _list_safe(self, recursive, silence_done_jobs):
        """
        Complicit to PureScheduler.list_safe()
        """
        print("{} {} {} {}"
              .format(self.repr_short(),
                      self.repr_id(),
                      self.repr_main(),
                      self.repr_requires()))
        if recursive:
            for job in self.jobs:
                job._list_safe(recursive, silence_done_jobs=silence_done_jobs)
            print('--end--', self.repr_id())

    def _iterate_jobs(self, scan_schedulers):
        if scan_schedulers:
            yield self
        for job in self.jobs:
            yield from job._iterate_jobs(
                scan_schedulers=scan_schedulers)

    def dot_cluster_name(self):
        """
        assigns a name to the subgraph that will represent
        a nested scheduler; dot format imposes this name to start
        with ``cluster_``
        """
        return "cluster_{}"\
               .format(self._sched_id)

    def check_cycles(self):
        """
        Supersedes
        :meth:`~asynciojobs.puresheduler.PureScheduler.check_cycles`
        to account for nested schedulers.

        Returns:
          bool: True if this scheduler, and all its nested schedulers
            at any depth, has no cycle and can be safely scheduled.
        """
        try:
            for job in self.topological_order():
                if isinstance(job, Scheduler) and not job.check_cycles():
                    return False
            return True
        except Exception as exc:                        # pylint: disable=W0703
            if self.verbose:
                print("check_cycles failed", exc)
            return False
