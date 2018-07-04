#!/usr/bin/env python3

"""
package / install
"""

import setuptools

# https://packaging.python.org/guides/single-sourcing-package-version/
# set __version__ by read & exec of the python code
# this is better than an import that would otherwise try to
# import the whole package, and fail if a required module is not yet there
from pkg_resources import resource_string
VERSION_CODE = resource_string('asynciojobs', 'version.py')
ENV = {}
exec(VERSION_CODE, ENV)
__version__ = ENV['__version__']

LONG_DESCRIPTION = (
    "See notebook at https://github.com/parmentelat/"
    "asynciojobs/blob/master/README.ipynb"
)

REQUIRED_MODULES = [
    'orderedset',
]

setuptools.setup(
    name="asynciojobs",
    author="Thierry Parmentelat",
    author_email="thierry.parmentelat@inria.fr",
    description="A simplistic orchestration engine for asyncio-based jobs",
    license="CC BY-SA 4.0",
    keywords=['asyncio', 'dependency', 'dependencies',
              'jobs', 'scheduling', 'orchestration'],

    packages=['asynciojobs'],
    version=__version__,
    python_requires='>=3.5',

    install_requires=REQUIRED_MODULES,
    extras_require={
        'graph': ['graphviz'],
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
