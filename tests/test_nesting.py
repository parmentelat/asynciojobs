# pylint: disable=c0111,c0103

import unittest

import time

from asynciojobs import Scheduler, Job, Sequence

from .util import co_print_sleep


# create a small diamond scheduler
def diamond_scheduler(msg, duration):
    d = Scheduler()
    j1 = Job(co_print_sleep(f"top {msg}", duration),
             scheduler=d)
    j2 = Job(co_print_sleep(f"left {msg}", duration),
             required=j1, scheduler=d)
    j3 = Job(co_print_sleep(f"right {msg}", duration),
             required=j1, scheduler=d)
    Job(co_print_sleep(f"bottom {msg}", duration),
        required=(j2, j3), scheduler=d)
    return d


class TestNesting(unittest.TestCase):

    def test_nesting1(self):
        """
        one main scheduler in sequence
        one job
        one subscheduler that runs 2 jobs in parallel
        one job
        """

        # sub-scheduler - total approx 1 s
        subs = Scheduler()
        Job(co_print_sleep("sub short", 0.5), scheduler=subs)
        Job(co_print_sleep("sub longs", 1), scheduler=subs)

        # main scheduler - total approx 2 s
        mains = Scheduler()
        Sequence(
            Job(co_print_sleep("main begin", 0.5)),
            # this is where the subscheduler is merged
            Job(subs.co_orchestrate(), label='subscheduler'),
            Job(co_print_sleep("main end", 0.5)),
            scheduler=mains
        )

        now = time.time()
        ok = mains.run()
        self.assertTrue(ok)

        # allow for a small variation around 2s of course
        duration = time.time() - now
        self.assertAlmostEqual(duration, 2, delta=0.05)

    def test_nesting2(self):
        """
        2 sub schedulers run in parallel while
        the third main one controls them both
        """
        # sub-scheduler - total approx 1.5 s
        sub1 = diamond_scheduler("SUB1", 0.5)
        # sub-scheduler - total approx 3 s
        sub2 = diamond_scheduler("SUB2", 1)

        # main scheduler - total approx 2 s
        mains = Scheduler()
        mainj1 = Job(co_print_sleep("mainj1", 1), label="mainj1",
                     scheduler=mains)
        mainj2 = Job(sub1.co_orchestrate(), label="mainj2",
                     required=mainj1,
                     scheduler=mains)
        mainj3 = Job(sub2.co_orchestrate(), label="mainj3",
                     required=mainj1,
                     scheduler=mains)
        Job(co_print_sleep("mainj4", 1), label="mainj4",
            required=(mainj2, mainj3),
            scheduler=mains)

        now = time.time()
        ok = mains.run()
        self.assertTrue(ok)

        # allow for a small variation around 2s of course
        duration = time.time() - now
        self.assertAlmostEqual(duration, 5, delta=0.05)
