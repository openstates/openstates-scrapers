=================
Writing A Scraper
=================

We provide a number of utility classes that scrapers should use that facilitate
retrieving resources, error handling, logging, and storing collected data.

.. contents::
   :local:


.. _metadata:

Providing Metadata
==================

All states should provide a ``metadata`` dictionary in their ``__init__.py``.

The following keys are required:

`state_name`
    the full name of this state, e.g. New Hampshire
`legislature name`
    the name of this state's legislative body, e.g. `"Texas Legislature"`
`upper_chamber_name`
    the name of the upper chamber of this state's legislature, e.g. `"Senate"`
`lower_chamber_name`
    the name of the lower chamber of this state's legislature, e.g. `"House of Representatives"` 
`upper_title`
    the title of a member of this state's upper chamber, e.g. `"Senator"`
`lower_title`
    the title of a member of this state's lower chamber, e.g. `"Representative"`
`upper_term`
    the length, in years, of a term in this state's upper chamber, e.g. `4`
`lower_term`
    the length, in years, of a term in this state's lower chamber, e.g. `2`
`sessions`
    an ordered list of available sessions, e.g.  `['2005-2006', '2007-2008', '2009-2010']
`session_details`
    a dictionary, with an entry for each session indicating
    the years it encompasses as well as any 'sub' sessions, e.g.::

       {'2009-2010': {'years': [2009, 2010],
                      'sub_sessions': ["2009 Special Session 1"]}}

.. _scraping-basics:

Scraping Basics
===============

All scrapers inherit from :class:`fiftystates.scrape.Scraper`, which provides
basic functionality that derived scrapers will use.

The most useful on the base `Scraper` class is ``urlopen(url, method='GET', body=None)``.
``Scraper.urlopen`` opens a URL and returns a string-like object that can then be
parsed by a library like `lxml <http://codespeak.net/lxml/>`_.

This method provides advantages over built-in urlopen methods in that the underlying ``Scraper``
class can be configured to support rate-limiting, caching, and provides robust error handling.

For advanced usage see `scrapelib <http://github.com/mikejs/scrapelib/>`_.

Logging
-------

The base class also configures a `python logger <http://docs.python.org/library/logging.html>`_
instance and provides several shortcuts for logging at various log levels:

``log(msg, *args, **kwargs)``
    log an message with level ``logging.INFO``
``debug(msg, *args, **kwargs)``
    log a message with level ``logging.DEBUG``
``warning(msg, *args, **kwargs)``
    log a message with level ``logging.WARNING``

It is also possible to access the ``self.logger`` object directly.

.. _bills:

Bills
=====

.. _votes:

Votes
=====

.. _legislators:

Legislators
===========

.. _committees:

Committees
==========

