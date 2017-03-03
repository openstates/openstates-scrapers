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

  docker-compose build  # Flaky. Try running the command again if it fails.
  docker-compose up database  # Starts the database
  docker-compose run openstates <abbreviated state code>  # Scrapes the state indicated by the code e.g. "ny"

This project runs on top of `billy <https://github.com/openstates/billy>`_, a scraping framework for government data.
Our Docker container runs the ``billy-update`` command
(`billy-update docs <http://billy.readthedocs.io/en/latest/scripts.html>`_) with whatever arguments you put at the end
of ``docker run``. For example, you can limit the scrape to Tennessee's (tn) state senators using::

  docker-compose run openstates tn --upper --legislators

Check out the `writing scrapers guide <http://docs.openstates.org/en/latest/contributing/writing-scrapers.html>`_ to understand how the scrapers work & how to contribute.

Testing
=======
To run all tests::

  docker-compose run --entrypoint=nosetests openstates /srv/openstates-web/openstates

Note that Illinois (il) is the only state with tests right now.
