#!/usr/bin/env python3

from __future__ import print_function

import sys
import os
import os.path
from distutils.core import setup
from asynciojobs.version import version as asynciojobs_version

# check python version
from sys import version_info
major, minor= version_info[0:2]
if not (major == 3 and minor >= 5):
    print("python 3.5 or higher is required")
    exit(1)

# read licence info
with open("COPYING") as f:
    license = f.read()
#with open("README.md") as f:
#    long_description = f.read()
long_description = "See notebook at https://github.com/parmentelat/asynciojobs/blob/master/README.ipynb"

### requirements - used by pip install
# *NOTE* for ubuntu: also run this beforehand
# apt-get -y install libffi-dev
# which is required before pip can install asyncssh
required_modules = [
    'asyncssh',
]

setup(
    name             = "asynciojobs",
    version          = asynciojobs_version,
    description      = "A simplistic orchestration engine for asyncio-based jobs",
    long_description = long_description,
    license          = license,
    author           = "Thierry Parmentelat",
    author_email     = "thierry.parmentelat@inria.fr",
    download_url     = "http://github/build.onelab.eu/asynciojobs/asynciojobs-{v}.tar.gz".format(v=asynciojobs_version),
    url              = "https://github.com/parmentelat/fitsophia/tree/master/asynciojobs",
    platforms        = "Linux",
    packages         = [ 'asynciojobs' ],
    scripts          = [ 'bin/asynciojobs'],
    install_requires = required_modules,
)

