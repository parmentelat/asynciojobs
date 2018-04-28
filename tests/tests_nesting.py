# pylint: disable=c0111, c0103, c0330

import unittest

from asynciojobs import PureScheduler, Job, Sequence

from asynciojobs import Scheduler

from asynciojobs import Watch

from .util import co_print_sleep, produce_png, diamond_scheduler


class Tests(unittest.TestCase):

    # xxx probably useless
    def test_nesting1(self):
        """
        one main scheduler in sequence
        one job
        one subscheduler that runs 2 jobs in parallel
        one job
        """

        watch = Watch('test_nesting1')
        # sub-scheduler - total approx 1 s
        sub_sched = PureScheduler(watch=watch)
        Job(co_print_sleep(watch, 0.5, "sub short"), scheduler=sub_sched)
        Job(co_print_sleep(watch, 1, "sub longs"), scheduler=sub_sched)

        # main scheduler - total approx 2 s
        main_sched = PureScheduler(watch=watch)
        Sequence(
            Job(co_print_sleep(watch, 0.5, "main begin")),
            # this is where the subscheduler is merged
            Job(sub_sched.co_run(), label='subscheduler'),
            Job(co_print_sleep(watch, 0.5, "main end")),
            scheduler=main_sched
        )

        print("===== test_nesting1", "LIST with details")
        main_sched.list(details=True)
        ok = main_sched.run()
        self.assertTrue(ok)

        # allow for a small variation around 2s of course
        duration = watch.seconds()
        self.assertAlmostEqual(duration, 2, delta=0.05)

    def test_nesting2(self):
        """
        2 sub schedulers run in parallel while
        the third main one controls them both
        """
        watch = Watch('test_nesting2')
        # sub-scheduler - total approx 0.5 s
        sub2 = diamond_scheduler(watch, 0.5, "SUB2",
                                 scheduler_class=PureScheduler)
        sub2.watch = watch
        # sub-scheduler - total approx 1 s
        sub3 = diamond_scheduler(watch, 1, "SUB3",
                                 scheduler_class=PureScheduler)
        sub3.watch = watch

        # main scheduler - total approx
        # 0.5 + max(0.5, 1) + 0.5 = 2 s
        expected_duration = 2
        main_sched = PureScheduler(watch=watch)
        mainj1 = Job(co_print_sleep(watch, 0.5, "mainj1"), label="mainj1",
                     scheduler=main_sched)
        mainj2 = Job(sub2.co_run(), label="mainj2",
                     required=mainj1,
                     scheduler=main_sched)
        mainj3 = Job(sub3.co_run(), label="mainj3",
                     required=mainj1,
                     scheduler=main_sched)
        Job(co_print_sleep(watch, 0.5, "mainj4"), label="mainj4",
            required=(mainj2, mainj3),
            scheduler=main_sched)

        ok = main_sched.run()
        self.assertTrue(ok)

        # allow for a small variation around 2s of course
        duration = watch.seconds()
        self.assertAlmostEqual(duration, expected_duration, delta=0.05)

    def test_nesting3(self):
        """
        same as test_nesting2
        but using a Scheduler instance
        2 sub schedulers run in parallel while
        the third main one controls them both
        """

        # main scheduler - total approx
        # 0.5 + max(0.5, 1) + 0.5 = 2 s
        expected_duration = 2

        watch = Watch('test_nesting3')
        main_sched = PureScheduler(verbose=True, watch=watch)
        main_sched.label = "main3"
        mainj1 = Job(co_print_sleep(watch, 0.5, "mainj1"), label="mainj1",
                     scheduler=main_sched)

        # sub-scheduler 2 - total approx 0.5 s
        sub_sched2 = diamond_scheduler(watch, 0.5, "SUB2")
        main_sched.add(sub_sched2)
        sub_sched2.requires(mainj1)
        sub_sched2.label = "sub_sched2"
        sub_sched2.verbose = True

        # sub-scheduler 3 - total approx 1 s
        sub_sched3 = diamond_scheduler(watch, 1, "SUB3")
        main_sched.add(sub_sched3)
        sub_sched3.requires(mainj1)
        sub_sched3.label = "sub_sched3"
        sub_sched3.verbose = True

        # last job in main scheduler
        Job(co_print_sleep(watch, 0.5, "mainj4"), label="mainj4",
            required=(sub_sched2, sub_sched3),
            scheduler=main_sched)

        for s in main_sched, sub_sched2, sub_sched3:
            if not s.sanitize():
                print(f"OOPS, had to sanitize sched {s.label}")

        print("===== test_nesting3", "LIST without details")
        main_sched.list(details=False)
        produce_png(main_sched, "test_nesting3")

        watch.reset()
        print("---run")
        ok = main_sched.run()
        if not ok:
            main_sched.debrief()
        self.assertTrue(ok)

        # allow for a small variation around 2s of course
        duration = watch.seconds()
        self.assertAlmostEqual(duration, expected_duration, delta=0.05)

    def test_nesting_sequence(self):

        expected_duration = 1.

        watch = Watch('test_nesting_sequence')

        subjob = Scheduler(
            Sequence(
                Job(co_print_sleep(watch, .2, "one")),
                Job(co_print_sleep(watch, .2, "two")),
                Job(co_print_sleep(watch, .2, "three")),
            ),
            watch=watch,
        )

        main = PureScheduler(
            Sequence(
                Job(co_print_sleep(watch, .2, "BEGIN")),
                subjob,
                Job(co_print_sleep(watch, .2, "END")),
            ),
            watch=watch)

        print("===== test_nesting_sequence", "LIST with details")
        main.list(details=True)

        self.assertTrue(main.run())
        self.assertAlmostEqual(watch.seconds(), expected_duration, delta=.05)

        produce_png(main, "test_nesting_sequence")
