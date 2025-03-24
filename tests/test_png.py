# pylint: disable=c0111, c0103, c0330, r0201

import unittest

from asynciojobs import Scheduler, Job, Sequence

from asynciojobs import Watch

from .util import co_print_sleep, produce_svg, diamond_scheduler, pipes


class Tests(unittest.TestCase):

    def test_png_easy1(self):
        """
        start with an easy one, a sequence that has a diamond inside
        """
        watch = Watch()
        sched = Scheduler(
            Sequence(
                Job(co_print_sleep(watch, .2, "beg"),
                    label="test_easy"),
                diamond_scheduler(watch, .6, "middle"),
                Job(co_print_sleep(watch, .2, "end")),
            ),
            watch=watch
        )
        produce_svg(sched, "graphic-png-easy1")
        # avoid warning about non-awaited coroutines
        sched.close_idle_jobs()

    def test_png_easy2(self):
        """
        same but with a multi-entry/multi-exit sub-sched
        """
        watch = Watch()
        sched = Scheduler(
            Sequence(
                Job(co_print_sleep(watch, .2, "beg"),
                    label="test_png_easy2"),
                pipes(watch, .6, "middle"),
                Job(co_print_sleep(watch, .2, "end")),
            ),
            watch=watch
        )
        produce_svg(sched, "graphic-png-easy2")
        # avoid warning about non-awaited coroutines
        sched.close_idle_jobs()

    def test_png_simple(self):
        """
        a sequence that has 2 subscheds in a row
        """
        watch = Watch()
        sched = Scheduler(
            Sequence(
                Job(co_print_sleep(watch, .2, "beg"),
                    label="test_png_simple start"),
                diamond_scheduler(watch, .6, "middle-up"),
                pipes(watch, .6, "middle-down"),
                Job(co_print_sleep(watch, .2, "end"),
                    label="test_png_simple end"),
            ),
            watch=watch
        )
        produce_svg(sched, "graphic-png-simple")
        # avoid warning about non-awaited coroutines
        sched.close_idle_jobs()

    def test_png_styles1(self):
        """
        trying the rendering of critical and forever jobs
        """
        watch = Watch()
        sched = Scheduler(
            Sequence(
                Job(co_print_sleep(watch, .1, "regular"),
                    label="regular",
                    critical=False, forever=False),
                Job(co_print_sleep(watch, .1, "critical"),
                    label="critical",
                    critical=True, forever=False),
                Job(co_print_sleep(watch, .1, "forever"),
                    label="forever",
                    critical=False, forever=True),
                Job(co_print_sleep(watch, .1, "both"),
                    label="both",
                    critical=True, forever=True),
            ),
            watch=watch,
        )

        produce_svg(sched, "graphic-png-styles1")
        # avoid warning about non-awaited coroutines
        sched.close_idle_jobs()

    def test_png_styles2(self):
        """
        trying the rendering of critical and forever jobs
        """
        watch = Watch()

        j1 = pipes(watch, .5, "none", nb_pipes=6)
        j1.critical = False
        j1.forever = False
        j1.label = "label-none"

        j2 = diamond_scheduler(watch, .5, "critical")
        j2.critical = True
        j2.forever = False
        j2.label = "label-critical"

        j3 = diamond_scheduler(watch, .5, "forever")
        j3.critical = False
        j3.forever = True
        j3.label = "label-forever"

        j4 = diamond_scheduler(watch, .5, "both")
        j4.critical = True
        j4.forever = True
        j4.label = "label-both"

        sched = Scheduler(
            Sequence(j1, j2, j3, j4),
            watch=watch,
        )

        produce_svg(sched, "graphic-png-styles2")
        # avoid warning about non-awaited coroutines
        sched.close_idle_jobs()


    def test_order1(self):

        async def aprint(x):
            print(x)

        def job(n):
            return Job(aprint(n), label=n)

        sub1, sub2, sub3, sub4 = Scheduler(), Scheduler(), Scheduler(), Scheduler()

        sched = Scheduler(
            Sequence(
                job('top'),
                sub1,
                job('middle'),
                sub2,
                sub3,
                sub4))

        for i in range(3):
            sub1.add(job(i+1))
            sub2.add(job(i+4))
            sub3.add(job(i+7))
            sub4.add(job(i+10))

        sub4.add(job(13))

        produce_svg(sched, "graphic-png-order1")
        # avoid warning about non-awaited coroutines
        sched.close_idle_jobs()
