# pylint: disable=c0111, c0103, c0330

import unittest

from asynciojobs import Scheduler, Job, Sequence

from asynciojobs import SchedulerJob

from asynciojobs import Watch

from .util import co_print_sleep


# create a small diamond scheduler
# total duration = 2 * duration
def diamond_scheduler(watch, duration, msg, scheduler_class=Scheduler):
    d = scheduler_class(watch=watch)
    j1 = Job(co_print_sleep(watch, duration/2, f"top {msg}"),
             label=f"top {msg}1",
             scheduler=d)
    j2 = Job(co_print_sleep(watch, duration, f"left {msg}"),
             label=f"left {msg}",
             required=j1, scheduler=d)
    j3 = Job(co_print_sleep(watch, duration, f"right {msg}", ),
             label=f"right {msg}",
             required=j1, scheduler=d)
    Job(co_print_sleep(watch, duration / 2, f"bottom {msg}"),
        label=f"bottom {msg}",
        required=(j2, j3), scheduler=d)
    return d


class Tests(unittest.TestCase):

    def test_nesting1(self):
        """
        one main scheduler in sequence
        one job
        one subscheduler that runs 2 jobs in parallel
        one job
        """

        watch = Watch('test_nesting1')
        # sub-scheduler - total approx 1 s
        subs = Scheduler(watch=watch)
        Job(co_print_sleep(watch, 0.5, "sub short"), scheduler=subs)
        Job(co_print_sleep(watch, 1, "sub longs"), scheduler=subs)

        # main scheduler - total approx 2 s
        mains = Scheduler(watch=watch)
        Sequence(
            Job(co_print_sleep(watch, 0.5, "main begin")),
            # this is where the subscheduler is merged
            Job(subs.co_run(), label='subscheduler'),
            Job(co_print_sleep(watch, 0.5, "main end")),
            scheduler=mains
        )

        print("===== test_nesting1", "LIST with details")
        mains.list(details=True)
        ok = mains.run()
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
        sub2 = diamond_scheduler(watch, 0.25, "SUB2")
        sub2.watch = watch
        # sub-scheduler - total approx 1 s
        sub3 = diamond_scheduler(watch, 0.5, "SUB3")
        sub3.watch = watch

        # main scheduler - total approx
        # 0.5 + max(0.5, 1) + 0.5 = 2 s
        expected_duration = 2
        mains = Scheduler(watch=watch)
        mainj1 = Job(co_print_sleep(watch, 0.5, "mainj1"), label="mainj1",
                     scheduler=mains)
        mainj2 = Job(sub2.co_run(), label="mainj2",
                     required=mainj1,
                     scheduler=mains)
        mainj3 = Job(sub3.co_run(), label="mainj3",
                     required=mainj1,
                     scheduler=mains)
        Job(co_print_sleep(watch, 0.5, "mainj4"), label="mainj4",
            required=(mainj2, mainj3),
            scheduler=mains)

        ok = mains.run()
        self.assertTrue(ok)

        # allow for a small variation around 2s of course
        duration = watch.seconds()
        self.assertAlmostEqual(duration, expected_duration, delta=0.05)

    def test_nesting3(self):
        """
        same as test_nesting2
        but using a SchedulerJob instance
        2 sub schedulers run in parallel while
        the third main one controls them both
        """

        # main scheduler - total approx
        # 0.5 + max(0.5, 1) + 0.5 = 2 s
        expected_duration = 2

        watch = Watch('test_nesting3')
        mains = Scheduler(verbose=True, watch=watch)
        mains.label = "main3"
        mainj1 = Job(co_print_sleep(watch, 0.5, "mainj1"), label="mainj1",
                     scheduler=mains)

        # sub-scheduler 2 - total approx 0.5 s
        subsched2 = diamond_scheduler(watch, 0.25, "SUB2", SchedulerJob)
        mains.add(subsched2)
        subsched2.requires(mainj1)
        subsched2.label = "subsched2"
        subsched2.verbose = True

        # sub-scheduler 3 - total approx 1 s
        subsched3 = diamond_scheduler(watch, 0.5, "SUB3", SchedulerJob)
        mains.add(subsched3)
        subsched3.requires(mainj1)
        subsched3.label = "subsched3"
        subsched3.verbose = True

        # last job in main scheduler
        Job(co_print_sleep(watch, 0.5, "mainj4"), label="mainj4",
            required=(subsched2, subsched3),
            scheduler=mains)

        for s in mains, subsched2, subsched3:
            if not s.sanitize():
                print(f"OOPS, had to sanitize sched {s.label}")

        print("===== test_nesting3", "LIST without details")
        mains.list(details=False)
        return
        print("===== test_nesting3", "LIST with details")
        mains.list(details=True)

        print("---run")
        ok = mains.run()
        if not ok:
            mains.debrief()
        self.assertTrue(ok)

        # allow for a small variation around 2s of course
        duration = watch.seconds()
        self.assertAlmostEqual(duration, expected_duration, delta=0.05)

    def test_nesting_sequence(self):

        expected_duration = 1.

        watch = Watch('test_nesting_sequence')

        subjob = SchedulerJob(
            Sequence(
                Job(co_print_sleep(watch, .2, "one")),
                Job(co_print_sleep(watch, .2, "two")),
                Job(co_print_sleep(watch, .2, "three")),
            ),
            watch=watch,
        )

        main = Scheduler(
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

    def test_nesting_sequence2(self):

        expected_duration = 1.
        watch = Watch('test_nesting_sequence')

        main = Scheduler(
            Sequence(
              Job(co_print_sleep(watch, .2, "BEGIN")),
              SchedulerJob(
                Sequence(
                  Job(co_print_sleep(watch, .2, "one")),
                  Job(co_print_sleep(watch, .2, "two")),
                  Job(co_print_sleep(watch, .2, "three")),
                ),
                watch=watch,
              ),
              Job(co_print_sleep(watch, .2, "END")),
            ),
            watch=watch)

        print("===== test_nesting_sequence2", "LIST with details")
        main.list(details=True)

        self.assertTrue(main.run())
        self.assertAlmostEqual(watch.seconds(), expected_duration, delta=.05)
