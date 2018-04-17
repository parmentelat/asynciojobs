# pylint: disable=c0111, c0103

import unittest

from asynciojobs import Scheduler, Job, Sequence

from .util import co_print_sleep


class TestGraph(unittest.TestCase):

    def test_graph1(self):

        s = Scheduler()
        s.add(Sequence(
            Job(co_print_sleep('begin')),
            Job(co_print_sleep('middle', 1), label='middle'),
            Job(co_print_sleep('end', .25)),
        ))
        print("test_graph1 NO DETAILS")
        s.list()
        print("test_graph1 WITH DETAILS")
        s.list(details=True)
        print("GRAPH")
        self.assertEqual(len(s), 3)
        g = s.graph()
        g.format = 'png'
        g.render('tests/test_graph1')
        print("(over)wrote tests/test_graph1.png")
        g_ids = s.graph(show_ids=True)
        g_ids.format = 'png'
        g_ids.render('tests/test_graph1_ids')
        print("(over)wrote tests/test_graph1_ids.png")

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

        s = Scheduler()
        s.add(Sequence(
            TextJob('textjob-with',
                    co_print_sleep('textjob, no label ')),
            TextJob('textjob-without',
                    co_print_sleep('textjob, with label '),
                    label='TextLabel'),
            GraphJob('graphjob-with',
                     co_print_sleep('graphjob, no label ')),
            GraphJob('graphjob-without',
                     co_print_sleep('graphjob, with label '),
                     label='GraphLabel'),
        ))
        print("test_graph2 NO DETAILS")
        s.list()
        print("test_graph2 WITH DETAILS")
        s.list(details=True)
        print("GRAPH")
        self.assertEqual(len(s), 4)
        g = s.graph()
        g.format = 'png'
        g.render('tests/test_graph2')
        print("(over)wrote tests/test_graph2.png")
