from unittest import TestCase

from asynciojobs import Scheduler, Job, Sequence

async def aprint(*messages):
    print(messages)

class CounterScheduler(Scheduler):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.counter = 0

class CounterJob(Job):
    def __init__(self, scheduler, *a, **k):
        self.scheduler = scheduler
        super().__init__(*a, **k)

    async def co_run(self):
        self.scheduler.counter += 1
        #print(f"after run : counter = {self.scheduler.counter}")

    async def co_shutdown(self, depth):
        self.scheduler.counter -= 1
        #print(f"after shutdown : counter = {self.scheduler.counter}")


class Tests(TestCase):

    def test_shutdown_simple(self):

        cardinal = 5

        s = CounterScheduler()
        s.add(Sequence(*[CounterJob(s, aprint(i))
                       for i in range(cardinal)]))

        self.assertEqual(s.counter, 0)
        s.run()
        self.assertEqual(s.counter, cardinal)
        s.shutdown()
        self.assertEqual(s.counter, 0)

    def test_shutdown_nested(self):

        cardinal = 4

        # same to the square
        top = CounterScheduler(label="TOP")
        subs = []
        for i in range(cardinal):
            sub = Scheduler(label=f"SUB {i}")
            subs.append(sub)
            sub.add(Sequence(*[CounterJob(top, aprint(10*i+j),
                                                label=str(10*i+j))
             for j in range(cardinal)]))
        top.add(Sequence(*subs))

        self.assertEqual(top.counter, 0)
        top.run()
        self.assertEqual(top.counter, cardinal*cardinal)
        top.shutdown()
        self.assertEqual(top.counter, 0)
