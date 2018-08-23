#!/usr/bin/env python3


"""
package / install
"""

import setuptools

# https://packaging.python.org/guides/single-sourcing-package-version/
# set __version__ by read & exec of the python code
# this is better than an import that would otherwise try to
# import the whole package, and fail if a required module is not yet there
from pathlib import Path                                # pylint: disable=c0411

VERSION_FILE = Path(__file__).parent / "asynciojobs" / "version.py"
ENV = {}
with VERSION_FILE.open() as f:
    exec(f.read(), ENV)                                 # pylint: disable=w0122
__version__ = ENV['__version__']

LONG_DESCRIPTION = (
    "See notebook at https://github.com/parmentelat/"
    "asynciojobs/blob/master/sphinx/README.ipynb"
)

REQUIRED_MODULES = [
    # orderedset is now optional - see extras_require below
]

setuptools.setup(
    name="asynciojobs",
    author="Thierry Parmentelat",
    author_email="thierry.parmentelat@inria.fr",
    description="A simplistic orchestration engine for asyncio-based jobs",
    long_description=LONG_DESCRIPTION,
    license="CC BY-SA 4.0",
    keywords=['asyncio', 'dependency', 'dependencies',
              'jobs', 'scheduling', 'orchestration'],

    packages=['asynciojobs'],
    version=__version__,
    python_requires='>=3.5',

    install_requires=REQUIRED_MODULES,
    extras_require={
        'graph': ['graphviz'],
        'ordered': ['orderedset'],
    },

    project_urls={
        'source': 'http://github.com/parmentelat/asynciojobs',
        'documentation': 'http://asynciojobs.readthedocs.io/',
    },

    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Information Technology",
        "Programming Language :: Python :: 3.5",
    ],
)
