#!/bin/sh

set -eo pipefail
unset DATABASE_URL

if command -v docker-compose > /dev/null 2>&1; then
    _COMPOSE="docker-compose"
else
    _COMPOSE="docker compose"
fi

# migrate and populate db
DATABASE_URL=postgis://openstates:openstates@db/openstatesorg ${_COMPOSE} run --rm --entrypoint "poetry run os-initdb" scrape
