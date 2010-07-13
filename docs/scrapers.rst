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
`terms`
    a list of dictionaries, with an entry for each term indicating
    the years it encompasses as well as all related sessions, e.g.::

       [
        {'name': '2001-2002',
         'sessions': ['2001 Regular Session',
                      'May 2002 Special Session',
                      'May 2001 Special Session'],
         'start_year': 2001, 'end_year': 2002},
        {'name': '2003-2004',
         'sessions': ['2003 Regular Session',
                      'Jan 2003 Special Session'],
         'start_year': 2003, 'end_year': 2004},
       ]

.. _scraping-basics:

Scraping Basics
===============

All scrapers inherit from :class:`fiftystates.scrape.Scraper`, which provides
basic functionality that derived scrapers will use. All derived scrapers must implement
a ``scrape(chamber, year)`` method.

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

Each ``xy/bills.py`` should define a ``XYBillScraper`` that derives from
:class:`fiftystates.scrape.bills.BillScraper` and implements the ``scrape(chamber, year)``
method.

As your ``scrape`` method gathers bills, it should create :class:`fiftystates.scrape.bills.Bill`
objects and call ``self.save_bill`` when it has added all related actions/sources to a bill.

Often it is easiest to also add votes at this time, to add a vote that took place on a
specific motion create :class:`fiftystates.scrape.votes.Vote` objects and attach them using a
Bill's ``add_vote`` method.

.. _votes:

Votes
=====

Sometimes it is difficult to gather votes as bills are being collected, in these
cases you can provide a ``xy/votes.py`` containing a ``XYVoteScraper`` that derives from
:mod:`fiftystates.scrape.bills.VoteScraper` and implements the ``scrape(chamber, year)``
method.

As your ``scrape`` method gathers votes, it should create :class:`fiftystates.scrape.votes.Vote`
objects and save them with ``self.save_vote``.

If your ``XYBillScraper`` gathers votes you should not provide a ``XYVoteScraper``.

.. _legislators:

Legislators
===========

Each ``xy/legislators.py`` should define a ``XYLegislatorScraper`` that derives from
:class:`fiftystates.scrape.legislators.LegislatorScraper` and implements the
``scrape(chamber, year)`` method.

Your ``scrape`` method should create :class:`fiftystates.scrape.legislators.Legislator`
objects and call ``self.save_legislator`` on them.

In many cases it is not possible to retrieve legislators prior to the current session,
in these cases it is acceptable to raise a :class:`fiftystates.scrape.NoDataForYear`
exception.

.. _committees:

Committees
==========

Each ``xy/committees.py`` should define a ``XYCommitteeScraper`` that derives from
:class:`fiftystates.scrape.committees.CommitteeScraper` and implements the
``scrape(chamber, year)`` method.

Your ``scrape`` method should create :class:`fiftystates.scrape.committee.Committee`
objects and call ``self.save_committee`` on them.

In many cases it is not possible to retrieve legislators prior to the current session,
in these cases it is acceptable to raise a :class:`fiftystates.scrape.NoDataForYear`
exception.
