all: doc

########## sphinx-generated doc
# Extensions (see sphinx/source/conf.py)
# * for type hints - this is rather crucial
# https://github.com/agronholm/sphinx-autodoc-typehints
doc:
	pip install ".[doc]" ".[graph]"
	$(MAKE) -C sphinx $@

.PHONY: doc

########## tests
tests:
	pip install ".[tests]"
	pytest

.PHONY: tests

##########
pyfiles:
	@git ls-files | grep '\.py$$' | grep -v '/conf.py$$'

pep8:
	$(MAKE) pyfiles | xargs flake8 --max-line-length=80 --exclude=__init__.py

pylint:
	$(MAKE) pyfiles | xargs pylint

.PHONY: pyfiles pep8 pylint

########## actually install
infra:
	apssh -t r2lab.infra pip install --upgrade asynciojobs
check:
	apssh -t r2lab.infra python -c '"import asynciojobs.version as version; print(version.version)"'
.PHONY: infra check
