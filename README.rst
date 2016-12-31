The Open States Project collects and makes available data about state legislative activities, including bill summaries, votes, sponsorships and state legislator information. This data is gathered directly from the states and made available in a common format for interested developers, through a JSON API and data dumps.

Links
=====

* `Open States Project API <http://openstates.org/api/>`_
* `Contributing Guidelines <http://openstates.org/contributing/>`_
* `Code on GitHub <http://github.com/sunlightlabs/openstates/>`_
* `Issue Tracker <http://sunlight.atlassian.net>`_
* `Open State Project Google Group <http://groups.google.com/group/fifty-state-project>`_
* `Sunlight Labs <http://sunlightlabs.com>`_

Getting Started
====
We use `Docker <https://www.docker.com/products/docker>`_ to provide a reproducible development environment. Make sure
you have Docker installed.  Inside of the directory you cloned this project into::

  docker build -t openstates/openstates .  # Flaky. Try running the command again if it fails.
  docker run openstates/openstates <abbreviated state code>  # Scrapes the state indicated by the code e.g. "ny"

This project runs on top of `billy <https://github.com/openstates/billy>`_, a scraping framework for government data.
Our Docker container runs the ``billy-update`` command
(`billy-update docs <http://billy.readthedocs.io/en/latest/scripts.html>`_) with whatever arguments you put at the end
of ``docker run``. For example, you can limit the scrape to Tennessee's (tn) state senators using::

  docker run openstates/openstates tn --upper --legislators

You have your local changes included in the container by
`mounting your clone directory <https://docs.docker.com/engine/tutorials/dockervolumes/#mount-a-host-directory-as-a-data-volume>`_::
  docker run -v `pwd`:/srv/openstates-web openstates/openstates [billy-update-args...]


Testing
====
To run all tests::

  docker run --entrypoint=nosetests openstates/openstates /srv/openstates-web/openstates

Note that Illinois (il) is the only state with tests right now.
