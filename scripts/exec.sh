#!/usr/bin/env bash

if [[ $# -lt 2 ]]; then
    echo "You must provide at least 2 arguments for this script to work"
    exit 2
fi

DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-5432}
DATABASE_URL="postgres://openstates:openstates@${DB_HOST}:${DB_PORT}/openstatesorg"
export DATABASE_URL
PYTHONPATH=scrapers poetry run os-update $@
