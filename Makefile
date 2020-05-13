########## for uploading onto pypi
# updated in May 2020 to use twine for uploads
# run pip install twine if needed
# to initialize twine credentials
# keyring set https://upload.pypi.org/legacy/ parmentelat
# keyring set https://test.pypi.org/legacy/ parmentelat

LIBRARY = asynciojobs

VERSION = $(shell python3 -c "from $(LIBRARY).version import __version__; print(__version__)")
VERSIONTAG = $(LIBRARY)-$(VERSION)
GIT-TAG-ALREADY-SET = $(shell git tag | grep '^$(VERSIONTAG)$$')
# to check for uncommitted changes
GIT-CHANGES = $(shell echo $$(git diff HEAD | wc -l))

# run this only once the sources are in on the right tag
pypi: cleanpypi
	@if [ $(GIT-CHANGES) != 0 ]; then echo "You have uncommitted changes - cannot publish"; false; fi
	@if [ -n "$(GIT-TAG-ALREADY-SET)" ] ; then echo "tag $(VERSIONTAG) already set"; false; fi
	@if ! grep -q ' $(VERSION)' CHANGELOG.md ; then echo no mention of $(VERSION) in CHANGELOG.md; false; fi
	@echo "You are about to release $(VERSION) - OK (Ctrl-c if not) ? " ; read _
	git tag $(VERSIONTAG)
	./setup.py sdist bdist_wheel
	twine upload dist/*

testpypi: cleanpypi
	./setup.py sdist bdist_wheel
	twine upload --repository-url https://test.pypi.org/legacy/ dist/*

cleanpypi:
	rm -rf build dist

.PHONY: pypi testpypi cleanpypi

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
