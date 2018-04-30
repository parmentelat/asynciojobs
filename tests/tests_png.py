# pylint: disable=c0111, c0103, c0330

import unittest

from asynciojobs import Scheduler, Job, Sequence

from asynciojobs import Watch

from .util import co_print_sleep, produce_png, diamond_scheduler, pipes


class Tests(unittest.TestCase):

    def test_png_easy(self):                            # pylint: disable=r0201
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
        produce_png(sched, "test_png_easy")

    def test_png_easy2(self):                           # pylint: disable=r0201
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
        produce_png(sched, "test_png_easy2")

    def test_png_simple(self):                          # pylint: disable=r0201
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
        produce_png(sched, "test_png_simple")

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

        produce_png(sched, "test_png_styles1")

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

        produce_png(sched, "test_png_styles2")
