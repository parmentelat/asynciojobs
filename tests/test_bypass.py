# pylint: disable=c0111, c0103, r0201

from re import M
import unittest

from asynciojobs import *
from .util import *

def job_in_s_w(s, w, i):
    return Job(
        co_print_sleep(w, .2, f"job {i}"),
        label=f"job{i}",
        scheduler=s)


class Tests(unittest.TestCase):

    def test_bypass1(self):

        w = Watch()
        s = Scheduler()

        j1, j2, j3, j4, j5 = [job_in_s_w(s, w, i) for i in range(1, 6)]
        j5.requires(
            j4.requires(
                j3.requires(
                    j2.requires(j1))))
        self.assertEqual(s.successors_downstream(j1), {j2, j3, j4, j5})
        self.assertEqual(s.predecessors_upstream(j5), {j1, j2, j3, j4})
        produce_svg(s, "graphic-bypass1-step0")


        s.bypass_and_remove(j3)
        self.assertTrue(s.sanitize())
        self.assertFalse(j3 in s.jobs)
        self.assertTrue(j2 in j4.required)
        produce_svg(s, "graphic-bypass1-step1")

    def test_bypass2(self):

        w = Watch()
        s = Scheduler()

        j1, j2, j3, j4, j5 = [job_in_s_w(s, w, i) for i in range(1, 6)]
        j5.requires(
            j4.requires(
                j3.requires(j1),
                j2.requires(j1)))
        self.assertEqual(s.successors_downstream(j1), {j2, j3, j4, j5})
        self.assertEqual(s.successors_downstream(j2), {j4, j5})
        self.assertEqual(s.successors_downstream(j3), {j4, j5})
        self.assertEqual(s.predecessors_upstream(j4), {j1, j2, j3})
        produce_svg(s, "graphic-bypass2-step0")

        s.bypass_and_remove(j4)
        self.assertTrue(s.sanitize())
        self.assertFalse(j4 in s.jobs)
        self.assertTrue(j2 in j5.required)
        self.assertTrue(j3 in j5.required)
        self.assertEqual(s.successors_downstream(j1), {j2, j3, j5})
        self.assertEqual(s.predecessors_upstream(j5), {j1, j2, j3})
        produce_svg(s, "graphic-bypass2-step1")

    def diamonds(self, n):
        r"""
        n should be 2 or 3

        with n=2 this returns a watch, a scheduler with 7 jobs
        j1 - j2 - j4 - j5 - j7
           \ j3 /    \ j6 /
        with n=3 it returns a watch, a scheduler with 10 jobs
        j1 - j2 - j4 - j5 - j7 - j8 - j10
           \ j3 /    \ j6 /    \ j9 /
        """

        w = Watch()
        s = Scheduler()

        j1, j2, j3, j4, j5, j6, j7 = [job_in_s_w(s, w, i) for i in range(1, 8)]
        j7.requires(
            j6.requires(j4),
            j5.requires(j4),
        )
        j4.requires(
            j3.requires(j1),
            j2.requires(j1),
        )
        if n == 2:
            return w, s, j1, j2, j3, j4, j5, j6, j7
        j8, j9, j10 = [job_in_s_w(s, w, i) for i in range(8, 11)]
        j10.requires(
            j8.requires(j7),
            j9.requires(j7),
        )
        if n == 3:
            return w, s, j1, j2, j3, j4, j5, j6, j7, j8, j9, j10


    def test_bypass3(self):

        w, s, j1, j2, j3, j4, j5, j6, j7 = self.diamonds(2)

        self.assertEqual(s.successors_downstream(j1), {j2, j3, j4, j5, j6, j7})
        self.assertEqual(s.successors_downstream(j4), {j5, j6, j7})
        self.assertEqual(s.successors_downstream(j7), set())
        self.assertEqual(s.predecessors_upstream(j1), set())
        self.assertEqual(s.predecessors_upstream(j4), {j1, j2, j3})
        self.assertEqual(s.predecessors_upstream(j7), {j1, j2, j3, j4, j5, j6})
        produce_svg(s, "graphic-bypass3-step0")

        s.bypass_and_remove(j4)
        self.assertTrue(s.sanitize())
        self.assertFalse(j4 in s.jobs)
        self.assertTrue(j2 in j5.required)
        self.assertTrue(j3 in j5.required)
        self.assertTrue(j2 in j6.required)
        self.assertTrue(j3 in j6.required)
        self.assertEqual(s.successors_downstream(j1), {j2, j3, j5, j6, j7})
        self.assertEqual(s.successors_downstream(j3), {j5, j6, j7})
        self.assertEqual(s.successors_downstream(j6), {j7})
        self.assertEqual(s.successors_downstream(j7), set())
        self.assertEqual(s.predecessors_upstream(j1), set())
        self.assertEqual(s.predecessors_upstream(j3), {j1})
        self.assertEqual(s.predecessors_upstream(j6), {j1, j2, j3})
        self.assertEqual(s.predecessors_upstream(j7), {j1, j2, j3, j5, j6})
        produce_svg(s, "graphic-bypass3-step1")

        s.bypass_and_remove(j1)
        self.assertTrue(s.sanitize())
        self.assertTrue(len(j2.required) == 0)
        self.assertTrue(len(j3.required) == 0)
        self.assertEqual(s.successors_downstream(j3), {j5, j6, j7})
        self.assertEqual(s.predecessors_upstream(j7), {j2, j3, j5, j6})
        produce_svg(s, "graphic-bypass3-step2")

        s.bypass_and_remove(j7)
        self.assertTrue(s.sanitize())
        self.assertFalse(set(s.successors(j5)))
        self.assertFalse(set(s.successors(j6)))
        produce_svg(s, "graphic-bypass3-step3")

    def test_bypass_seq(self):

        w = Watch()
        s = Scheduler()

        jobs = [job_in_s_w(s, w, i) for i in range(1, 6)]
        Sequence(*jobs, scheduler=s)

        produce_svg(s, "graphic-bypass-seq-step0")

        j1, j2, j3, j4, j5 = jobs
        s.bypass_and_remove(j3)
        self.assertTrue(s.sanitize())
        self.assertFalse(j3 in s.jobs)
        self.assertTrue(j2 in j4.required)
        self.assertEqual(s.successors_downstream(j1), {j2, j4, j5})
        self.assertEqual(s.successors_downstream(j2), {j4, j5})
        self.assertEqual(s.successors_downstream(j4), {j5})
        self.assertEqual(s.successors_downstream(j5), set())
        self.assertEqual(s.predecessors_upstream(j1), set())
        self.assertEqual(s.predecessors_upstream(j2), {j1})
        self.assertEqual(s.predecessors_upstream(j4), {j1, j2})
        self.assertEqual(s.predecessors_upstream(j5), {j1, j2, j4})
        produce_svg(s, "graphic-bypass-seq-step1")


    def test_bypass_keep1(self):

        w, s, j1, j2, j3, j4, j5, j6, j7 = self.diamonds(2)
        produce_svg(s, "graphic-bypass-keep1-step0")
        s.keep_only_between(starts=[j2, j3], ends=[j5, j6])
        self.assertEqual(len(s), 5)
        self.assertEqual(s.jobs, {j2, j3, j4, j5, j6})
        produce_svg(s, "graphic-bypass-keep1-step1")

    def test_bypass_keep2(self):

        w, s, j1, j2, j3, j4, j5, j6, j7 = self.diamonds(2)
        produce_svg(s, "graphic-bypass-keep2-step0")
        s.keep_only_between(starts=[j4])
        self.assertEqual(len(s), 4)
        self.assertEqual(s.jobs, {j4, j5, j6, j7})
        produce_svg(s, "graphic-bypass-keep2-step1")

    def test_bypass_keep3(self):

        w, s, j1, j2, j3, j4, j5, j6, j7 = self.diamonds(2)
        produce_svg(s, "graphic-bypass-keep3-step0")
        s.keep_only_between(starts=[j4], keep_starts=False)
        self.assertEqual(s.jobs, {j5, j6, j7})
        produce_svg(s, "graphic-bypass-keep3-step1")

    def test_bypass_keep4(self):
        w, s, j1, j2, j3, j4, j5, j6, j7, j8, j9, j10 = self.diamonds(3)
        j_odd = job_in_s_w(s, w, 11)
        j7.requires(j_odd.requires(j2))
        produce_svg(s, "graphic-bypass-keep4-step0")

        s.keep_only_between(starts=[j2, j3], ends=[j5, j6])
        self.assertEqual(len(s), 5)
        self.assertEqual(s.jobs, {j2, j3, j4, j5, j6})
        produce_svg(s, "graphic-bypass-keep4-step1")

    def test_bypass_keep5(self):
        w, s, j1, j2, j3, j4, j5, j6, j7, j8, j9, j10 = self.diamonds(3)
        j_odd = job_in_s_w(s, w, 11)
        j7.requires(j_odd.requires(j2))
        produce_svg(s, "graphic-bypass-keep5-step0")

        s.keep_only_between(starts=[j2, j3], ends=[j8, j9], keep_ends=False)
        self.assertEqual(len(s), 7)
        self.assertEqual(s.jobs, {j2, j3, j4, j5, j6, j7, j_odd})
        produce_svg(s, "graphic-bypass-keep5-step1")

    def test_bypass_keep10(self):
        w, s, j1, j2, j3, j4, j5, j6, j7, j8, j9, j10 = self.diamonds(3)
        s.keep_only([j1, j2, j3, j4])
        self.assertEqual(len(s), 4)
        self.assertEqual(len(set(s.successors(j1))), 2)
        self.assertEqual(len(set(s.predecessors(j1))), 0)
        self.assertEqual(len(set(s.successors(j2))), 1)
        self.assertEqual(len(set(s.predecessors(j2))), 1)
        self.assertEqual(len(set(s.successors(j4))), 0)
        self.assertEqual(len(set(s.predecessors(j4))), 2)

    def test_bypass_keep11(self):
        w, s, j1, j2, j3, j4, j5, j6, j7, j8, j9, j10 = self.diamonds(3)
        s.keep_only([j1, j4, j7])
        self.assertEqual(len(s), 3)
        self.assertEqual(len(set(s.successors(j1))), 0)
        self.assertEqual(len(set(s.predecessors(j1))), 0)
        self.assertEqual(len(set(s.successors(j4))), 0)
        self.assertEqual(len(set(s.predecessors(j4))), 0)
        self.assertEqual(len(set(s.successors(j7))), 0)
        self.assertEqual(len(set(s.predecessors(j7))), 0)
