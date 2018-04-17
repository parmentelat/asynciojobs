# pylint: disable=c0111,c0103

import unittest

import time

from asynciojobs import Scheduler, Job, Sequence

from .util import co_print_sleep


class TestNesting(unittest.TestCase):

    def test_nesting(self):

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
