########## for uploading onto pypi
# this assumes you have an entry 'pypi' in your .pypirc
# see pypi documentation on how to create .pypirc

LIBRARY = asynciojobs

VERSION = $(shell python3 setup.py --version)
VERSIONTAG = $(LIBRARY)-$(VERSION)
GIT-TAG-ALREADY-SET = $(shell git tag | grep '^$(VERSIONTAG)$$')
# to check for uncommitted changes
GIT-CHANGES = $(shell echo $$(git diff HEAD | wc -l))

# run this only once the sources are in on the right tag
pypi:
	@if [ $(GIT-CHANGES) != 0 ]; then echo "You have uncommitted changes - cannot publish"; false; fi
	@if [ -n "$(GIT-TAG-ALREADY-SET)" ] ; then echo "tag $(VERSIONTAG) already set"; false; fi
	@if ! grep -q ' $(VERSION)' CHANGELOG.md ; then echo no mention of $(VERSION) in CHANGELOG.md; false; fi
	@echo "You are about to release $(VERSION) - OK (Ctrl-c if not) ? " ; read _
	git tag $(VERSIONTAG)
	./setup.py sdist upload -r pypi

# it can be convenient to define a test entry, say testpypi, in your .pypirc
# that points at the testpypi public site
# no upload to build.onelab.eu is done in this case
# try it out with
# pip install -i https://testpypi.python.org/pypi $(LIBRARY)
# dependencies need to be managed manually though
testpypi:
	./setup.py sdist upload -r testpypi

.PHONY: pypi testpypi

##############################
tags:
	git ls-files | xargs etags

.PHONY: tags

##########
tests test:
	python3 -m unittest
.PHONY: tests test

########## sphinx
# Extensions (see sphinx/source/conf.py)
# * for type hints - this is rather crucial
# https://github.com/agronholm/sphinx-autodoc-typehints
# pip3 install sphinx-autodoc-typehints
# * for coroutines - useful to mark async def's as *coroutine*
# http://pythonhosted.org/sphinxcontrib-asyncio/
# pip3 install sphinxcontrib-asyncio
readme-strip readme html doc:
	$(MAKE) -C sphinx $@

.PHONY: readme-strip readme html doc

##########
pyfiles:
	@git ls-files | grep '\.py$$' | grep -v '/conf.py$$'

pep8:
	$(MAKE) pyfiles | xargs flake8 --max-line-length=80 --exclude=__init__.py

pylint:
	$(MAKE) pyfiles | xargs pylint


.PHONY: pep8 pylint pyfiles

########## actually install
infra:
	apssh -t r2lab.infra pip3 install --upgrade asynciojobs
check:
	apssh -t r2lab.infra python3 -c '"import asynciojobs.version as version; print(version.version)"'
.PHONY: infra check
