#!/usr/bin/env python
from setuptools import setup

long_description = open("README.md").read()

setup(
    name="openstates",
    version="2017",
    author="James Turk",
    author_email="james@openstates.org",
    license="GPL v3",
    url="http://openstates.org",
    description="Open States",
    long_description=long_description,
    platforms=["any"],
)
