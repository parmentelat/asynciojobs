# ChangeLog

## 0.20.0 - 2025 Mar 23

- the debrief() method accepts a new optional argument `silence_done_jobs`
  to avoid listing jobs that are done; for backward compatibility
  the default is to show all jobs in the scheduler
- schedule objects have 2 methods, mostly used in tests primarily
  but can come in handy to avoid annoying messages from the asyncio runtime
  that tracks non-awaited coroutines
  - `close_all_jobs()`
  - `close_done_jobs()`

## 0.19.1 - 2024 Dec 16

- the description used in pypi is just the toplevel README, which points at rtd
- this because the images were not getting properly inserted on pypi

## 0.19.0 - 2024 Dec 16

- the synchroneous `run()` methods no longer call `get_event_loop()`
  and use a `asyncio.Runner` instance instead
- the doc no longer calls these `run()` methods, but use `await
  scheduler.co_run()` instead, since this is the simplest way in the context of
  a notebook - where there already is an event loop running
- use pyproject.toml for build instead of setup.py
- consequently remove Makefile.pypi
- refer to `python` and `pip` instead of `python3` and `pip3` in the docs
- remove `sphinx/requirements-rtd.txt`, these requirements are now in
  `pyproject.toml` as well as the `readthedocs` extra dependency

## 0.18.1 - 2022 Oct 4

* new method Scheduler.keep_only
  useful in simpler cases where the caller knows which jobs to keep


## 0.18.0 - 2022 Oct 4

* rewrote successors* and predecessors* to be usable with a collection
  of jobs, and to always return a set
* rewrote keep_only_between; previous implementation was flawed when there
  were nodes not comparable with the threshholds

## 0.17.0 -- 2022 Sep 6

* no change since 0.16.4 except for a minor tweak in the sphinx config
* however since we now rely on python-3.9 this deserves a clearer
  bump in the version number

## 0.16.4 -- 2022 Sep 6

* previous version was not working with Python3.9
  due to using a | to refer to a union type
* this version now does use types hints like `set[AbstractJob]`
  so this means 3.9 is required
* renamed tests/tests_stuff.py into tests/test_stuff.py
  and move to using pytest as a test driver
* dusted off doc building

## 0.16.3 -- 2022 Sep 4

* new methods in `PureScheduler`:
  * `successors(job)` to iterate over a job's successors
    * as well as `predecessors(job)`
  * `predecessors_upstream()` and `successors_downstream()` to compute
    the closure of the requirement relationship in both directions
  * `bypass_and_remove(job)`
    allows to prune jobs from a scheduler while preserving the logic
  * `keep_only_between()` to cut parts of a scheduler
  * also, `PureScheduler` becomes iterable, and iterates over its jobs
  * `export_as_graphic(filename, format)` and `export_as_svg(filename)`
     complement `export_as_png`

* `job.requires(job)` does nothing
  this is to ease the a posteriori addition of a global first step
  like typically check_lease

## 0.15.2 -- 2022 Mar 20

* in anticipation for 3.11, `scheduler.run()` now creates an event loop when needed,
  i.e. when `get_running_loop()` triggers the `RuntimeError` exception

## 0.15.1 - 2022 Mar 18

* fix release 0.15.0 that is broken, DO NOT USE
* was using `asyncio.run()` to implement the synchronous
  wrappers `run()` and `shutdown()` on a `Scheduler` object
  but `asyncio.run()` is way to intrusive for that

## 0.15.0 - 2022 Mar 8

* for python-3.10: remove the `loop` parameter when creating a `Queue`

## 0.14.3 - 2020 May 13

* again based on sharable Makefile.pypi

## 0.14.2 - 2020 May 13

* no change in code
* reviewed recipe for uploading to PyPI
* long_description now based on proper README in markdown

## 0.14.1 - 2018 Nov 20

* for Python-3.5 and below: remove use of ModuleNotFoundError, use ImportError instead

## 0.14.0 - 2018 Nov 20

* `PureScheduler.add()` returns the job, and no longer the scheduler.
  Use `update()` when cascading is needed.

## 0.13.2 - 2018 Oct 10

* minor tweaks in the way things are displayed

## 0.13.1 - 2018 Sep 20

* bugfix: in dot output, the source and destination of arrows need to be atomic jobs, not subgraphs; we had that wrong in case where nesting depth was more than 2.

## 0.13.0 - 2018 Aug 30

* re-enabled auto-shutdown() message broadcast system; this method is sent to all jobs within a scheduler when co_run() finishes;
* a job in a nested scheduler receives this event when its most enclosing scheduler finishes, not when the highest-level scheduler finishes;
* the feature is deemed complete and well tested including wrt shutdown_timeout.

## 0.12.11 - 2018 Aug 23

* new method `iterate_jobs()` on schedulers to scan all jobs in   scheduler and nested sons.

## 0.12.10 - 2018 Jul 5

* iron unicode support detection, primarily for testing apssh within a ubuntu virtualbox

## 0.12.9 - 2018 Jul 5

* make OrderedSet optional again; too cumbersome on some distros like fedora
* OrderedSet will be used if present, otherwise use plain sets
* can install with either `pip3 install asynciojobs[ordered]`
* or equivalently with `pip3 install orderedset`
* release 0.12.8 is broken

## 0.12.7 - 2018 Jul 4

* fix packaging, so that `orderedset` can properly be installed as a dependency
* intermediate releases were still broken in this respect

## 0.12.2 - 2018 Jun 14

* use OrderedSet's to preserve creation order
* more balanced graphical layout in case of nested schedulers
* 0.12.1 was broken, it used a couple of f-strings

## 0.11.4 - 2018 Jun 12

* schedulers are graphically rendered with right corners instead of rounded
* darker color for critical jobs - plain red was too much

## 0.11.3 - 2018 Jun 12

* new convenience method `export_as_pngfile()`

## 0.11.2 - 2018 May 15

* alter signature of co_shutdown() to remove argument `depth`, which is
  not relevant, and creates confusion for user libraries.
* there is still a need to more accurately specify the expected behaviour
  of co_shutdown() though, see also notes in PureScheduler.co_shutdown()

## 0.11.1 - 2018 May 10

This is a release candidate for 1.0:

### major changes

* default value for `critical` is now `True` for all species, jobs and schedulers alike - see #7
* shutdown() is no longer implicitly called by `run()`, it is now up to the caller to call this method - see #10
* critical schedulers now propagate exceptions so they can bubble up the nested schedulers tree - see #12
* co_shutdown() now must accept mandatory argument depth
* `rain_check()` renamed into `check_cycles()`

### enhancements

* schedulers have a new attribute `shutdown_timeout`, defaults to 1s
* `list()`, `list_safe()`, `check_cycles()` and `sanitize()` know about nested schedulers
* new method `PureScheduler.remove(job)`
* AbstractJob.requires() accepts kwarg `remove=True` to allow for removal of requirements
* enhance border width of critical jobs in dot representation for colorblind people
* `list_safe()` now shows requirements too
* more graphs in the README

### minor
* scheduler methods no longer accept a loop parameter

## 0.10.2 - 2018 May 2

* empty schedulers now run fine

## 0.10.1 - 2018 Apr 30

* make schedulers nestable by default - see issue #3
  * `Scheduler` is now the nestable class (formerly known as SchedulerJob);
  * `PureScheduler` is the new name for what was formerly known as `Scheduler`

* see issue #1 : `jobs_window` and `timeout` are no longer parameters
  to `co_run()`, but attributes of a `PureScheduler` object

* graphical layout - see issue #4
  * critical jobs or schedulers are shown with a red border
  * forever jobs or schedulers are shown with a dashed line

## 0.9.1 - 2018 Apr 25

* graphical output should now properly show nested schedulers in all cases of imbrications
* textual output marginally nicer too
* removed the formal definition of the Schedulable type hint that was only clobbering the doc
* major renaming; all methods that produce pieces of text for representing objects are called repr_something()
* more tools in tests.utils

## 0.8.2 - 2018 Apr 20

* `Scheduler.list()` shows nested jobs too
* resurrected the `PrintJob` class

## 0.8.1 - 2018 Apr 19

* new class SchedulerJob allows to ease the creation of **nested schedulers**;
  no support yet for graphical representation though
* in the process, reviewed names for Scheduler methods:
  * for synchroneous calls, one can use `run()` (preferred)
    or ``orchestrate()`` (legacy)
  * coroutine `co_orchestrate()` is now renamed into `co_run()`;
   `co_orchestrate()` is now absent from the code
* new class Watch for more elegant tests and nicer outputs

## 0.7.1 - 2018 Apr 17

* thoroughly reviewed the way custom labels are defined and used; classes that
  inherit `AbstractJob` can redefine text_label() and graph_label()
* graph production: both methods (dot and native digraph) now consistently
  accept argument `show_ids`
* major overhaul on the documentation
  * using the numpy style in docstrings
  * examples of nested schedulers
  * section on troubleshooting
* code is now totally pep8/flake8- and pylint- clean

## 0.6.1 - 2018 Mar 12

* adopt new layout for the doc - no source/ subdir under sphinx
* from asynciojobs import __version__
* cosmetic micro changes in the doc

## 0.6.0 - 2018 Feb 25

* Scheduler.graph() can natively visualize in a notebook
* Scheduler.run() an alias for orchestrate
* printing a scheduler shows number of jobs
* doc uses new sphinx theme

## 0.5.8 - 2018 Jan 16

* introduce dot_label() on jobs as a means
  to override label() when producing a dotfile

## 0.5.7 - 2017 Dec 19

* minor tweaks suggested by pylint

## 0.5.6 - 2017 Dec 18

* bugfix, remove one occurrence of Exceptin instead of Exception

## 0.5.5 - 2017 Nov 2

* just flushing a pile on harmless cosmetic changes

## 0.5.4 - 2016 Dec 15

* only minor changes, essentially PEP8-friendly
* with a very shy start at type hints
* but documentation w/ type hints is still unclear
  (in fact even without them, I can see weird extra '*')

## 0.5.2 - 2016 Dec 8

* setup uses setuptools and no distutils anymore
* cleaned __init__.py
* use super() in subclasses
* autodoc should now outline coroutines
* 0.5.1 broken

## 0.5.0 - 2016 Dec 6

* windowing capability to limit number of simultaneous jobs
* new status in job lifecycle: idle → scheduled → running → done
  'scheduled' means : waiting for a slot in window

## 0.4.6 - 2016 Dec 5

* much nicer dotfile output, using double quotes to render
  strings instead of identifiers like we were trying to do
* PrintJob can be created in a scheduler as well
* 0.4.5 is broken in PrintJob

## 0.4.4 - 2016 Dec 5

* feedback message is forced for severe conditions (crit. exc. and timeout)
* debrief(details)
* minor improvements in export_as_dotfile

## 0.4.3 - 2016 Dec 2

* hardened export_as_dotfile()

## 0.4.2 - 2016 Dec 1

* can create jobs and sequences with scheduler=

## 0.4.1 - 2016 Nov 30

* sphinx documentation on http://nepi-ng.inria.fr/asynciojobs

## 0.4.0 - 2016 Nov 21

* rename engine into scheduler

## 0.3.4 - 2016 Nov 20

* a first sphinx doc, but not yet available at readthedocs.org because
  I could not get rtd to run python3.5

## 0.3.3 - 2016 Nov 17

* Job's default_label() to provide a more meaningful default when label is not set
  on a Job instance

## 0.3.2 - 2016 Nov 17

* major bugfix, sometimes critical job was not properly dealt with because it was last
* new class PrintJob with an optional sleep delay
* Engine.list(details=True) gives details on all the jobs
  provided that they have the details() method

## 0.3.1 - 2016 Nov 15

* no semantic change, just simpler and nicer
* cosmetic : nicer list() that shows all jobs with a 4-characters pictogram
  that shows critical / forever / done/running/idle and if an exception occured
* verbosity reviewed : only one verbose flag for the engine obj

## 0.2.3 - 2016 Oct 23

* Engine.store_as_dotfile() can export job requirements graph to graphviz

## 0.2.2 - 2016 Oct 20

* bugfix for when using Engine.update/Engine.add with a Sequence

## 0.2.1 - 2016 Oct 7

* cleanup

## 0.2.0 - 2016 Oct 4

* robust and tested management of requirements throughout

## 0.1.2 - 2016 Oct 2

* only cosmetic

## 0.1.1 - 2016 Sep 28

* hardened and tested Sequence - can be nested and have required=
* jobs are listed in a more natural order by list() and debrief()

## 0.1.0 - 2016 Sep 27

* the Sequence class for modeling simple sequences without
  having to worry about the requires deps
* a critical job that raises an exception always gets its
  stack traced

## 0.0.6 - 2016 Sep 21

* in debug mode, show stack corresponding to caught exceptions
* various cosmetic

## 0.0.5 - 2016 Sep 21

* bugfix - missing await

## 0.0.4 - 2016 Sep 20

* Engine.verbose
* robustified some corner cases

## 0.0.3 - 2016 Sep 19

* Engine.why() and Engine.debrief()

## 0.0.2 - 2016 Sep 15

* tweaking pypi upload

## 0.0.1 - 2016 Sep 15

* initial version
