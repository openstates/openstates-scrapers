#!/bin/sh

MAX_SECONDS_TO_WAIT=30

seconds_waited=0
until mysql -h "${MYSQL_HOST:-"localhost"}" -u "${MYSQL_USER:-"root"}" -e "SHOW DATABASES"; do
  sleep 1

  seconds_waited=$((seconds_waited+1))
  if [ "$seconds_waited" -gt "$MAX_SECONDS_TO_WAIT" ]; then
    echo "ERROR: California's MySQL was not available after $MAX_SECONDS_TO_WAIT seconds; exiting"
    exit 1
  fi
done

poetry run python -m openstates.ca.download
