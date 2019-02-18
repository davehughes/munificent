VIRTUALENV=env

.PHONY: bootstrap
bootstrap: pip-requirements

.PHONY: test
test: pip-requirements
	$(VIRTUALENV)/bin/tox

.PHONY: pip-requirements
pip-requirements: .make/pip-requirements

$(VIRTUALENV):
	virtualenv $(VIRTUALENV) --python=python3
	$(VIRTUALENV)/bin/pip install -U pip

.make/pip-requirements: requirements*.txt | .make $(VIRTUALENV)
	echo -n $? | xargs -d" " -I{} $(VIRTUALENV)/bin/pip install -r {}
	touch $@

.make:
	mkdir -p .make

clean:
	rm -rf env
	rm -rf .make
	rm -rf .tox
	rm -rf **/*.pyc
