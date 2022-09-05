include Makefile.pypi

##############################
tags:
	git ls-files | xargs etags

.PHONY: tags

##########
tests test:
	pytest

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
