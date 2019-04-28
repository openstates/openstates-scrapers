The Open States project collects and makes available data about state legislative activities, including bill summaries, votes, sponsorships and state legislator information. This data is gathered directly from the states and made available in a common format for interested developers, through a JSON API and data dumps.

Links
=====

* `Open States Project API <https://docs.openstates.org/api/>`_
* `Code on GitHub <https://github.com/openstates/openstates/>`_
* `Issue Tracker <https://github.com/openstates/openstates/issues>`_
* `Open States Discourse <https://discourse.openstates.org>`_

Getting Started
===============

We use `Docker <https://www.docker.com/products/docker>`_ to provide a reproducible development environment. Make sure
you have Docker installed.

Inside your Open States repository directory, run a scrape for a specific state by running::

  docker-compose run --rm scrape <state postal code>

You can also choose to scrape only specific data types for a state. The data types available vary from state to state; look at the ``scrapers`` listed in the state's ``__init__.py`` for a list. For example, Tennessee (with a state postal code of ``tn``) has::

    scrapers = {
        'bills': TNBillScraper,
        'committees': TNCommitteeScraper,
        'events': TNEventScraper,
        'people': TNPersonScraper,
    }

So you can limit a Tennessee scrape to only committees and legislators using::

  docker-compose run --rm scrape tn committees people

After retrieving everything from the state, ``scrape`` imports the data into a PostgreSQL database. If you want to skip this step, include a ``--scrape`` flag at the end of your command, like so::

  docker-compose run --rm scrape tn committees people --scrape

If you *do* want to import data into Postgres, start a Postgres service using Docker Compose::

    docker-compose up postgres

Then run database migrations and import `jurisdictions <https://opencivicdata.readthedocs.io/en/latest/data/jurisdiction.html>`_, thus initializing the database contents::

    docker-compose run --rm dbinit

Now you can run the scrape service without the ``--scrape`` flag, and data will be imported into Postgres. You can connect to the database and inspect data using ``psql`` (credentials are set in ``docker-compose.yml``)::

    psql postgres://postgres:secret@localhost:5432/openstates

After you run ``scrape`` (with or without the Postgres import), it will leave one JSON file in the ``_data`` subdirectory for each entity that was scraped. These JSON files contain the transformed, scraped data, and are very useful for debugging.

Check out the `writing scrapers guide <https://docs.openstates.org/en/latest/contributing/getting-started.html>`_ to understand more about how the scrapers work, and how you can contribute.

Testing
=======

Our scraping framework, Pupa, has a strong test harness, and requires well-structured data when ingesting. Furthermore, Open States scrapers should be written to fail when they encounter unexpected data, rather than guessing at its format and possibly ingesting bad data. Together, this means that there aren't many benefits to writing unit tests for particular Open States scrapers, versus high upkeep costs.

Occasionally, states *will* have unit tests, though, for specific structural cases. To run all tests::

  docker-compose run --rm --entrypoint=nosetests scrape /srv/openstates-web/openstates

API Keys
========

A few states require credentials to access their APIs. If you want to run code for these states, get credentials for yourself using these steps:

* NY

  * Get credentials at: https://legislation.nysenate.gov/#signup
  * Set in environment prior to running scrape: ``NEW_YORK_API_KEY``

* IN

  * Get credentials at: http://docs.api.iga.in.gov/introduction.html#security-and-authentication
  * Set in environment prior to running scrape: ``INDIANA_API_KEY``
  * As a side note, Indiana also requires a `user-agent string <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent>`_, so set that in your environment as well, prior to running scrape: ``USER_AGENT``
