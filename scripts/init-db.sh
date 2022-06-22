#!/bin/sh

set -ex
unset DATABASE_URL

# stop database and remove volume
docker-compose down
docker-compose up -d db
sleep 3

# migrate and populate db
DATABASE_URL=postgis://openstates:openstates@db/openstatesorg docker-compose run --rm --entrypoint "poetry run os-initdb" scrape
