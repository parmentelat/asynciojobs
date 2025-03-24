# pylint: disable=c0111, c0103, c0330

import unittest

from asynciojobs import PureScheduler, Job, Sequence

from asynciojobs import Scheduler

from asynciojobs import Watch

from .util import co_print_sleep, produce_svg, diamond_scheduler


class BoomError(Exception):
    pass


async def boom(message):
    raise BoomError(message)


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
        produce_svg(main_sched, "graphic-nesting3")

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
            label="sub-scheduler\non several lines",
            critical=True, forever=True,
        )

        main = Scheduler(
            Sequence(
                Job(co_print_sleep(watch, .2, "BEGIN"),
                    label="job-label"),
                subjob,
                Job(co_print_sleep(watch, .2, "END")),
            ),
            watch=watch)

        print("===== test_nesting_sequence", "LIST with details")
        main.list(details=True)

        self.assertTrue(main.run())
        self.assertAlmostEqual(watch.seconds(), expected_duration, delta=.05)

        produce_svg(main, "graphic-nesting-sequence")

    def test_critical_exc(self):

        def sched_boom(s_crit, j_crit):
            return Scheduler(
                    Job(boom(str(j_crit)), critical=j_crit),
                    critical=s_crit)

        # regular non-critical schedulers should not raise anything
        # returns True as Job is not critical
        sched = sched_boom(False, False)
        self.assertTrue(sched.run())
        sched.close_idle_jobs()
        # returns False as Job is critical
        sched = sched_boom(False, True)
        self.assertFalse(sched.run())
        sched.close_idle_jobs()

        # it's a different business for critical schedulers
        # Job is not critical, so returns True
        sched = sched_boom(True, False)
        self.assertTrue(sched.run())
        sched.close_idle_jobs()

        # Job is not critical, so raise BoomError
        with self.assertRaises(BoomError):
            sched = sched_boom(True, True)
            sched.run()
        sched.close_all_jobs()

    def test_critical_exc2(self):

        def sched_sched_boom(s1_crit, s2_crit, j_crit):
            return Scheduler(
                    Scheduler(
                        Job(boom("ok"), critical=j_crit,
                            label=f"boom {j_crit}"),
                        critical=s2_crit,
                        label=f"internal {s2_crit}"
                        ),
                    critical=s1_crit,
                    label=f"external {s1_crit}")

        # regular non-critical schedulers should not raise anything
        # returns True as Job is not critical
        s = sched_sched_boom(False, False, False)
        self.assertTrue(s.run())
        s = sched_sched_boom(False, False, True)
        self.assertTrue(s.run())
        s = sched_sched_boom(False, True, False)
        self.assertTrue(s.run())
        s = sched_sched_boom(False, True, True)
        self.assertFalse(s.run())

        # it's a different business for critical schedulers
        # Job is not critical, so returns True
        s = sched_sched_boom(True, False, False)
        self.assertTrue(s.run())
        s = sched_sched_boom(True, False, True)
        self.assertTrue(s.run())
        s = sched_sched_boom(True, True, False)
        self.assertTrue(s.run())
        with self.assertRaises(BoomError):
            s = sched_sched_boom(True, True, True)
            s.run()

    def test_sanitize(self):

        watch = Watch()

        def job(i):
            return Job(co_print_sleep(watch, 0.1, f"job{i}"),
                       label=i)

        def simple():
            all = j1, j2, j3, j4, j5 = [job(i) for i in range(1, 6)]
            sched1 = Scheduler(j1, j2, j3, label='top simple')
            j2.requires(j4)
            j3.requires(j5)
            self.assertEqual(len(j2.required), 1)
            self.assertEqual(len(j3.required), 1)
            sched1.sanitize()
            self.assertEqual(len(j2.required), 0)
            self.assertEqual(len(j3.required), 0)

            for j in all:
                j.close()

        def nested():
            all1 = j11, j12, j13, j14, j15 = [job(i) for i in range(11, 16)]
            sched2 = Scheduler(Sequence(j11, j12, j13), label="nested internal")
            j12.requires(j14)
            j13.requires(j15)

            all = j1, j2, j3, j4, j5 = [job(i) for i in range(1, 6)]
            s1 = Scheduler(Sequence(j1, sched2, j3), label="nested top")
            j1.requires(j4)
            j1.requires(j11)

            sched2.requires(j13)

            # j2 not included in sched, untouched
            j2.requires(j1)

            self.assertEqual(len(j12.required), 2)
            self.assertEqual(len(j13.required), 2)
            self.assertEqual(len(j1.required), 2)
            self.assertEqual(len(sched2.required), 2)
            self.assertEqual(len(j3.required), 1)
            s1.sanitize()
            self.assertEqual(len(j12.required), 1)
            self.assertEqual(len(j13.required), 1)
            self.assertEqual(len(j1.required), 0)
            self.assertEqual(len(sched2.required), 1)
            self.assertEqual(len(j3.required), 1)

            for j in (*all, *all1):
                j.close()

        simple()
        nested()
