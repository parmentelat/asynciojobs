"""
Schedulers and jobs requirements are essentially sets of jobs,
and from a semantic point of view, order does not matter.

However for debugging/cosmetic reasons,
keeping track of creation order can be convenient.

So using ``OrderedSet`` looks like a good idea;
but it turns out that on some distros like fedora,
installing ``OrderedSet`` can be a pain, as it involves recompiling C code,
which in turn pulls in a great deal of dependencies.

For this reason, we use ``OrderedSet`` only if available,
and resort to regular sets otherwise.
On macos or ubuntu, fortunately, this can be simply achieved with::

    pip3 install orderedset

or alternatively with::

    pip3 install asynciojobs[ordered]
"""

# pylint: disable=e0401, w0611

try:
    from orderedset import OrderedSet as BestSet
except ImportError:
    BestSet = set
