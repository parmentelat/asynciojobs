# pylint: disable=c0111, c0103, r0201

import unittest

from asynciojobs import PureScheduler, Scheduler, Job, Sequence, Watch

from .util import co_print_sleep


class Tests(unittest.TestCase):

    def test_flat_cycles(self):

        watch = Watch()

        def job_in_s(i, s):
            return Job(co_print_sleep(watch, .2, f"job {i}"),
                       label=f"job{i}",
                       scheduler=s)

        def check_class(klass):
            sched = klass()
            j1, j2, j3 = [job_in_s(i, sched) for i in range(1, 4)]
            j3.requires(j2)
            j2.requires(j1)

            # no cycle yet
            self.assertTrue(sched.check_cycles())

            # create cycle
            j1.requires(j3)
            self.assertFalse(sched.check_cycles())
            sched.close_idle_jobs()

        check_class(PureScheduler)
        check_class(Scheduler)

    def test_nested_cycles(self):

        watch = Watch()

        def job(i):
            return Job(co_print_sleep(watch, .2, f"job {i}"),
                       label=f"job{i}")
        js1, js2, js3 = [job(i) for i in range(11, 14)]
        s2 = Scheduler(Sequence(js1, js2, js3))

        j1, j3 = job(1), job(3)
        s1 = Scheduler(Sequence(j1, s2, j3))
        self.assertTrue(s1.check_cycles())

        # create cycle in subgraph
        js1.requires(js3)
        self.assertFalse(s1.check_cycles())

        # restore in OK state
        js1.requires(js3, remove=True)
        self.assertTrue(s1.check_cycles())

        # add cycle in toplevel
        j1.requires(j3)
        self.assertFalse(s1.check_cycles())

        # restore in OK state
        j1.requires(j3, remove=True)
        self.assertTrue(s1.check_cycles())

        # add one level down
        s3 = Scheduler()
        jss1, jss2, jss3 = [job(i) for i in range(111, 114)]
        Sequence(jss1, jss2, jss3, scheduler=s3)

        # surgery in s2; no cycles
        s2.remove(js2)
        s2.sanitize()
        s2.add(s3)
        s3.requires(js1)
        js3.requires(s3)
        self.assertTrue(s1.check_cycles())

        # add cycle in s3
        js1.requires(js3)
        self.assertFalse(s1.check_cycles())

        for s in (s1, s2, s3):
            s.close_idle_jobs()
        # this one has been removed manually
        js2.close()
