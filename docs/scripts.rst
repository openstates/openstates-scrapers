=============
Billy Scripts
=============

Billy is primarily composed of a handful of scripts that help facilitate the scraping, import, and cleanup process.

Scraping
========

.. program:: scrape.py

:program:`scrape.py` <STATE>
----------------------------

.. option:: STATE

    state scraper module name (eg. nc) [required]

.. option:: --alldata

    include all available scrapers

.. option:: --upper, --lower

    scrape upper/lower chamber (if neither is specified will include both)

.. option:: --bills, --legislators, --votes, --committees, --events

    include (bill, legislator, vote, committee, event) scraper

.. option:: -v, --verbose

    be verbose (use multiple times for more verbosity)

.. option:: -s SESSIONS, --sessions SESSIONS

    session(s) to scrape, must be present in the state's metadata

.. option:: --strict

    fail immediately when encountering validation warnings

.. option:: -n, --no_cache

    do not use cache

.. option:: -r RPM, --rpm RPM

    set maximum number of requests per minute
