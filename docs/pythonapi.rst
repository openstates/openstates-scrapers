.. _pythonapi:

========================
Python Scraper Interface
========================

Scraper
-------

.. autoclass:: fiftystates.scrape.Scraper
   :members: __init__, urlopen, scrape

Exceptions
==========

.. autoclass:: fiftystates.scrape.ScrapeError

.. autoclass:: fiftystates.scrape.NoDataForYear

Bills
=====

BillScraper
-----------
.. autoclass:: fiftystates.scrape.bills.BillScraper
   :members: scrape, save_bill

Bill
----
.. autoclass:: fiftystates.scrape.bills.Bill
   :members: __init__, add_action, add_sponsor, add_version, add_vote,
             add_source

Votes
=====

VoteScraper
-----------
.. autoclass:: fiftystates.scrape.votes.VoteScraper
   :members: scrape, save_vote

Vote
----
.. autoclass:: fiftystates.scrape.votes.Vote
   :members: __init__, yes, no, other, add_source

Legislators
===========

LegislatorScraper
-----------------
.. autoclass:: fiftystates.scrape.legislators.LegislatorScraper
   :members: scrape, save_legislator

Person
------
.. autoclass:: fiftystates.scrape.legislators.Person
   :members: __init__, add_role

Legislator
----------
.. autoclass:: fiftystates.scrape.legislators.Legislator
   :members: __init__, add_source

Committees
==========

CommitteeScraper
----------------
.. autoclass:: fiftystates.scrape.committees.CommitteeScraper
   :members: scrape, save_committee

Committee
---------
.. autoclass:: fiftystates.scrape.committees.Committee
   :members: __init__, add_member
