#!/usr/bin/env python
from setuptools import setup

long_description = open('README.rst').read()

setup(name='openstates',
      version='0.2.0',
      author="James Turk",
      author_email="jturk@sunlightfoundation.com",
      license="GPL v3",
      url="http://openstates.org",
      description='Open State Project',
      long_description=long_description,
      platforms=['any'],
)
