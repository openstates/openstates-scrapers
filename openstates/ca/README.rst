Getting Started
===============

- Run mysql via docker-compose: ::

    $ docker-compose up mysql

- Download and ingest the data: ::

    $ docker-compose run --entrypoint python openstates -m openstates.ca.download

- Scrape the data: ::

    $ docker-compose run openstates ca
