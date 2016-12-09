#!/usr/bin/env python3
import os.path

from asynciojobs.scheduler import Scheduler
from asynciojobs.job import Job

from apssh.jobs.sshjobs import SshNode, SshJob, SshJobScript
from apssh.formatters import ColonFormatter
from apssh.keys import load_agent_keys

async def aprint(*args, **kwds):
    print(*args, **kwds)

# first script does not take args as it it passed directly as a command
path = "tests"
with open(os.path.join(path, "randwait-noarg.sh")) as f:
    bash_oneliner = f.read()

# this one accepts one message argument
bash_script = os.path.join(path, "randwait-arg.sh")


####################
def two_passes(gateway, node_ids, synchro, debug=False,
               before=True, after=True):

    """
    synchro = True : wait for pass1 to complete
                     on all nodes before triggering pass2
    synchro = False: run pass2 on node X as soon as pass1 is done on node X
    """

    gateway_node = SshNode(hostname=gateway, username="root",
                           client_keys=load_agent_keys())

    msg = "synchro={}".format(synchro)

    nodenames = ["fit{:02d}".format(id) for id in node_ids]
    nodes = [SshNode(gateway=gateway_node,
                     hostname=nodename, username="root",
                     formatter=ColonFormatter(),
                     debug=debug)
             for nodename in nodenames]

    print(40*'*', msg)
    jobs1 = [SshJob(node=node,
                    command=["/bin/bash -c '{}'".format(bash_oneliner)],
                    label="{} - pass1 on {}".format(msg, node.hostname))
             for node in nodes]

    middle = Job(aprint(20*'=' + 'middle'), label='middle')

    jobs2 = [SshJobScript(node=node,
                          command=[bash_script, 'pass2'],
                          label="{} - pass2 on {}".format(msg, node.hostname))
             for node in nodes]

    for j1 in jobs1:
        middle.requires(j1)

    if not synchro:
        for j1, j2 in zip(jobs1, jobs2):
            j2.requires(j1)
    else:
        for j2 in jobs2:
            j2.requires(middle)

    s = Scheduler(debug=debug)
    if before:
        s.update(jobs1)
    s.add(middle)
    if after:
        s.update(jobs2)
    print("========== sanitize")
    s.sanitize()
    print("========== rain check")
    s.rain_check()
    print("========== orchestrating")
    orch = s.orchestrate()
    print('********** orchestrate ->', orch)
    s.list()
    print('**********')

if __name__ == '__main__':

    from argparse import ArgumentParser
    parser = ArgumentParser()
    parser.add_argument("-g", "--gateway", default="faraday.inria.fr")
    parser.add_argument("-d", "--debug", action='store_true')
    parser.add_argument("--after", action='store_true')
    parser.add_argument("--before", action='store_true')
    # -1 : first test
    # -2 : second test
    # -3 : both
    parser.add_argument("-s", "--scenarii", type=int, default=3)
    parser.add_argument("node_ids", nargs="+", type=int,
                        default=[1, 2, 3])

    args = parser.parse_args()
    debug = args.debug
    scenarii = args.scenarii
    node_ids = args.node_ids
    gateway = args.gateway

    # --after means only after
    if args.before:
        before, after = True, False
    elif args.after:
        before, after = False, True
    else:
        before, after = True, True
    if scenarii & 1:
        two_passes(gateway, node_ids, True, debug, before, after)
    if scenarii & 2:
        two_passes(gateway, node_ids, False, debug, before, after)
