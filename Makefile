.PHONY: bootstrap
bootstrap: 
	test -d env || virtualenv env	
	env/bin/pip install -U pip
	$(MAKE) pip-requirements

.PHONY: test
test:
	tox

.PHONY: lint
lint:
	flake8 munificent

.PHONY: pip-requirements
pip-requirements: .make/pip-requirements

.make/pip-requirements: requirements*.txt | .make
	env/bin/pip install -r requirements*.txt
	touch $@

.make:
	mkdir -p .make

clean:
	rm -rf env
	rm -rf .make
	rm -rf .tox
	rm -rf **/*.pyc
