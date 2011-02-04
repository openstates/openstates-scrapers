.. _pythonapi:

========
Scraping
========

All scrapers that can be run with :program:`scrape.py` utilize these classes.

A state scraper is comprised mainly of classes derived from :class:`~billy.scrape.bills.BillScraper`,
:class:`~billy.scrape.legislators.LegislatorScraper`, :class:`~billy.scrape.votes.VoteScraper`, and
:class:`~billy.scrape.committees.CommitteeScraper`.

The Scraper classes have a :meth:`scrape` method that when overridden is responsible for creating
:class:`~billy.scrape.bills.Bill`, :class:`~billy.scrape.legislators.Legislator`,
:class:`~billy.scrape.votes.Vote`, and :class:`~billy.scrape.committees.Committee` objects as appropriate.

.. module:: billy.scrape

billy.scrape
============

Scraper
-------

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
.. autoclass:: billy.scrape.votes.VoteScraper
   :members: scrape, save_vote

Vote
----
.. autoclass:: billy.scrape.votes.Vote
   :members: __init__, yes, no, other, add_source


.. module:: billy.scrape.legislators

Legislators
===========

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

CommitteeScraper
----------------
.. autoclass:: billy.scrape.committees.CommitteeScraper
   :members: scrape, save_committee

Committee
---------
.. autoclass:: billy.scrape.committees.Committee
   :members: __init__, add_member
