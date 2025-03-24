# pylint: disable=c0111, c0103

import unittest

from asynciojobs import PureScheduler, Job, Sequence, Watch

from .util import co_print_sleep, produce_svg


class Tests(unittest.TestCase):

    def test_graph1(self):

        watch = Watch()

        s = PureScheduler()
        s.add(Sequence(
            Job(co_print_sleep(watch, .25, 'begin')),
            Job(co_print_sleep(watch, 1., 'middle'), label='middle'),
            Job(co_print_sleep(watch, .25, 'end')),
        ))
        print("test_graph1 NO DETAILS")
        s.list()
        print("test_graph1 WITH DETAILS")
        s.list(details=True)
        print("GRAPH")
        self.assertEqual(len(s), 3)
        s.run()
        self.assertAlmostEqual(watch.seconds(), 1.5, delta=0.05)
        produce_svg(s, "graphic-graph1")

    def test_graph2(self):

        class TextJob(Job):
            def __init__(self, text, *args, **kwds):
                self.text = text
                super().__init__(*args, **kwds)

            def text_label(self):
                return "[[TextJob {}]]".format(self.text[::-1])

            def details(self):
                return f"TextJob details say\n" \
                    f"that initial text was {self.text}"

        class GraphJob(Job):
            def __init__(self, graph, *args, **kwds):
                self.graph = graph
                super().__init__(*args, **kwds)

            def graph_label(self):
                return "[[GraphJob\n{}]]".format(self.graph[::-1])

            def details(self):
                return f"GraphJob details\nare even more verbose and say\n" \
                       f"that initial graph message\nwas {self.graph}"

        watch = Watch()
        sched = PureScheduler()
        sched.add(Sequence(
            TextJob('textjob-with',
                    co_print_sleep(watch, 0.1, 'textjob, no label ')),
            TextJob('textjob-without',
                    co_print_sleep(watch, 0.1, 'textjob, with label '),
                    label='TextLabel'),
            GraphJob('graphjob-with',
                     co_print_sleep(watch, 0.1, 'graphjob, no label ')),
            GraphJob('graphjob-without',
                     co_print_sleep(watch, 0.1, 'graphjob, with label '),
                     label='GraphLabel'),
        ))
        print("test_graph2 NO DETAILS")
        sched.list()
        print("test_graph2 WITH DETAILS")
        sched.list(details=True)
        print("GRAPH")
        self.assertEqual(len(sched), 4)
        produce_svg(sched, "graphic-graph2")

        sched.close_idle_jobs()
