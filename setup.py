#!/usr/bin/env python
from setuptools import setup
from fiftystates.client import __version__

long_description = open('README.rst').read()

setup(name="fiftystates",
      version=__version__,
      namespace_packages=['fiftystates'],
      packages=['fiftystates.scrape', 'fiftystates.backend',
                'fiftystates.site'],
      description="The Fifty State Project",
      author="Michael Stephens",
      author_email="mstephens@sunlightfoundation.com",
      license="BSD",
      url="http://github.com/sunlightlabs/fiftystates",
      long_description=long_description,
      platforms=["any"],
      classifiers=["Development Status :: 4 - Beta",
                   "Intended Audience :: Developers",
                   "License :: OSI Approved :: BSD License",
                   "Natural Language :: English",
                   "Operating System :: OS Independent",
                   "Programming Language :: Python",
                   "Topic :: Software Development :: Libraries :: Python Modules",
                   ],
      )
