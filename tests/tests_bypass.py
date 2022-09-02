# pylint: disable=c0111, c0103, r0201

import unittest

from asynciojobs import PureScheduler, Scheduler, Job, Sequence, Watch

from .util import co_print_sleep


class Tests(unittest.TestCase):

    def test_bypass_1(self):

        watch = Watch()

        def job_in_s(i, s):
            return Job(co_print_sleep(watch, .2, f"job {i}"),
                       label=f"job{i}",
                       scheduler=s)

        s = Scheduler()
        j1, j2, j3, j4, j5 = [job_in_s(i, s) for i in range(1, 6)]
        j5.requires(j4.requires(j3.requires(j2.requires(j1))))

        # print("DEBRIEF before")
        # s.debrief()

        s.bypass_and_remove(j3)
        self.assertFalse(j3 in s.jobs)
        self.assertTrue(j2 in j4.required)

        # print("DEBRIEF after")
        # s.debrief()

