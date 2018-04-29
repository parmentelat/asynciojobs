"""
The ``Scheduler`` class makes it easier to nest scheduler objects.
"""

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
                 watch=None, verbose=False,
                 **kwds):

        PureScheduler.__init__(self, *jobs_or_sequences,
                               jobs_window=jobs_window, timeout=timeout,
                               verbose=verbose, watch=watch)
        AbstractJob.__init__(self, **kwds)

    def _set_sched_id(self, start, id_format):
        """
        Works as a complicit to PureScheduler._set_sched_ids.
        It sets local the ``_sched_id`` attribute and returns the index
        for the next job.
        """
        # first set index on the current (kind of fake) node
        i = AbstractJob._set_sched_id(self,             # pylint: disable=w0212
                                      start, id_format)
        # go on with the jobs in sub scheduler
        return PureScheduler._set_sched_ids(self,       # pylint: disable=w0212
                                            i, id_format)

    def _job_count(self):
        """
        Complicit to PureScheduler._total_length()

        Returns:
          int: 1 + number of nodes included/nested
        """
        return 1 + self._total_length()

    def _list(self, details, depth):
        """
        Complicit to PureScheduler.list()
        """
        print(self.repr_id(),
              self.repr_short(),
              '>'*(depth+1),
              self.repr_main(),
              "{} -> {}".format(self.repr_requires(),
                                self.repr_entries()))
        for job in self.topological_order():
            job._list(details, depth+1)                 # pylint: disable=W0212
        print(self.repr_id(),
              # this should be 7-spaces like repr_short()
              '  end  ',
              '<'*(depth+1),
              self.repr_main(),
              self.repr_exits())

    def dot_cluster_name(self):
        """
        assigns a name to the subgraph that will represent
        a nested scheduler; dot format imposes this name to start
        with ``cluster_`
        """
        return "cluster_{}"\
               .format(self._sched_id)
