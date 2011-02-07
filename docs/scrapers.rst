.. _scrapers:

================
Writing Scrapers
================

A state scraper is implementing by providing classes derived from :class:`~billy.scrape.bills.BillScraper`,
:class:`~billy.scrape.legislators.LegislatorScraper`, :class:`~billy.scrape.votes.VoteScraper`, and
:class:`~billy.scrape.committees.CommitteeScraper`.

Derived scraper classes should override the :meth:`scrape` method that that is responsible for creating
:class:`~billy.scrape.bills.Bill`, :class:`~billy.scrape.legislators.Legislator`,
:class:`~billy.scrape.votes.Vote`, and :class:`~billy.scrape.committees.Committee` objects as appropriate.

Example state scraper directory structure::

    ./ex/__init__.py      # metadata for "ex" state scraper
    ./ex/bills.py         # contains EXBillScraper (also scrapes Votes)
    ./ex/legislators.py   # contains EXLegislatorScraper
    ./ex/committees.py    # contains EXCommitteeScraper

.. module:: billy.scrape

billy.scrape
============

Scraper
-------

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



.. autoclass:: billy.scrape.Scraper
   :members: __init__, urlopen, validate_session, validate_term

SourcedObject
-------------

.. autoclass:: billy.scrape.SourcedObject
    :members: add_source

Exceptions
----------

.. autoclass:: billy.scrape.ScrapeError

.. autoclass:: billy.scrape.NoDataForPeriod


.. module:: billy.scrape.bills

Bills
=====

BillScraper
-----------

``BillScraper`` implementations should gather and save :class:`~billy.scrape.bills.Bill` objects.

Sometimes it is easiest to also gather :class:`~billy.scrape.votes.Vote` objects in a BillScraper as well,
these can be attached to :class:`~billy.scrape.bills.Bill` objects via the :meth:`add_vote` method.


.. autoclass:: billy.scrape.bills.BillScraper
   :members: scrape, save_bill

Bill
----
.. autoclass:: billy.scrape.bills.Bill
   :members: __init__, add_action, add_sponsor, add_vote, add_title,
             add_version, add_document, add_source


.. module:: billy.scrape.votes

Votes
=====

VoteScraper
-----------

``VoteScraper`` implementations should gather and save :class:`~billy.scrape.votes.Vote` objects.

If a state's ``BillScraper`` gathers votes it is not necessary to provide a ``VoteScraper`` implementation.

.. autoclass:: billy.scrape.votes.VoteScraper
   :members: scrape, save_vote

Vote
----
.. autoclass:: billy.scrape.votes.Vote
   :members: __init__, yes, no, other, add_source


.. module:: billy.scrape.legislators

Legislators
===========

``LegislatorScraper`` implementations should gather and save :class:`~billy.scrape.legislators.Legislator` objects.

Sometimes it is easiest to also gather committee memberships at the same time as legislators.  Committee memberships can can be attached to :class:`~billy.scrape.legislators.Legislator` objects via the :meth:`add_role` method.

LegislatorScraper
-----------------
.. autoclass:: billy.scrape.legislators.LegislatorScraper
   :members: scrape, save_legislator

Person
------
.. autoclass:: billy.scrape.legislators.Person
   :members: __init__, add_role

Legislator
----------
.. autoclass:: billy.scrape.legislators.Legislator
   :members: __init__, add_source


.. module:: billy.scrape.committees

Committees
==========

``CommitteeScraper`` implementations should gather and save :class:`~billy.scrape.committees.Committee` objects.

If a state's ``LegislatorScraper`` gathers committee memberships it is not necessary to provide a ``CommitteeScraper`` implementation.

CommitteeScraper
----------------
.. autoclass:: billy.scrape.committees.CommitteeScraper
   :members: scrape, save_committee

Committee
---------
.. autoclass:: billy.scrape.committees.Committee
   :members: __init__, add_member
