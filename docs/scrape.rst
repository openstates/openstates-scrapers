.. _pythonapi:

========================
Python Scraper Interface
========================

LegislationScraper
==================

.. autoclass:: fiftystates.scrape.utils.legislation.LegislationScraper
   :members: __init__, urlopen, log, save_bill, save_legislator, scrape_bills, scrape_legislators, scrape_metadata, save_person, urlopen, urlopen_context, lxml_context, run

Bill
====
.. autoclass:: fiftystates.scrape.utils.legislation.Bill
   :members: __init__, add_action, add_sponsor, add_version, add_vote,
             add_source

Vote
====
.. autoclass:: fiftystates.scrape.utils.legislation.Vote
   :members: __init__, yes, no, other, add_source

Person
======
.. autoclass:: fiftystates.scrape.utils.legislation.Person
   :members: __init__, add_role

Legislator
==========
.. autoclass:: fiftystates.scrape.utils.legislation.Legislator
   :members: __init__, add_source

Exceptions
==========
.. autoclass:: fiftystates.scrape.utils.legislation.ScrapeError

.. autoclass:: fiftystates.scrape.utils.legislation.NoDataForYear
