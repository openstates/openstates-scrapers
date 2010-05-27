.. _pythonapi:

==================
Python Scraper API
==================

LegislationScraper
==================

.. autoclass:: legislation.LegislationScraper
   :members: __init__, urlopen, log, save_bill, save_legislator, scrape_bills, scrape_legislators, scrape_metadata, save_person, urlopen, urlopen_context, lxml_context, run

Bill
====
.. autoclass:: legislation.Bill
   :members: __init__, add_action, add_sponsor, add_version, add_vote,
             add_source

Vote
====
.. autoclass:: legislation.Vote
   :members: __init__, yes, no, other, add_source

Person
======
.. autoclass:: legislation.Person
   :members: __init__, add_role

Legislator
==========
.. autoclass:: legislation.Legislator
   :members: __init__, add_source

Exceptions
==========
.. autoclass:: legislation.ScrapeError

.. autoclass:: legislation.NoDataForYear
