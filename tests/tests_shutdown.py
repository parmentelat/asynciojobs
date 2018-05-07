# pylint: disable=c0111

import asyncio

from unittest import TestCase

from asynciojobs import Scheduler, Job, Sequence

async def aprint(*messages):
    print(messages)


class CounterScheduler(Scheduler):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.counter = 0


class CounterJob(Job):
    def __init__(self, scheduler, delay, *a, **k):
        """
        scheduler is **NOT** the scheduler where the job belongs directly
          but instead the global toplevel scheduler. This way all the jobs
          can make side effect on the counter attached there.
        delay is, in tens of seconds, the time that co_shutdown will take

        example: delay=15 -> shutdown takes 1.5 s
        """
        self.scheduler = scheduler
        self.delay = delay
        super().__init__(*a, **k)

    async def co_run(self):
        self.scheduler.counter += 1

    async def co_shutdown(self, depth):
        # delay in tens of seconds
        await asyncio.sleep(self.delay/10)
        self.scheduler.counter -= 1


class Tests(TestCase):

    def test_shutdown_simple(self):

        cardinal = 5

        sched = CounterScheduler()
        sched.add(Sequence(*[CounterJob(sched, i/10, aprint(i))
                             for i in range(cardinal)]))

        self.assertEqual(sched.counter, 0)
        self.assertTrue(sched.run())
        self.assertEqual(sched.counter, cardinal)
        self.assertTrue(sched.shutdown())
        self.assertEqual(sched.counter, 0)

    def test_shutdown_nested(self):

        cardinal = 4

        # same to the square
        top = CounterScheduler(label="TOP")
        subs = []
        for i in range(cardinal):
            sub = Scheduler(label=f"SUB {i}")
            subs.append(sub)
            sub.add(Sequence(*[CounterJob(top, 0, aprint('ok'),
                                          label=10*i+j)
                               for j in range(cardinal)]))
        top.add(Sequence(*subs))

        self.assertEqual(top.counter, 0)
        self.assertTrue(top.run())
        self.assertEqual(top.counter, cardinal*cardinal)
        self.assertTrue(top.shutdown())
        self.assertEqual(top.counter, 0)

    def test_shutdown_nested_timeout(self):

        # so here we create 16 jobs for which the shutdown
        # durations will be
        # 0.1 0.2 0.3 0.4 - 1.1 1.2 1.3 1.4
        # 2.1 2.2 2.3 2.4 - 3.1 3.2 3.3 3.4
        # so if we set shutdown_timeout = 1s, we should
        # still find counter == 12

        cardinal = 4

        # same to the square
        top = CounterScheduler(label="TOP")
        subs = []
        for i in range(cardinal):
            sub = Scheduler(label=f"SUB {i}")
            subs.append(sub)
            sub.add(Sequence(*[CounterJob(top, 10*i+j+1, aprint('ok'),
                                          label=10*i+j+1)
                               for j in range(cardinal)]))
        top.add(Sequence(*subs))

        self.assertEqual(top.counter, 0)
        self.assertTrue(top.run())
        self.assertEqual(top.counter, cardinal*cardinal)
        self.assertFalse(top.shutdown())
        self.assertEqual(top.counter, cardinal * (cardinal-1))
