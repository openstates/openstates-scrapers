The Open States Project collects and makes available data about state legislative activities, including bill summaries, votes, sponsorships and state legislator information. This data is gathered directly from the states and made available in a common format for interested developers, through a JSON API and data dumps.

Links
=====

* `Open States Project API <http://docs.openstates.org/api/>`_
* `Code on GitHub <https://github.com/openstates/openstates/>`_
* `Issue Tracker <https://github.com/openstates/openstates/issues>`_
* `Open States Slack <http://openstates-slack.herokuapp.com>`_

Getting Started
===============
We use `Docker <https://www.docker.com/products/docker>`_ to provide a reproducible development environment. Make sure
you have Docker installed.  Inside of the directory you cloned this project into::

  docker-compose run --rm scrape <abbreviated state code>  # Scrapes the state indicated by the code e.g. "ny"

For each state, you can also select one or more individual scrapers to run.  The scraper names vary from state to state; look at the ``scrapers`` listed in the state's ``__init__.py``. For example, Tennessee has:: 

    scrapers = {
        'bills': TNBillScraper,
        'committees': TNCommitteeScraper,
        'events': TNEventScraper,
        'people': TNPersonScraper,
    }

So you can limit the scrape to Tennessee's (tn) committees and legislators using::

  docker-compose run --rm scrape tn committees people

After retrieving everything from the state, `scrape` imports the data into a Postgresql database (setup doc pending).  If you want to skip this step, include a `--scrape` modifier at the end of the command line, like so::

  docker-compose run --rm scrape tn people --scrape

After you run `scrape`, it will leave .json files, one for each entity scraped, in the ``_data`` project subdirectory.  These contain the transformed, scraped data, and are very useful for debugging. 

Check out the `writing scrapers guide <http://docs.openstates.org/en/latest/contributing/getting-started.html>`_ to understand how the scrapers work & how to contribute.

Testing
=======
To run all tests::

  docker-compose run --rm --entrypoint=nosetests scrape /srv/openstates-web/openstates

Note that Illinois is the only state with scraper tests right now.

Our scraping framework, Pupa, has a strong test harness, and requires well-structured data when ingesting. Furthermore, Open States scrapers should be written to fail when they encounter unexpected data, rather than guessing at its format and possibly ingesting bad data. Together, this means that there aren't many benefits to writing unit tests for particular Open States scrapers, versus relatively high upkeep costs.

API Keys
========

A few states require credentials to access their APIs. If you want to run code for these states, get credentials for yourself using these steps:

* NY

  * Get credentials at: http://legislation.nysenate.gov/
  * Set in environment prior to running scrape: ``NEW_YORK_API_KEY``

* IN

  * Get credentials at: http://docs.api.iga.in.gov/introduction.html
  * Set in environment prior to running scrape: ``INDIANA_API_KEY``

* OR

  * Get credentials at: https://www.oregonlegislature.gov/citizen_engagement/Pages/data.aspx
  * Set in environment prior to running scrape: ``OLODATA_USERNAME`` and ``OLODATA_PASSWORD``
