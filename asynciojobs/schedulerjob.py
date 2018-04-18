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


    Examples:

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

    .. note:: the most appealling reason for using nested schedulers
      lies with the use of ``forever`` jobs, that would need to be cleaned
      up before the complete end of the main scheduler. Using an
      intermediate-level scheduler can in some case help alleviate or solve
      such issues.

    """
    def __init__(self, *jobs_or_sequences,
                 verbose=False,
                 watch=None,
                 **kwds):
        Scheduler.__init__(self, *jobs_or_sequences,
                           verbose=verbose, watch=watch)
        AbstractJob.__init__(self, **kwds)

    async def co_run(self):
        await self.co_orchestrate()
