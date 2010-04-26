.. _pythonapi:

==================
Python Scraper API
==================

LegislationScraper
==================

.. autoclass:: pyutils.legislation.LegislationScraper
   :members: __init__, urlopen, log, add_bill, add_legislator, scrape_bills, scrape_legislators, scrape_metadata, add_person, urlopen, urlopen_context, run

Bill
====
.. autoclass:: pyutils.legislation.Bill
   :members: __init__, add_action, add_sponsor, add_version, add_vote,
             add_source

Vote
====
.. autoclass:: pyutils.legislation.Vote
   :members: __init__, yes, no, other, add_source

Person
======
.. autoclass:: pyutils.legislation.Person
   :members: __init__, add_role

Legislator
==========
.. autoclass:: pyutils.legislation.Legislator
   :members: __init__, add_source

Exceptions
==========
.. autoclass:: pyutils.legislation.ScrapeError

.. autoclass:: pyutils.legislation.NoDataForYear
