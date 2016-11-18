# 0.3.3 - 2016 Nov 17

* Job's default_label() to provide a more meaningful default when label is not set
  on a Job instance

# 0.3.2 - 2016 Nov 17

* major bugfix, sometimes critical job was not properly dealt with because it was last
* new class PrintJob with an optional sleep delay
* Engine.list(details=True) gives details on all the jobs
  provided that they have the details() method

# 0.3.1 - 2016 Nov 15

* no semantic change, just simpler and nicer
* cosmetic : nicer list() that shows all jobs with a 4-characters pictogram
  that shows critical / forever / done/running/idle and if an exception occured
* verbosity reviewed : only one verbose flag for the engine obj

# 0.2.3 - 2016 Oct 23

* Engine.store_as_dotfile() can export job requirements graph to graphviz 

# 0.2.2 - 2016 Oct 20

* bugfix for when using Engine.update/Engine.add with a Sequence

# 0.2.1 - 2016 Oct 7

* cleanup

# 0.2.0 - 2016 Oct 4

* robust and tested management of requirements throughout

# 0.1.2 - 2016 Oct 2

* only cosmetic

# 0.1.1 - 2016 Sep 28

* hardened and tested Sequence - can be nested and have required=
* jobs are listed in a more natural order by list() and debrief()

# 0.1.0 - 2016 Sep 27

* the Sequence class for modeling simple sequences without
  having to worry about the requires deps
* a critical job that raises an exception always gets its
  stack traced

# 0.0.6 - 2016 Sep 21

* in debug mode, show stack corresponding to caught exceptions
* various cosmetic 

# 0.0.5 - 2016 Sep 21

* bugfix - missing await

# 0.0.4 - 2016 Sep 20

* Engine.verbose
* robustified some corner cases

# 0.0.3 - 2016 Sep 19

* Engine.why() and Engine.debrief()

# 0.0.2 - 2016 Sep 15

* tweaking pypi upload

# 0.0.1 - 2016 Sep 15

* initial version

