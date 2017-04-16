#!/bin/bash

echo "HIHIHI"
until mysql -h "${MYSQL_HOST:-"localhost"}" -u "${MYSQL_USER:-"root"}" -e "SHOW DATABASES"; do
  echo "SLEEP"
  sleep 1
done

$PUPA_ENV/bin/python -m openstates.ca.download
