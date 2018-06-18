|ocbackers| |ocsponsors| 
The Open States Project collects and makes available data about state legislative activities, including bill summaries, votes, sponsorships and state legislator information. This data is gathered directly from the states and made available in a common format for interested developers, through a JSON API and data dumps.

Links
=====

* `Open States Project API <http://docs.openstates.org/api/>`_
* `Code on GitHub <https://github.com/openstates/openstates/>`_
* `Issue Tracker <https://github.com/openstates/openstates/issues>`_
* `Open States Discourse <http://discourse.openstates.org>`_

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

After retrieving everything from the state, `scrape` imports the data into a Postgresql database. If you want to skip this step, include a `--scrape` modifier at the end of the command line, like so::

  docker-compose run --rm scrape tn people --scrape

To import data into a postgres database, start the postgres service using docker compose::

    docker-compose up postgres

Then run database migrations and import jurisdictions::

    docker-compose run --rm dbinit

Now you can run the scrape service without the `--scrape` flag, and data will be imported into postgres. You can connect to the database and inspect data using `psql` (credentials are set in `docker-compose.yml`)::

    psql postgres://postgres:secret@localhost:5432/openstates

After you run `scrape`, it will leave .json files, one for each entity scraped, in the ``_data`` project subdirectory. These contain the transformed, scraped data, and are very useful for debugging. 

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
  
Credits
=======
Contributors
+-----------------
Thank you to all the people who have already contributed. 
|occontributorimage|

Backers
-----------------
Thank you to all our backers! 
|ocbackerimage|

Sponsors
-----------------
Support this project by becoming a sponsor. Your logo will show up here with a link to your website. `become_sponsor`_

|ocsponsor0| |ocsponsor1| |ocsponsor2|

.. |ocbackers| image:: https://opencollective.com/openstates/backers/badge.svg
    :target: https://opencollective.com/openstates
    :alt: Backers on Open Collective
.. |ocsponsors| image:: https://opencollective.com/openstates/sponsors/badge.svg
    :target: https://opencollective.com/openstates
    :alt: Sponsors on Open Collective
    
.. |ocbackerimage| image:: https://opencollective.com/openstates/backers.svg?width=890
    :target: https://opencollective.com/openstates
    :alt: Backers on Open Collective
.. |occontributorimage| image:: https://opencollective.com/openstates/contributors.svg?width=890&button=false
    :target: https://opencollective.com/openstates
    :alt: Repo Contributors

.. _become_sponsor: https://opencollective.com/openstates#sponsor

.. |ocsponsor0| image:: https://opencollective.com/openstates/sponsor/0/avatar.svg
    :target: https://opencollective.com/openstates/sponsor/0/website
    :alt: Sponsor
.. |ocsponsor1| image:: https://opencollective.com/openstates/sponsor/1/avatar.svg
    :target: https://opencollective.com/openstates/sponsor/1/website
    :alt: Sponsor
.. |ocsponsor2| image:: https://opencollective.com/openstates/sponsor/2/avatar.svg
    :target: https://opencollective.com/openstates/sponsor/2/website
    :alt: Sponsor
