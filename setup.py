#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os

from setuptools import find_packages, setup


NAME = 'munificent'
HERE = os.path.abspath(os.path.dirname(__file__))

# Load the package's __version__.py module as a dictionary.
about = {}
project_slug = NAME.lower().replace("-", "_").replace(" ", "_")
with open(os.path.join(HERE, project_slug, '__version__.py')) as f:
    exec(f.read(), about)

setup(
    name=NAME,
    version=about['__version__'],
    description='TODO',
    author='David Hughes',
    author_email='d@vidhughes.com',
    url='https://github.com/davehughes/munificent',
    packages=find_packages(exclude=('tests',)),
    install_requires=[
        'requests',
        'SqlAlchemy',
        ],
    include_package_data=True,
    # entry_points={
    #     'console_scripts': ['mycli=mymodule:cli'],
    # },
)
