#!/usr/bin/env python
from setuptools import setup

long_description = open('README.rst').read()

setup(name='openstates',
      version='1.3.0',
      author="James Turk",
      author_email="jturk@sunlightfoundation.com",
      license="GPL v3",
      url="http://openstates.org",
      description='Open States',
      long_description=long_description,
      platforms=['any'],
)
