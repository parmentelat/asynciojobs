#!/usr/bin/env python3

"""
A simple tool to define ad-hoc 'jobs' 
"""

import time
import math
import asyncio

def ts():
    """ 
    a time stamp with millisecond 
    """
    # apparently this is not supported by strftime ?!?
    cl = time.time()
    ms = int(1000 * (cl-math.floor(cl)))
    return time.strftime("%M-%S-") + "{:03d}".format(ms)

##############################
async def _sl(n, middle, emergency):
    """
_sl(timeout, middle=False) returns a future that specifies an job like this:
* print incoming `->`
* wait for the time out
* print outgoing `<-` 
* return the timeout

_sl(timeout, middle=True) returns a future that specifies an job like this:
* print incoming `->`
* wait for half the time out
* print inside `==` - and optionnally raise an exception there if `emergency` is set
* wait for the second half of the time out
* print outgoing `<-` 
* return the timeout

"""
    print("{} -> sl({})".format(ts(), n))
    if middle:
        await asyncio.sleep(n/2)
        print("{} == sl({})".format(ts(), n))
        if emergency:
            raise Exception("emergency exit")
        await asyncio.sleep(n/2)
    else:
        await asyncio.sleep(n)
    print("{} <- sl({})".format(ts(), n))
    return n

def sl(n): return _sl(n, middle=False, emergency=False)
def slm(n): return _sl(n, middle=True, emergency=False)

##############################
from asynciojobs.job import AbstractJob

class SleepJob(AbstractJob):
    def __init__(self, timeout, middle=False):
        AbstractJob.__init__(self, forever=False, label="sleep for {}s".format(timeout))
        self.timeout = timeout
        self.middle = middle

    async def co_run(self):
        result = await _sl(self.timeout, middle=self.middle, emergency=False)
        return result

    async def co_shutdown(self):
        pass
        

class TickJob(AbstractJob):
    def __init__(self, cycle):
        AbstractJob.__init__(self, forever=True, label="Cyclic tick every {}s".format(cycle))
        self.cycle = cycle

    async def co_run(self):
        counter = 1
        while True:
            print("{} -- Tick {} from {}".format(ts(), counter, self.label))
            counter += 1
            await asyncio.sleep(self.cycle)

    async def co_shutdown(self):
        pass


async def co_exception(n):
    await asyncio.sleep(n)
    raise ValueError(10**6*n)
    
####################            
from asynciojobs import Job as J
from asynciojobs import Sequence as Seq
from asynciojobs import Engine

# shortcuts
SLJ = SleepJob
TJ  = TickJob

sep = 40 * '*' + ' '

import unittest

def check_required_types(engine, message):
    wrong = [j for j in engine.jobs if not isinstance(j, AbstractJob) or not hasattr(j, 'required')]
    if len(wrong) != 0:
        print("Engine {} has {}/{} ill-typed jobs"
              .format(len(len(wrong), engine.jobs)))
        return False
    return True

class Tests(unittest.TestCase):

    ####################
    def test_cycle(self):
        """a simple loop with 3 jobs - cannot handle that"""
        a1, a2, a3 = J(sl(1.1)), J(sl(1.2)), J(sl(1.3))
        a1.requires(a2)
        a2.requires(a3)
        a3.requires(a1)

        e = Engine(a1, a2, a3)

        # these lines seem to trigger a nasty message about a coro not being waited
        self.assertFalse(e.rain_check())

    ####################
    # Job(asyncio.sleep(0.4))
    # or
    # SleepJob(0.4)
    # are almost equivalent forms to do the same thing
    def test_simple(self):
        """a simple topology, that should work"""
        jobs = SLJ(0.1), SLJ(0.2), SLJ(0.3), SLJ(0.4), SLJ(0.5), J(sl(0.6)), J(sl(0.7))
        a1, a2, a3, a4, a5, a6, a7 = jobs
        a4.requires(a1, a2, a3)
        a5.requires(a4)
        a6.requires(a4)
        a7.requires(a5)
        a7.requires(a6)
        
        e = Engine(*jobs)
        e.list(sep + "LIST BEFORE")
        self.assertTrue(e.rain_check())
        self.assertTrue(e.orchestrate(loop=asyncio.get_event_loop()))
        for j in jobs:
            self.assertFalse(j.raised_exception())
        e.list(sep + "LIST AFTER")
        print(sep + "DEBRIEF")
        e.debrief()
        
    ####################
    def test_forever(self):
        a1, a2, t1 = SLJ(1), SLJ(1.5), TJ(.6)
        a2.requires(a1)
        e = Engine(a1, a2, t1)
        e.list()
        self.assertTrue(e.orchestrate())
        e.list()

    ####################
    def test_timeout(self):
        a1, a2, a3 = [SLJ(x) for x in (0.5, 0.6, 0.7)]
        a2.requires(a1)
        a3.requires(a2)
        e = Engine(a1, a2, a3)
        # should timeout in the middle of stage 2
        self.assertFalse(e.orchestrate(timeout=1))
        e.list()

    ####################
    def test_exc_non_critical(self):

        a1, a2 = SLJ(1), J(co_exception(0.5), label='non critical boom')
        e = Engine(a1, a2)
        self.assertTrue(e.orchestrate())
        e.list()

    ####################
    def test_exc_critical(self):

        a1, a2 = SLJ(1), J(co_exception(0.5), label='critical boom', critical=True)
        e = Engine(a1, a2)
        self.assertFalse(e.orchestrate())
        e.list(sep + 'critical')
        print(sep + 'debrief(verbose=False)')
        e.debrief(verbose=False)
        print(sep + 'debrief(verbose=True)')
        e.debrief(verbose=True)

    ####################
    def test_sequence1(self):
        "a simple sequence"
        a1 = J(sl(0.1), label=1)
        a2 = J(sl(0.1), label=2)
        a3 = J(sl(0.1), label=3)
        s = Seq(a1, a2, a3)
        e = Engine(s)
        e.list(sep + "sequence1")
        self.assertEqual(len(a1.required), 0)
        self.assertEqual(len(a2.required), 1)
        self.assertEqual(len(a3.required), 1)
        self.assertTrue(check_required_types(e, "test_sequence1"))
        self.assertTrue(e.orchestrate())

    ####################
    def test_sequence2(self):
        "a job and a sequence"
        a1 = J(sl(0.1), label=1)
        a2 = J(sl(0.1), label=2)
        a3 = J(sl(0.1), label=3)
        s = Seq(a2, a3, required=a1)
        e = Engine(a1, s)
        e.list(sep + "sequence2")
        self.assertEqual(len(a1.required), 0)
        self.assertEqual(len(a2.required), 1)
        self.assertEqual(len(a3.required), 1)
        self.assertTrue(check_required_types(e, "test_sequence2"))
        self.assertTrue(e.orchestrate())

    ####################
    def test_sequence3(self):
        "a sequence and a job"
        a1 = J(sl(0.1), label=1)
        a2 = J(sl(0.1), label=2)
        s = Seq(a1, a2)
        a3 = J(sl(0.1), label=3, required=s)
        #e = Engine(s, a3)
        e = Engine()
        e.update((s, a3))
        e.list(sep + "sequence3")
        self.assertEqual(len(a1.required), 0)
        self.assertEqual(len(a2.required), 1)
        self.assertEqual(len(a3.required), 1)
        self.assertTrue(check_required_types(e, "test_sequence3"))
        self.assertTrue(e.orchestrate())

    ####################
    def test_sequence4(self):
        "a sequence of 2 sequences"
        a1 = J(sl(0.1), label=1)
        a2 = J(sl(0.1), label=2)
        a3 = J(sl(0.1), label=3)
        a4 = J(sl(0.1), label=4)
        s1 = Seq(a1, a2)
        s2 = Seq(a3, a4)
        e = Engine(Seq(s1, s2))
        e.list(sep + "sequence4")
        self.assertEqual(len(a1.required), 0)
        self.assertEqual(len(a2.required), 1)
        self.assertEqual(len(a3.required), 1)
        self.assertEqual(len(a4.required), 1)
        self.assertTrue(check_required_types(e, "test_sequence4"))
        self.assertTrue(e.orchestrate())
    
        
    ####################
    def test_sequence5(self):
        "sequences with required"
        a1 = J(sl(0.1), label=1)
        a2 = J(sl(0.1), label=2)
        a3 = J(sl(0.1), label=3)
        a4 = J(sl(0.1), label=4)
        a5 = J(sl(0.1), label=5)
        a6 = J(sl(0.1), label=6)
        s1 = Seq(a1, a2)
        s2 = Seq(a3, a4, required = s1)
        s3 = Seq(a5, a6, required = s2)
        e = Engine(s1, s2, s3)
        e.list(sep + "sequence5")
        self.assertEqual(len(a1.required), 0)
        self.assertEqual(len(a2.required), 1)
        self.assertEqual(len(a3.required), 1)
        self.assertEqual(len(a4.required), 1)
        self.assertEqual(len(a5.required), 1)
        self.assertEqual(len(a6.required), 1)
        self.assertTrue(check_required_types(e, "test_sequence5"))
        self.assertTrue(e.orchestrate())


    ##########
    def test_requires_job(self):

        a1 = J(sl(0.1), label="a1")
        a2 = J(sl(0.1), label="a2")
        a3 = J(sl(0.1), label="a3")
        a4 = J(sl(0.1), label="a4")
        a5 = J(sl(0.1), label="a5")

        # several forms to create
        b = J(sl(0.2), required = None)
        self.assertEqual(len(b.required), 0)
        b = J(sl(0.2), required = (None,))
        self.assertEqual(len(b.required), 0)
        b = J(sl(0.2), required = [None])
        self.assertEqual(len(b.required), 0)
        b = J(sl(0.2), required = a1)
        self.assertEqual(len(b.required), 1)
        b = J(sl(0.2), required = (a1,))
        self.assertEqual(len(b.required), 1)
        b = J(sl(0.2), required = [a1])
        self.assertEqual(len(b.required), 1)
        b = J(sl(0.2), label='BROKEN', required = (a1, a2))
        self.assertEqual(len(b.required), 2)
        b = J(sl(0.2), required = [a1, a2])
        self.assertEqual(len(b.required), 2)
        b = J(sl(0.2), required = [a1, (a2,), set([a3, a4]), [[[[[[a5]]]]]]])
        self.assertEqual(len(b.required), 5)

    ##########
    def test_requires_sequence(self):

        # we leave these untouched (no req. added)
        a1 = J(sl(0.1), label="a1")
        a2 = J(sl(0.1), label="a2")
        a3 = J(sl(0.1), label="a3")
        a4 = J(sl(0.1), label="a4")
        a5 = J(sl(0.1), label="a5")
        
        # re-create these each time to have fresh data
        def bs():
            b1 = J(sl(0.1), label="b1")
            b2 = J(sl(0.1), label="b2")
            b3 = J(sl(0.1), label="b3")
            return b1, b2, b3

        b1, b2, b3, *_ = bs()
        s1 = Seq(b1, b2, b3, required = [a1, a2])
        self.assertEqual(len(b1.required), 2)
        self.assertEqual(len(b2.required), 1)
        
        b1, b2, b3, *_ = bs()
        s1 = Seq(b1, b2, b3)
        s1.requires([a1, a2])
        self.assertEqual(len(b1.required), 2)
        self.assertEqual(len(b2.required), 1)
        

    ##########
    def test_timeout(self):
        a1 = J(sl(1), label="a1")
        a2 = J(sl(2), label="a2")
        a3 = J(sl(10), label="a3")
        result = Engine(a1, a2, a3).orchestrate(timeout=3)
        self.assertEqual(result, False)
        self.assertEqual(a1.is_done(), True)
        self.assertEqual(a1.result(), 1)
        self.assertEqual(a2.is_done(), True)
        self.assertEqual(a2.result(), 2)
        self.assertEqual(a3.is_done(), False)
        
        
    ##########
    def test_forever(self):
        async def tick(n):
            while True:
                print('tick {}'.format(n))
                await asyncio.sleep(n)

        a1 = J(sl(0.5), label="finite")
        a2 = J(tick(0.1), forever = True, label = "forever")
        e = Engine(a1, a2)
        result = e.orchestrate()
        self.assertEqual(result, True)
        self.assertEqual(a1.is_done(), True)
        self.assertEqual(a2.is_done(), False)

if __name__ == '__main__':
    import sys
    if '-v' in sys.argv:
        import engine
        engine.debug = True
        sys.argv.remove('-v')
    unittest.main()

