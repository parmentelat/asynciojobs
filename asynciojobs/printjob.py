"""
The ``PrintJob`` class is a specialization of the
:class:`~asynciojobs.job.AbstractJob` class,
mostly useful for debugging, tests and tutorials.
"""

import asyncio

from .job import AbstractJob


class PrintJob(AbstractJob):
    """
    A job that just prints messages, and optionnally sleeps for some time.

    Parameters:

      messages: passed to ``print`` as-is
      sleep: optional, an int or float describing in seconds
        how long to sleep after the messages get printed
      banner: optional, a fixed text printed out before the messages
       like e.g. ``40*'='``; it won't make it into ``details()``
      scheduler: passed to :class:``AbstractJob``
      required: passed to :class:``AbstractJob``
      label: passed to :class:``AbstractJob``
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
        """
        Implementation of the method expected by :class:`AbstractJob`
        """
        try:
            if self.banner:
                print(self.banner + " ", end="")
            print(*self.messages)
            if self.sleep:
                print("Sleeping for {}s".format(self.sleep))
                await asyncio.sleep(self.sleep)
        except Exception:                               # pylint: disable=W0703
            # should not happen, but if it does we need to know why
            import traceback
            traceback.print_exc()

    async def co_shutdown(self):
        """
        Implementation of the method expected by :class:`AbstractJob`;
        does nothing.
        """
        pass

    def details(self):                                  # pylint: disable=C0111
        """
        Implementation of the method expected by :class:`AbstractJob`
        """
        result = ""
        if self.sleep:
            result += "[+ sleep {}s] ".format(self.sleep)
        result += "msg= "
        result += self.messages[0]
        result += "..." if len(self.messages) > 1 else ""
        return result
