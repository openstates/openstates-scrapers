***************
Scraping Basics
***************

All scrapers inherit from :class:`billy.scrape.Scraper`, which provides
basic functionality that derived scrapers will use. All derived scrapers must implement
a :func:`scrape` method.

The most useful on the base :class:`Scraper` class is ``urlopen(url, method='GET', body=None)``.
``Scraper.urlopen`` opens a URL and returns a string-like object that can then be
parsed by a library like `lxml <http://codespeak.net/lxml>`_.

This method provides advantages over built-in urlopen methods in that the underlying :class:`Scraper` class can be configured to support rate-limiting, caching, and provides robust error handling.

.. note::
    For advanced usage see `scrapelib <http://github.com/sunlightlabs/scrapelib/>`_ which provides the basis for :class:`billy.scrape.Scraper`.

Logging
=======

The base class also configures a `python logger <http://docs.python.org/library/logging.html>`_ instance and provides several shortcuts for logging at various log levels:

``log(msg, *args, **kwargs)``
    log a message with level ``logging.INFO``
``debug(msg, *args, **kwargs)``
    log a message with level ``logging.DEBUG``
``warning(msg, *args, **kwargs)``
    log a message with level ``logging.WARNING``

.. note::
    It is also possible to access the ``self.logger`` object directly.

Bills
=====

Each ``xy/bills.py`` should define a ``XYBillScraper`` that derives from
:class:`billy.scrape.bills.BillScraper` and implements the ``scrape(chamber, session)``
method.

As your ``scrape`` method gathers bills, it should create :class:`billy.scrape.bills.Bill`
objects and call ``self.save_bill`` when it has added all related actions/sources to a bill.

Sometimes it is easiest to also add votes to bills at this time, to add a vote that took place on a specific motion create :class:`billy.scrape.votes.Vote` objects and attach them using a Bill's ``add_vote`` method.

Votes
=====

Some sites store votes separately from bills so scraping them together is counterintuitive.  In these
cases you can provide a ``xy/votes.py`` containing a ``XYVoteScraper`` that derives from
:class:`billy.scrape.bills.VoteScraper` and implements the ``scrape(chamber, session)``
method.

As your ``scrape`` method gathers votes, it should create :class:`billy.scrape.votes.Vote`
objects and save them with ``self.save_vote``.

.. note::
    If your ``XYBillScraper`` gathers votes you should not provide a ``XYVoteScraper``.


Legislators
===========

Each ``xy/legislators.py`` should define a ``XYLegislatorScraper`` that derives from
:class:`billy.scrape.legislators.LegislatorScraper` and implements the ``scrape(chamber, term)`` method.

Your ``scrape`` method should create :class:`billy.scrape.legislators.Legislator`
objects and call ``self.save_legislator`` on them.

In many cases it is not possible to retrieve legislators prior to the current session, in these cases it is acceptable to raise a :class:`billy.scrape.NoDataForPeriod` exception.

Committees
==========

Each ``xy/committees.py`` should define a ``XYCommitteeScraper`` that derives from :class:`billy.scrape.committees.CommitteeScraper` and implements the ``scrape(chamber, term)`` method.

Your ``scrape`` method should create :class:`billy.scrape.committee.Committee`
objects and call ``self.save_committee`` on them.

In many cases it is not possible to retrieve committees prior to the current session,
in these cases it is acceptable to raise a :class:`billy.scrape.NoDataForPeriod` exception.

.. note::
    If your ``XYLegislatorScraper`` gathers committees you should not provide a ``XYCommitteeScraper``.
