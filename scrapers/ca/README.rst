Getting Started
===============

SQLite (recommended)
--------------------

Extract a ``pubinfo`` data archive, then point the scraper at that directory. The
first run creates ``capublic.sqlite3`` beside the ``.dat`` files; later runs reuse
it until the dump files change. ::

    $ CA_DATA_DIR=~/Downloads/pubinfo_daily_Mon os-update ca bills --scrape

With the repository's local command wrapper, including an explicit session: ::

    $ CA_DATA_DIR=~/Downloads/pubinfo_daily_Mon ./command.sh ca bills session=20252026

The database can also be built explicitly. ::

    $ python -m scrapers.ca.sqlite_import ~/Downloads/pubinfo_daily_Mon

Use ``CA_SQLITE_PATH`` to place the generated database elsewhere, or
``CA_DATABASE_URL=sqlite:////absolute/path/capublic.sqlite3`` to use an existing
database without inspecting dump files.

MySQL (legacy)
--------------

Download and ingest the data: ::

    $ docker-compose run --rm ca-download

- Scrape the data: ::

    $ docker-compose run --rm scrape ca
