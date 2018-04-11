#!/usr/bin/env python3

"""
package / install
"""

from sys import version_info

import setuptools

from asynciojobs import __version__

# check python version
MAJOR, MINOR = version_info[0:2]
if not (MAJOR == 3 and MINOR >= 5):
    print("python 3.5 or higher is required")
    exit(1)


LONG_DESCRIPTION = \
                   "See notebook at https://github.com/parmentelat/" \
                   "asynciojobs/blob/master/README.ipynb"

REQUIRED_MODULES = []

setuptools.setup(
    name="asynciojobs",
    version=__version__,
    author="Thierry Parmentelat",
    author_email="thierry.parmentelat@inria.fr",
    description="A simplistic orchestration engine for asyncio-based jobs",
    long_description=LONG_DESCRIPTION,
    license="CC BY-SA 4.0",
    url="http://asynciojobs.readthedocs.io/",
    packages=['asynciojobs'],
    install_requires=REQUIRED_MODULES,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Information Technology",
        "Programming Language :: Python :: 3.5",
    ],
)
