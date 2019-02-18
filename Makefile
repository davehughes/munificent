.PHONY: bootstrap
bootstrap: 
	test -d env || virtualenv env	
	env/bin/pip install -U pip
	$(MAKE) pip-requirements

.PHONY: test
test:
	tox

.PHONY: pip-requirements
pip-requirements: .make/pip-requirements

.make/pip-requirements: requirements*.txt | .make
	echo -n $? | xargs -d" " -I{} env/bin/pip install -r {}
	touch $@

.make:
	mkdir -p .make

clean:
	rm -rf env
	rm -rf .make
	rm -rf .tox
	rm -rf **/*.pyc
