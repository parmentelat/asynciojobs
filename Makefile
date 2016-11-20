CONVERT = jupyter nbconvert --ExecutePreprocessor.enabled=True --ExecutePreprocessor.allow_errors=True
NBNORM = ../flotpython/tools/nbnorm.py

norm:
	$(NBNORM) --author "Thierry Parmentelat - Inria" README.ipynb

all: readme
readme: README.md
README.md: README-eval.ipynb
	$(CONVERT) --to markdown README-eval.ipynb --stdout > $@ || rm $@

README-eval.ipynb: README.ipynb
	jupyter nbconvert --ExecutePreprocessor.timeout=600 --to notebook --execute README.ipynb
	mv -f README.nbconvert.ipynb README-eval.ipynb

readme-clean:
	rm -f README.md README-eval.ipynb

.PHONY: all readme readme-clean

########## for uploading onto pypi
# this assumes you have an entry 'pypi' in your .pypirc
# see pypi documentation on how to create .pypirc

LIBRARY = asynciojobs

VERSION = $(shell python3 -c "from $(LIBRARY).version import version; print(version)")
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

##############################
tags:
	git ls-files | xargs etags

.PHONY: tags

##########
tests:
	python3 tests/tests.py
.PHONY: tests


########## actually install
infra:
	apssh -t r2lab.infra pip3 install --upgrade asynciojobs
check:
	apssh -t r2lab.infra python3 -c '"import asynciojobs.version as version; print(version.version)"'

.PHONY: infra check

########## docs
docs:
	$(MAKE) -C docs html

docs-clean:
	$(MAKE) -C docs clean

all-docs: readme-clean readme docs

.PHONY: docs docs-clean all-docs
