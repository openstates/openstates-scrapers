.. _pythonapi:

==================
Python Scraper API
==================

LegislationScraper
==================

.. autoclass:: pyutils.legislation.LegislationScraper
   :members: __init__, urlopen, log, add_bill, add_legislator, scrape_bills, scrape_legislators, scrape_metadata

Bill
====
.. autoclass:: pyutils.legislation.Bill
   :members: __init__, add_action, add_sponsor, add_version, add_vote

Vote
====
.. autoclass:: pyutils.legislation.Vote
   :members: __init__, yes, no, other

Legislator
==========
.. autoclass:: pyutils.legislation.Legislator
   :members: __init__

Exceptions
==========
.. autoclass:: pyutils.legislation.ScrapeError

.. autoclass:: pyutils.legislation.NoDataForYear
