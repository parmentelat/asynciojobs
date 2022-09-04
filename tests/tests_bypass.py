# pylint: disable=c0111, c0103, r0201

from re import M
import unittest

from asynciojobs import *
from .util import *


class Tests(unittest.TestCase):

    def test_bypass1(self):

        watch = Watch()
        s = Scheduler()

        def job_in_s(i):
            return Job(co_print_sleep(watch, .2, f"job {i}"),
                       label=f"job{i}",
                       scheduler=s)

        j1, j2, j3, j4, j5 = [job_in_s(i) for i in range(1, 6)]
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

        watch = Watch()
        s = Scheduler()

        def job_in_s(i):
            return Job(co_print_sleep(watch, .2, f"job {i}"),
                       label=f"job{i}",
                       scheduler=s)

        j1, j2, j3, j4, j5 = [job_in_s(i) for i in range(1, 6)]
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

    def test_bypass3(self):

        watch = Watch()
        s = Scheduler()

        def job_in_s(i):
            return Job(co_print_sleep(watch, .2, f"job {i}"),
                       label=f"job{i}",
                       scheduler=s)

        j1, j2, j3, j4, j5, j6, j7 = [job_in_s(i) for i in range(1, 8)]
        j7.requires(
            j6.requires(j4),
            j5.requires(j4),
        )
        j4.requires(
            j3.requires(j1),
            j2.requires(j1),
        )
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

        watch = Watch()
        s = Scheduler()

        def job_in_s(i):
            return Job(co_print_sleep(watch, .2, f"job {i}"),
                       label=f"job{i}")

        jobs = [job_in_s(i) for i in range(1, 6)]
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
