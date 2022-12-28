#!/bin/sh

set -ex
unset DATABASE_URL

# stop database and remove volume
docker compose down

# only remove volume if it exists
set +e
VOLNAME=$(docker volume ls -q | grep openstates-postgres)
[[ -n "${VOLNAME}" ]] && docker volume rm "${VOLNAME}"
set -e

docker compose up --wait db

# migrate and populate db
DATABASE_URL=postgis://openstates:openstates@db/openstatesorg docker compose run --rm --entrypoint "poetry run os-initdb" scrape
