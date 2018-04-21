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
                    label="test_easy"),
                diamond_scheduler(watch, .6, "middle-up"),
                pipes(watch, .6, "middle-down"),
                Job(co_print_sleep(watch, .2, "end")),
            ),
            watch=watch
        )
        produce_png(sched, "test_png_simple")
