# pylint: disable=c0111

import asyncio

from unittest import TestCase

from asynciojobs import Scheduler, Job, Sequence

from .util import produce_svg


VERBOSE = False

def verbose(*args, **kwds):
    if not VERBOSE:
        return
    print(*args, **kwds)


async def aprint(*messages):
    print(messages)


class CounterScheduler(Scheduler):
    def __init__(self, *a, **k):
        super().__init__(*a, verbose=VERBOSE, **k)
        self.counter = 0


class CounterJob(Job):
    def __init__(self, scheduler, delay, shutdown_delay, *args, **kwds):
        """
        scheduler is **NOT** the scheduler where the job belongs directly
          but instead the global toplevel scheduler. This way all the jobs
          can make side effect on the counter attached there.
        delay is, in tens of seconds, the time that co_shutdown will take

        example: delay=15 -> shutdown takes 1.5 s
        """
        self.scheduler = scheduler
        self.delay = delay
        self.shutdown_delay = shutdown_delay
        super().__init__(*args, **kwds)

    async def co_run(self):
        verbose(f">>> CounterJob.run {self.label}")
        await asyncio.sleep(self.delay)
        self.scheduler.counter += 1
        verbose(f"<<< CounterJob.run {self.label}")

    async def co_shutdown(self):
        # delay in tens of seconds
        verbose(f">>> CounterJob.shutdown {self.label}")
        if not self.is_done():
            verbose(f"ignoring job {self.label} - is_done={self.is_done()}")
            return
        await asyncio.sleep(self.shutdown_delay)
        self.scheduler.counter -= 1
        verbose(f"<<< CounterJob.shutdown {self.label}")


class Tests(TestCase):

    # simple / sequential scheduler

    def _test_simple(self, sched_timeout):

        cardinal = 4

        sched = CounterScheduler(critical=False, timeout=sched_timeout)
        sched.add(Sequence(
            *[CounterJob(sched, delay=(i+1)/10, shutdown_delay=0,
                         corun=aprint(i),
                         label=f"simple {i}",
                         )
              for i in range(cardinal)]))

        self.assertEqual(sched.counter, 0)
        sched.run()
# shutdown is now implicit
#        self.assertEqual(sched.counter, cardinal)
#        self.assertTrue(sched.shutdown())
        self.assertEqual(sched.counter, 0)
        sched.close_all_jobs()

    def test_simple(self):
        self._test_simple(sched_timeout=None)

    def test_simple_timeout(self):
        self._test_simple(sched_timeout=0.5)


    # mostly the same with a nested scheduler

    def _test_nested(self, sched_timeout):

        cardinal = 3

        # same to the square
        top = CounterScheduler(critical=False, timeout=sched_timeout,
                               label="OUT")
        subs = []
        for i in range(cardinal):
            sub = Scheduler(label=f"SUB {i}")
            subs.append(sub)
            sub.add(Sequence(
                *[CounterJob(top, delay=(i+j)/10, shutdown_delay=0,
                             corun=aprint('ok'),
                             label=f"nested {i} x {j}")
                  for j in range(cardinal)]))
        top.add(Sequence(*subs))

        self.assertEqual(top.counter, 0)
        top.run()
# shutdown is now implicit
#        self.assertEqual(top.counter, cardinal*cardinal)
#        self.assertTrue(top.shutdown())
        self.assertEqual(top.counter, 0)

        top.close_all_jobs()

    def test_nested(self):
        self._test_nested(sched_timeout=None)

    def test_nested_timeout(self):
        self._test_nested(sched_timeout=0.5)


    # with a shutdown_timeout
    # much like the simple version but
    #
    # we create 2 pipes of <cardinal> jobs that all take 0.1s
    #
    # one of the pipes has all its jobs' shutdown() take 0.1s
    # the other has all its jobs' shutdown()        take 0.5s

    def _test_shutdown_timeout(self, sched_timeout, shutdown_timeout):

        cardinal = 4
        run_delay = 0.1
        delays = (0.1, 0.5)

        sched = CounterScheduler(critical=False,
                                 timeout=sched_timeout,
                                 shutdown_timeout=shutdown_timeout)
        for shutdown_delay in delays:
            sched.add(Sequence(
                *[CounterJob(sched, delay=run_delay,
                             shutdown_delay=shutdown_delay,
                             corun=aprint(i),
                             label=f"sched-timeout {i} x {shutdown_delay}",
                             )
                  for i in range(cardinal)]))

        self.assertEqual(sched.counter, 0)
        sched.run()

        ## compute expected remaining counter
        expected = 0
        if not sched_timeout:
            actual = cardinal
        elif sched_timeout == 0.25:
            # shutdown works only on jobs that are done,
            # so at this point we're in the middle of the third row of jobs
            # and only 2 jobs per pipe have completed
            actual = 2
        else:
            print("INTERNAL ERROR")
        ## with no execution timeout
        # all jobs have run, result will depend on
        # how shutdown_timeout compares with short and long
        short, long = delays
        if shutdown_timeout < short:
            expected = 2 * actual
        elif short <= shutdown_timeout < long:
            expected = actual
        else:
            expected = 0
        produce_svg(sched, "debug")

        self.assertEqual(sched.counter, expected)

        sched.close_all_jobs()

    def test_shsd_none_short(self):
        return self._test_shutdown_timeout(None, 0.05)
    def test_shsd_none_medium(self):
        return self._test_shutdown_timeout(None, 0.2)
    def test_shsd_none_long(self):
        return self._test_shutdown_timeout(None, 0.7)

    def test_shsd_aborted_short(self):
        return self._test_shutdown_timeout(0.25, 0.05)
    def test_shsd_aborted_medium(self):
        return self._test_shutdown_timeout(0.25, 0.2)
    def test_shsd_aborted_long(self):
        return self._test_shutdown_timeout(0.25, 0.7)
