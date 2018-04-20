from asynciojobs import Scheduler

from asynciojobs import AbstractJob

"""
The ``SchedulerJob`` class makes it easier to nest scheduler objects.
"""


class SchedulerJob(Scheduler, AbstractJob):
    """
    The ``SchedulerJob`` class is a mixin of the two
    :class:`~asynciojobs.scheduler.Scheduler` and
    :class:`~asynciojobs.job.AbstractJob` classes.

    As such it can be used to create nested schedulers,
    since it is a scheduler that can contain jobs,
    and at the same time it is a job, and so it can be included in
    a scheduler.

    Parameters:
      jobs_or_sequences: passed to :class:`~asynciojobs.scheduler.Scheduler`,
        allows to add these jobs inside of the newly-created scheduler;
      verbose (bool): passed to
        :class:`~asynciojobs.scheduler.Scheduler`;
      watch (Watch): passed to :class:`~asynciojobs.scheduler.Scheduler`;
      kwds: all other named arguments are sent
        to the :class:`~asynciojobs.job.AbstractJob` constructor.


    Example:

      Here's how to create a very simple scheduler with
      an embedded sub-scheduler; the whole result is equivalent to a simple
      4-steps sequence::

        main = Scheduler(
           Sequence(
             Job(aprint("begin", duration=0.25)),
             SchedulerJob(
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

      Using an intermediate-level scheduler can in some case help alleviate or
      solve such issues.

      **XXX** However, at this point, the following remains **TODO**:

      * need to add timeout and window settings as attributes
        in the scheduler object
      * because otherwise right now, the good aspects of using
        scheduler-jobs a.k.a. subschedulers
        are not available because co_run() on a scheduler expects these as
        arguments, and one cannot store these attributes in the scheduler
        object itself.


    """
    def __init__(self, *jobs_or_sequences,
                 verbose=False,
                 watch=None,
                 **kwds):
        Scheduler.__init__(self, *jobs_or_sequences,
                           verbose=verbose, watch=watch)
        AbstractJob.__init__(self, **kwds)

    def _set_sched_id(self, start, id_format):
        """
        Works as a complicit to Scheduler._set_sched_ids.
        It sets local the ``_sched_id`` attribute and returns the index
        for the next job.
        """
        # first set index on the current (kind of fake) node
        i = AbstractJob._set_sched_id(self,             # pylint: disable=w0212
                                      start, id_format)
        # go on with the jobs in sub scheduler
        return Scheduler._set_sched_ids(self,           # pylint: disable=w0212
                                        i, id_format)

    def _job_count(self):
        """
        Complicit to Scheduler._total_length()

        Returns:
          int: 1 + number of nodes included/nested
        """
        return 1 + self._total_length()

    def _list(self, details, depth):
        """
        Complicit to Scheduler.list()
        """
        if details:
            print('>'*(depth+1), "{} {} with {} jobs"
                  .format(type(self).__name__,
                          self._get_text_label(),
                          len(self)))
        for job in self.topological_order():
            job._list(details, depth+1)                 # pylint: disable=W0212
        if details:
            print('<'*(depth+1), type(self).__name__)
