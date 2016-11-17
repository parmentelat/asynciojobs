
<span style="float:left;">Licence CC BY-NC-ND</span><span style="float:right;">Thierry Parmentelat - Inria&nbsp;<img src="media/inria-25.png" style="display:inline"></span><br/>

# A simplistic orchestration engine

The main and single purpose of this library is to allow for the static description of a scenario involving `asyncio`-compliant jobs, that have dependencies in the sense that a given job cannot start until its requirements have not completed.

So in a nutshell you would:

* define a set of `Job` objects, 
* together with their `requires` relationship; that is to say, for each of them, which other jobs need to have completed before this one can be started,
* and run this logic through an `Engine` object, that will orchestrate the whole secenario 

Further features allow to

* define a job as running `forever`, in which case the engine of course won't wait for it, but instead will terminate it when all other jobs are done;
* define a job as `critical`; a critical job that raises an exception causes the orchestration to terminate abruptly;
* define a global `timeout` for the whole engine.


A job object can be created:

* either as a `Job` instance from a regular asyncio coroutine
* or by specializing the `AbstractJob` class and defining its `co_run()` method

As a convenience, the `Sequence` class is mostly a helper class that can free you from manually managing the `requires` deps in long strings of jobs.


```python
import asyncio
```

# Installing

```
pip3 install asynciojobs
```

# Examples

Let's consider a simple coroutine for the sake of illustration


```python
import time

async def mycoro(timeout):
    print("-> mycoro({})".format(timeout))
    await asyncio.sleep(timeout)
    print("<- mycoro({})".format(timeout))
    # return something easy to recognize: the number of milliseconds
    return 1000 * timeout
```

### example A

Running a series of coroutines in parallel - a la `gather` - can be done like this


```python
from asynciojobs import Job, Engine
```


```python
a1, a2, a3 = Job(mycoro(0.1)), Job(mycoro(0.2)), Job(mycoro(0.25)),
```

What we're saying here is that we have three jobs, that have no relationships between them. 

So when we run them, we would start all 3 coroutines at once, and return once they are all done:


```python
ea = Engine(a1, a2, a3)
ea.orchestrate()
```

    -> mycoro(0.1)
    -> mycoro(0.2)
    -> mycoro(0.25)
    <- mycoro(0.1)
    <- mycoro(0.2)
    <- mycoro(0.25)





    True




```python
z = mycoro(5)
```

### example B : add requirements (dependencies)

Now we can add *requirements* dependencies between jobs, like in the following example. We take this chance to show that jobs can be tagged with a label, which can turn out te be convenient somtimes.


```python
b1, b2, b3 = (Job(mycoro(0.1), label="b1"),
              Job(mycoro(0.2), label="b2"),
              Job(mycoro(0.25)))

b2.requires(b1)
```

Now `b3` needs `b1` to be finished before it can start. And so only the 2 first coroutines get started at the beginning, and only once b1 has finished does b3 start.


```python
# with this setup we are certain that b3 ends in the middle of b2
eb = Engine(b1, b2, b3)
eb.orchestrate()
```

    -> mycoro(0.1)
    -> mycoro(0.25)
    <- mycoro(0.1)
    -> mycoro(0.2)
    <- mycoro(0.25)
    <- mycoro(0.2)





    True



### exemple B' : exact same using a `Sequence`

The code above in example B is exactly identical to this


```python
from asynciojobs import Sequence

ebp = Engine(Sequence(Job(mycoro(0.1), label="bp1"),
                      Job(mycoro(0.2), label="bp2")),
             Job(mycoro(0.25)))

ebp.orchestrate()
```

    -> mycoro(0.25)
    -> mycoro(0.1)
    <- mycoro(0.1)
    -> mycoro(0.2)
    <- mycoro(0.25)
    <- mycoro(0.2)





    True



### inspect results

Before we see more examples, let's see how details for each `Job` can be retrieved once `orchestrate` finishes:


```python
# a shorter equivalent form would be 
# e2.list()
 
for job in eb.jobs:
    print(job)
```

      ☉ ☓   <Job `b1` -> 100.0>
      ☉ ☓   <Job `b2` -> 200.0>
      ☉ ☓   <Job `NOLABEL` -> 250.0>



```python
print(b1.is_done())
```

    True



```python
print(b3.result())
```

    250.0


### example C : infinite loops, or coroutines that don't return

Sometimes it is useful to deal with a endless loop; for example if we want to separate completely actions and printing, we can use an `asyncio.Queue` to implement a simple message bus as follows


```python
message_bus = asyncio.Queue()

async def monitor_loop(bus):
    while True:
        message = await bus.get()
        print("BUS: {}".format(message))
```

Now we need a modified version of the previous coroutine, that interacts with this message bus instead of printing anything itself&nbsp;:


```python
async def mycoro_bus(timeout, bus):
    await bus.put("-> mycoro({})".format(timeout))
    await asyncio.sleep(timeout)
    await bus.put("<- mycoro({})".format(timeout))
    # return something easy to recognize
    return 10 * timeout
```

We can replay the prevous scenario, adding the monitoring loop as a separate job; however we need to declare this job with `forever=True` so that we know when the bulk of the scenario is completed, since the monitoring loop will never return.


```python
c1, c2, c3, c4 = (Job(mycoro_bus(0.2, message_bus), label="c1"),
                  Job(mycoro_bus(0.4, message_bus), label="c2"), 
                  Job(mycoro_bus(0.3, message_bus), label="c3"),
                  Job(monitor_loop(message_bus), forever=True, label="monitor"))

c3.requires(c1)

ec = Engine(c1, c2, c3, c4)
ec.orchestrate()
```

    BUS: -> mycoro(0.2)
    BUS: -> mycoro(0.4)
    BUS: <- mycoro(0.2)
    BUS: -> mycoro(0.3)
    BUS: <- mycoro(0.4)
    BUS: <- mycoro(0.3)





    True



Note that `orchestrate` always terminates as soon as all the non-`forever` jobs are complete. The `forever` jobs, on the other hand, get cancelled, so of course no return value is available at the end of the scenario&nbsp;:


```python
ec.list()
```

    01   ☉ ☓   <Job `c1` -> 2.0>
    02   ☉ ↺ ∞ <Job `monitor`>
    03   ☉ ☓   <Job `c2` -> 4.0>
    04   ☉ ☓   <Job `c3` -> 3.0> - requires:{01}


### example D : specifying a global timeout

`orchestrate` accepts a `timeout` argument in seconds. When provided, `orchestrate` will ensure its global duration does not exceed this value, and will return `False` if the timeout triggers.

Of course this can be used with any number of jobs and dependencies, but for the sake of simplicity let us see this in action with just one job that loops forever


```python
async def forever():
    for i in range(100000):
        print("{}: forever {}".format(time.strftime("%H:%M:%S"), i))
        await asyncio.sleep(.1)
        
j = Job(forever(), forever=True)
e = Engine(j)
e.orchestrate(timeout=0.25)
```

    17:22:34: forever 0
    17:22:34: forever 1
    17:22:34: forever 2





    False



As you can see the result of `orchestrate` in this case is `False`, since not all jobs have completed. Apart from that the jobs is now in this state:


```python
j
```




      ☉ ↺ ∞ <Job `NOLABEL`>



### handling exceptions

A job instance can be **critical** or not; what this means is as follows

 * if a critical job raises an exception, the whole engine aborts immediately and returns False
 * if a non-critical job raises an exception, the whole engine proceeds regardless
 
In both cases the exception can be retrieved in the corresponding Job object with `raised_exception()`

For convenience, the **critical** property can be set either at the `Job` or at the `Engine` level. Of course the former takes precedence if set. The default for an engine object is `critical=False`. Let us see this below.

### Example E : non critical jobs


```python
async def boom(n):
    await asyncio.sleep(n)
    raise Exception("boom after {}s".format(n))
```


```python
# by default everything is non critical
e1 = Job(mycoro(0.2))
e2 = Job(boom(0.2), label="boom")
e3 = Job(mycoro(0.3))
e2.requires(e1)
e3.requires(e2)

e = Engine(e1, e2, e3)
print("orch:", e.orchestrate())
e.list()
```

    -> mycoro(0.2)
    <- mycoro(0.2)
    -> mycoro(0.3)
    <- mycoro(0.3)
    orch: True
    01   ☉ ☓   <Job `NOLABEL` -> 200.0>
    02   ★ ☓   <Job `boom` => exception:!!Exception:boom after 0.2s!!> - requires:{01}
    03   ☉ ☓   <Job `NOLABEL` -> 300.0> - requires:{02}


### Example F : critical jobs


```python
# to make the boom job critical we can either set that on the job or on the engine object
e1 = Job(mycoro(0.2))
e2 = Job(boom(0.2), label="boom", critical=True)
e3 = Job(mycoro(0.3))
e2.requires(e1)
e3.requires(e2)

e = Engine(e1, e2, e3)
print("orchestrate:", e.orchestrate())
e.list()
```

    -> mycoro(0.2)
    <- mycoro(0.2)
    orchestrate: False
    01   ☉ ☓   <Job `NOLABEL` -> 200.0>
    02 ⚠ ★ ☓   <Job `boom` => CRIT. EXC.:!!Exception:boom after 0.2s!!> - requires:{01}
    03     ⚐   <Job `NOLABEL`> - requires:{02}


# More

### `co_orchestrate` 

`orchestrate` is a regular `def` function (i.e. not an `async def`), but in fact just a wrapper around the native coroutine called `co_orchestrate`.

    def orchestrate(self, loop=None, *args, **kwds):
        if loop is None:
            loop = asyncio.get_event_loop()
        return loop.run_until_complete(self.co_orchestrate(loop=loop, *args, **kwds))

### `debrief()` and `list()`

`Engine.list()` shows a complete list of the jobs, in a format designed for quickly grasping where you are.

`Engine.debrief()` is designed for engines that have run and returned `False`, it does output the same listing as `list()` but with additional statistics on the number of jobs, and, most importantly, on the stacks of jobs that have raised an exception.


* here's the legend of symbols used

|          |   |
|----------|---|
| critical                       | `⚠` |
|raised an exception             | `★` |
| went through without exception | `☉` |
| complete | `☓` |
| running  | `↺` |
| idle     | `⚐` |
| forever  | `∞`|

* and here's an example of output for `list()` . 

```
01 ⚠ ★ ☓ ∞ <J `forever=True crit.=True status=done boom=True` => CRIT. EXC.:!!bool:True!!>
02 ⚠ ★ ↺ ∞ <J `forever=True crit.=True status=ongoing boom=True` => CRIT. EXC.:!!bool:True!!> - requires:{01}
03 ⚠ ★ ☓   <J `forever=False crit.=True status=done boom=True` => CRIT. EXC.:!!bool:True!!> - requires:{02}
04 ⚠ ★ ↺   <J `forever=False crit.=True status=ongoing boom=True` => CRIT. EXC.:!!bool:True!!> - requires:{03}
05 ⚠ ☉ ☓ ∞ <J `forever=True crit.=True status=done boom=False` -> 0> - requires:{04}
06 ⚠ ☉ ↺ ∞ <J `forever=True crit.=True status=ongoing boom=False`> - requires:{05}
07 ⚠   ⚐ ∞ <J `forever=True crit.=True status=idle boom=False`> - requires:{06}
08 ⚠ ☉ ☓   <J `forever=False crit.=True status=done boom=False` -> 0> - requires:{07}
09 ⚠ ☉ ↺   <J `forever=False crit.=True status=ongoing boom=False`> - requires:{08}
10 ⚠   ⚐   <J `forever=False crit.=True status=idle boom=False`> - requires:{09}
11   ★ ☓ ∞ <J `forever=True crit.=False status=done boom=True` => exception:!!bool:True!!> - requires:{10}
12   ★ ↺ ∞ <J `forever=True crit.=False status=ongoing boom=True` => exception:!!bool:True!!> - requires:{11}
13   ★ ☓   <J `forever=False crit.=False status=done boom=True` => exception:!!bool:True!!> - requires:{12}
14   ★ ↺   <J `forever=False crit.=False status=ongoing boom=True` => exception:!!bool:True!!> - requires:{13}
15   ☉ ☓ ∞ <J `forever=True crit.=False status=done boom=False` -> 0> - requires:{14}
16   ☉ ↺ ∞ <J `forever=True crit.=False status=ongoing boom=False`> - requires:{15}
17     ⚐ ∞ <J `forever=True crit.=False status=idle boom=False`> - requires:{16}
18   ☉ ☓   <J `forever=False crit.=False status=done boom=False` -> 0> - requires:{17}
19   ☉ ↺   <J `forever=False crit.=False status=ongoing boom=False`> - requires:{18}
20     ⚐   <J `forever=False crit.=False status=idle boom=False`> - requires:{19}
```

Note that if your locale/terminal cannot output these, the code will tentatively resort to pure ASCII output.

### `rain_check`

`rain_check` will check for cycles in the requirements graph. It returns a boolean. It's a good idea to call it before running an orchestration.

### `sanitize`

In some cases like esp. test scenarios, it can be helpful to add requirements to jobs that are not in the engine. The `sanitize` method removes such extra requirements, and unless you are certain it is not your case, it might be a good idea to call it explcitly before an orchestration.

### `co_shutdown`

Before returning, `orchestrate` sends the `co_shutdown()` method on all jobs. The default behaviour - in the `Job` class - is to do nothing, but this can be redefined when relevant. Typically, an implementation of an `SshJob` will allow for a given SSH connection to be shared amongs several `SshJob` instances, and so `co_shutdown()` may be used to  close the underlying SSH connections at the end of the scenario.

### `save_as_dotfile`

An engine can be exported as a dotfile for feeding `graphviz` and producing visual diagrams. Provided that you have the `dot` program (which is part of `graphviz`) installed, you could do something like

    e.save_as_dotfile('foo.dot')
    os.system("dot -Tpng foo.dot -o foo.png")


### the `Sequence` class

You can group jobs in sequences so you don't need to worry about requirements. This might still be a little brittle for now. You can nest sequences in sequences.


```python
from asynciojobs import Sequence

e = Engine (Sequence(Job(mycoro(1), label="j1"), 
                     Job(mycoro(2), label="lab2"), 
                     Job(mycoro(3), label="tag3")))
e.list()
```

    01     ⚐   <Job `j1`>
    02     ⚐   <Job `lab2`> - requires:{01}
    03     ⚐   <Job `tag3`> - requires:{02}


### customizing the `Job` class

`Job` actually is a specializtion of `AbstractJob`, and the specification is that the `co_run()` method should denote a coroutine itself, and that is what is triggered by `Engine` for running said job.

You can define your own `Job` class by specializing `job.AbstractJob` - more on this later, we'll define some predefined jobs, in particular for interacting through ssh, and possibly many others.

# TODO

## termination and re-run

1. related: for the tests at least, and maybe also in practical life, if we create an engine that does not pass  `rain_check`, and so don't run orchestrate, then we'd need a means to garbage collect the pending coroutines

1. also related: there is an intention in the code that one engine object can be run several times. Looks like this won't work as expected anymore, and it can be an issue in the context of reproducible research: we may/will want to run the same scenario object several times, don't we ? 

 * This maybe is not too serious; we may get away with that by just doing
 
instead of

```
e = Engine(Job(coro(1)), Job(coro(2))
e.orchestrate()
# won't work again because the coroutines have dried out
e.orchestrate()
```

do this

```
def run():
   e = Engine(Job(coro(1)), Job(coro(2))
   e.orchestrate()

# this of course works
run()
run()

```
 

## monitoring 
* come up with some basic (curses ?) monitor to show what's going on; what I have in mind is something like rhubarbe load where all jobs would be displayed, one line each, and their status could be shown so that one can get a sense of what is going on
* one way to look at this is to have the main Engine class send itself a `tick()` method, and then specialize `Engine` as `EngineCurses` that would actually do things on such events.
* ***or*** this gets delegated on a `message_queue` object. **Review the rhubarbe code on this aspect**.

## convenience
* ~~do we want to support requires by labels ?~~ : NO

* **BUT** it would make sense to allow `requires` to be passed at job creation time ?

```
a1 = J(mycoro(1), label="a1")
a2 = J(mycoro(2), requires = [a1], label="a2")
a3 = J(mycoro(3), requires = [a1, a2])
```


# Historical notes

The purpose is to come up with an as-simple-as-it-gets replacement for our toolset for orchestrating network experiments. In its simplest form, it can be described as an ***orchestration tool for `asyncio`-based libraries***, with the following objectives

* we ***primarily*** target ***ssh-based*** kind of interactions with nodes; typically we need to control any number of nodes reachable through ssh, ranging from hundreds of them in the context of PlanetLab, down to tens or a handful in the context of R2lab
* previous tools like in particular [NEPI](http://nepi.inria.fr) came with a very ambitious goal of being extremely generic, to the cost of achieving poor to very poor performance, in particular in the specific niche of ssh-addressable nodes; in contrast, here we want to achieve optimal performance, to the possible cost of generality.

So in order to take these objectives into account:

* we want to have full control on ssh connections, and specifically to open only one such connection per node for the whole duration of the exp.
* `asyncio` allows us to be totally single-threaded, so no multi-threading is needed, and thus no critical section nonsense
* similarly we want to be able to rely on the internal ssh protocol to be notified when a remote command is done, ***instead of having to cyclically*** check for its status, which comes at an incredibly high cost

It appears that the only critical feature required here as compared to what `asyncio` offers out of the box, is to handle dependencies between atomic jobs. It the main and only purpose of this micro-tool, to allow an experimenter to describe its experiment as a logically ordered set of jobs. 

As I hope it will turn out, all this applies in a straightforward way to both

* simple ssh-derivatives; at this point, it looks like we essentially need 2 first-class citizens here:
  * running commands native to the remote system, or 
  * pushing a local script remotely and run it

* but in fact the same applies as-is to any kind of coroutine, that could either
  * have a local purpose, like dealing with a local software bus for exchanging messages between jobs
  * or at the other extreme of the spectrum, interact with network resource using technologies totally different from `ssh`, provided that they rely on `asyncio`-aware libraries. Virtually everything is available as `asyncio`-compliant these days, from `http` to `telnet` - already used e.g. in `rhubarbe` - to, I am sure, `xmlrpc` or other more modern variants based on JSON, as well as XMPP-based stuff, if need be. 
