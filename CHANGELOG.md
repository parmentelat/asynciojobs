# ChangeLog

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
