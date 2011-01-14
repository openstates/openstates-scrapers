.. _pythonapi:

========================
Python Scraper Interface
========================

Scraper
-------

.. autoclass:: billy.scrape.Scraper
   :members: __init__, urlopen

Exceptions
==========

.. autoclass:: billy.scrape.ScrapeError

.. autoclass:: billy.scrape.NoDataForPeriod

Bills
=====

BillScraper
-----------
.. autoclass:: billy.scrape.bills.BillScraper
   :members: scrape, save_bill

Bill
----
.. autoclass:: billy.scrape.bills.Bill
   :members: __init__, add_action, add_sponsor, add_version, add_vote,
             add_source

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
