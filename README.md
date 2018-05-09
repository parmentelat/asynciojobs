# Purpose

The `asynciojobs` library adds dependency management to asyncio-based scenarios.

It allows to create and run schedulers, where jobs are coroutines or other
asyncio-friendly programs, whose dependencies are directed acyclic graphs
(DAGs).

Schedulers can be nested, i.e. a scheduler can be used as a job;
functions can be written, that return pieces of scenarios.

# Read more at readthedocs

See complete documentation at http://asynciojobs.readthedocs.io/
